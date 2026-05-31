import uuid
from decimal import Decimal
from app.strategies.base import PaymentStrategy, NormalizedPaymentResponse, NormalizedRefundResponse


_PROVIDER_A_STATE_MAP = {
    "created": "SUCCESS",
    "captured": "SUCCESS",
    "failed": "FAILED",
    "pending": "PENDING",
}


class ProviderAStrategy(PaymentStrategy):

    def process_payment(self, amount: Decimal, currency: str, customer_id: str) -> NormalizedPaymentResponse:
        cents_amount = int(amount * 100)

        unique_bank_ref = f"pay_A_{uuid.uuid4().hex[:10]}"

        mock_raw_json = {
            "id": unique_bank_ref,
            "state": "created",
            "amount": cents_amount,
            "currency": currency.upper(),
        }

        return NormalizedPaymentResponse(
            provider_reference=mock_raw_json["id"],
            amount=Decimal(mock_raw_json["amount"]) / 100,
            status=_PROVIDER_A_STATE_MAP.get(mock_raw_json["state"], "PENDING"),
            raw_response=mock_raw_json,
        )

    def process_refund(self, payment_reference: str, amount: Decimal, currency: str) -> NormalizedRefundResponse:
        cents_amount = int(amount * 100)
        unique_refund_ref = f"ref_A_{uuid.uuid4().hex[:10]}"

        mock_raw_json = {
            "id": unique_refund_ref,
            "state": "refunded",
            "amount": cents_amount,
            "currency": currency.upper(),
        }

        return NormalizedRefundResponse(
            provider_reference=mock_raw_json["id"],
            amount=Decimal(mock_raw_json["amount"]) / 100,
            status="SUCCESS",
            raw_response=mock_raw_json,
        )
