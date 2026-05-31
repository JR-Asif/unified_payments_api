import hashlib
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from app.schemas import PaymentCreate, PaymentResponse
from app.database import get_db
from app.models import Payment
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from datetime import datetime, timezone
from app.config import settings
from typing import List, Optional

from app.strategies.factory import PaymentProcessorFactory
from app.utils.idempotency import IdempotencyManager
import uuid
from app.utils.loggers import logger, customer_id_ctx, request_id_ctx


router = APIRouter(prefix="/payments", tags=["payments"])


# Create Payment — POST /payments per spec. Idempotency key required.
@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def create_payment(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    x_idempotency_key: str = Header(
        ...,
        alias="X-Idempotency-Key",
        description="Required: unique key to prevent duplicate charges on retries",
    ),
):
    request_id_ctx.set(uuid.uuid4().hex[:8])
    customer_id_ctx.set(payload.customer_id)
    logger.info(
        f"payment.request_received customer_id={payload.customer_id} "
        f"amount={payload.amount} currency={payload.currency} "
        f"provider={payload.provider} has_idempotency_key={bool(x_idempotency_key)}"
    )

    scoped_cache_key = f"idemp:{payload.customer_id}:{x_idempotency_key}"

    payload_string = f"{payload.amount}:{payload.currency}:{payload.customer_id}:{payload.provider}"
    current_request_hash = hashlib.sha256(payload_string.encode()).hexdigest()

    is_new, state, cached_data = IdempotencyManager.acquire_lock_or_get_status(scoped_cache_key)

    if not is_new:
        if state == "IN_PROGRESS":
            logger.warning(f"payment.duplicate_in_flight key={scoped_cache_key}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A duplicate transaction is already processing in our cluster.",
            )
        if state == "SUCCESS":
            cached_hash = cached_data.get("request_hash")
            if cached_hash and cached_hash != current_request_hash:
                logger.warning(f"payment.idempotency_payload_tampered key={scoped_cache_key}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Idempotency Key Violation: Payload parameters do not match original request.",
                )
            logger.info(f"payment.idempotency_cache_hit key={scoped_cache_key}")
            return cached_data["response"]

    try:
        db_payment_record = process_payment_lifecycle(payload, db)

        response_model_data = PaymentResponse.model_validate(db_payment_record).model_dump(mode="json")

        cache_payload = {
            "request_hash": current_request_hash,
            "response": response_model_data,
        }
        IdempotencyManager.commit_success(scoped_cache_key, cache_payload)
        logger.info(
            f"payment.created payment_id={db_payment_record.id} amount={db_payment_record.amount} "
            f"currency={db_payment_record.currency} provider={db_payment_record.provider} "
            f"status={db_payment_record.status}"
        )

        return response_model_data

    except HTTPException:
        IdempotencyManager.release_lock(scoped_cache_key)
        raise
    except Exception:
        logger.exception(f"payment.processing_failed key={scoped_cache_key}")
        IdempotencyManager.release_lock(scoped_cache_key)
        raise


def process_payment_lifecycle(payload: PaymentCreate, db: Session) -> Payment:
    """Persist the payment row, call the chosen provider, then store the result."""
    db_payment = Payment(
        amount=payload.amount,
        currency=payload.currency.upper(),
        customer_id=payload.customer_id,
        provider=payload.provider,
        status="PENDING",
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    logger.info(f"payment.pending_persisted payment_id={db_payment.id} status=PENDING")

    try:
        strategy = PaymentProcessorFactory.get_strategy(payload.provider)
        logger.info(f"payment.gateway_call payment_id={db_payment.id} provider={payload.provider}")
        gateway_response = strategy.process_payment(
            amount=payload.amount, currency=payload.currency, customer_id=payload.customer_id
        )

        db_payment.status = gateway_response.status
        db_payment.provider_reference = gateway_response.provider_reference
        db_payment.raw_response = gateway_response.raw_response
        db.commit()
        db.refresh(db_payment)
        logger.info(
            f"payment.gateway_success payment_id={db_payment.id} "
            f"provider_reference={gateway_response.provider_reference} "
            f"status={gateway_response.status}"
        )
        return db_payment

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"payment.gateway_failed payment_id={db_payment.id} provider={payload.provider}")
        db.rollback()
        db.query(Payment).filter(Payment.id == db_payment.id).update({
            "status": "FAILED",
            "raw_response": {"error_type": type(exc).__name__},
        })
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream payment provider failed to process the request.",
        )


# Get Payment by id — GET /payments/{payment_id} per spec
@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: UUID, db: Session = Depends(get_db)):
    """Get Payment by id (per spec: GET /payments/{payment_id})."""
    request_id_ctx.set(uuid.uuid4().hex[:8])
    try:
        payment = db.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            logger.warning(f"payment.not_found payment_id={payment_id}")
            raise HTTPException(status_code=404, detail="Payment not found")
        customer_id_ctx.set(str(payment.customer_id))
        return PaymentResponse.model_validate(payment)
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"payment.fetch_failed payment_id={payment_id}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
