from abc import ABC, abstractmethod
from decimal import Decimal
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class NormalizedPaymentResponse:
    """Common payment shape — what both Provider A and Provider B Responses get translated into."""
    provider_reference: str
    amount: Decimal
    status: str
    raw_response: Dict[str, Any]


@dataclass
class NormalizedRefundResponse:
    """Common refund shape — what both providers' refund responses get translated into."""
    provider_reference: str
    amount: Decimal
    status: str
    raw_response: Dict[str, Any]


class PaymentStrategy(ABC):
    """Interface every external payment provider must implement (per spec: two providers with different formats)."""

    @abstractmethod
    def process_payment(self, amount: Decimal, currency: str, customer_id: str) -> NormalizedPaymentResponse:
        pass

    @abstractmethod
    def process_refund(self, payment_reference: str, amount: Decimal, currency: str) -> NormalizedRefundResponse:
        pass
