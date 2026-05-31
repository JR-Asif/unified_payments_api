from decimal import Decimal
import uuid
from app.strategies.base import PaymentStrategy, NormalizedPaymentResponse, NormalizedRefundResponse


_PROVIDER_B_STATUS_MAP = {
    "INITIATED": "SUCCESS",
    "COMPLETED": "SUCCESS",
    "FAILED": "FAILED",
    "PENDING": "PENDING",
}


class ProviderBStrategy(PaymentStrategy):

    def process_payment(self, amount: Decimal, currency: str, customer_id: str) -> NormalizedPaymentResponse:
        string_amount = f"{amount:.2f}"
        unique_transaction_ref = f"txn_B_{uuid.uuid4().hex[:10]}"

        mock_raw_json = {
            "transactionId": unique_transaction_ref,
            "paymentStatus": "INITIATED",
            "totalAmount": string_amount,
            "currencyCode": currency.upper(),
        }

        return NormalizedPaymentResponse(
            provider_reference=mock_raw_json["transactionId"],
            amount=Decimal(mock_raw_json["totalAmount"]),
            status=_PROVIDER_B_STATUS_MAP.get(mock_raw_json["paymentStatus"], "PENDING"),
            raw_response=mock_raw_json,
        )

    def process_refund(self, payment_reference: str, amount: Decimal, currency: str) -> NormalizedRefundResponse:
        string_amount = f"{amount:.2f}"

        unique_refund_ref = f"ref_B_{uuid.uuid4().hex[:10]}"

        mock_raw_json = {
            "refundTrackId": unique_refund_ref,
            "paymentStatus": "REFUNDED",
            "totalAmount": string_amount,
            "currencyCode": currency.upper(),
        }

        return NormalizedRefundResponse(
            provider_reference=mock_raw_json["refundTrackId"],
            amount=Decimal(mock_raw_json["totalAmount"]),
            status="SUCCESS",
            raw_response=mock_raw_json,
        )
