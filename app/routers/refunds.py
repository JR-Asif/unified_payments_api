from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
import hashlib
import uuid
from app.database import get_db
from app.schemas import RefundCreate, RefundResponse
from app.utils.idempotency import IdempotencyManager
from app.models import Payment, Refund
from app.utils.loggers import logger, customer_id_ctx, request_id_ctx
from app.strategies.factory import PaymentProcessorFactory


router = APIRouter(prefix="/payments", tags=["Refunds"])


# Refund — POST /payments/{payment_id}/refund per spec. Full amount only.
@router.post("/{payment_id}/refund", response_model=RefundResponse, status_code=status.HTTP_201_CREATED)
def create_refund(
    payment_id: uuid.UUID,
    payload: RefundCreate,
    db: Session = Depends(get_db),
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
):
    request_id_ctx.set(uuid.uuid4().hex[:8])
    logger.info(f"refund.request_received payment_id={payment_id} amount={payload.amount} reason=\"{payload.reason}\"")

    scoped_cache_key = f"idemp:refund:{payment_id}:{x_idempotency_key}"

    payload_string = f"{payment_id}:{payload.amount}:{payload.reason}"
    current_request_hash = hashlib.sha256(payload_string.encode()).hexdigest()

    is_new, state, cached_data = IdempotencyManager.acquire_lock_or_get_status(scoped_cache_key)

    if not is_new:
        if state == "IN_PROGRESS":
            logger.warning(f"refund.duplicate_in_flight payment_id={payment_id} key={scoped_cache_key}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This refund request is already active in our cluster.",
            )

        if state == "SUCCESS":
            if cached_data.get("request_hash") != current_request_hash:
                logger.warning(f"refund.idempotency_payload_tampered payment_id={payment_id} key={scoped_cache_key}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Idempotency Key Violation: Refund attributes do not match original request.",
                )
            logger.info(f"refund.idempotency_cache_hit payment_id={payment_id} key={scoped_cache_key}")
            return cached_data["response"]

    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            logger.warning(f"refund.parent_payment_not_found payment_id={payment_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original payment trace not found.")

        customer_id_ctx.set(str(payment.customer_id))

        if payload.amount != payment.amount:
            logger.warning(f"refund.partial_attempt_blocked payment_id={payment_id} requested={payload.amount} original={payment.amount}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Business Rule Violation: Partial refunds are strictly disabled. Expected exactly {payment.amount} {payment.currency}.",
            )

        existing_refund = db.query(Refund).filter(Refund.payment_id == payment_id, Refund.status == "SUCCESS").first()
        if existing_refund:
            logger.warning(f"refund.duplicate_full_refund_blocked payment_id={payment_id} existing_refund_id={existing_refund.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Business Rule Violation: This transaction has already been fully refunded.",
            )

        if not payment.provider_reference:
            logger.warning(f"refund.parent_payment_unprocessed payment_id={payment_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Original payment was never captured by a provider; nothing to refund.",
            )

        try:
            strategy = PaymentProcessorFactory.get_strategy(payment.provider)
            logger.info(f"refund.gateway_call payment_id={payment_id} provider={payment.provider} payment_reference={payment.provider_reference}")
            refund_response = strategy.process_refund(
                payment_reference=payment.provider_reference,
                amount=payload.amount,
                currency=payment.currency,
            )
            logger.info(f"refund.gateway_success payment_id={payment_id} provider_reference={refund_response.provider_reference} status={refund_response.status}")
        except HTTPException:
            raise
        except Exception:
            logger.exception(f"refund.gateway_failed payment_id={payment_id} provider={payment.provider}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Refund could not be processed by the upstream provider.",
            )

        db_refund = Refund(
            payment_id=payment_id,
            amount=refund_response.amount,
            reason=payload.reason,
            status=refund_response.status,
            provider_reference=refund_response.provider_reference,
            raw_response=refund_response.raw_response,
        )
        db.add(db_refund)
        db.commit()
        db.refresh(db_refund)
        logger.info(f"refund.created refund_id={db_refund.id} payment_id={payment_id} amount={db_refund.amount} status={db_refund.status}")

        response_model_data = RefundResponse.model_validate(db_refund).model_dump(mode="json")
        cache_payload = {
            "request_hash": current_request_hash,
            "response": response_model_data,
        }
        IdempotencyManager.commit_success(scoped_cache_key, cache_payload)

        return response_model_data

    except HTTPException:
        IdempotencyManager.release_lock(scoped_cache_key)
        raise
    except Exception:
        logger.exception(f"refund.processing_failed payment_id={payment_id} key={scoped_cache_key}")
        IdempotencyManager.release_lock(scoped_cache_key)
        raise
