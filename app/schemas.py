from pydantic import BaseModel, ConfigDict, Field, field_validator
from decimal import Decimal
from datetime import datetime
from typing import Optional, Any, Dict
import uuid


class PaymentCreate(BaseModel):
    """Create Payment request body (POST /payments per spec)."""
    amount: Decimal = Field(..., gt=0, description="The payment amount. Must be greater than 0.")
    currency: str = Field(..., min_length=3, max_length=3, description="3-letter ISO currency code (e.g., SAR).")
    customer_id: str = Field(..., min_length=1, description="The unique identifier of the customer.")
    provider: str = Field(..., description="The target payment gateway (e.g., provider_a, provider_b).")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        """Uppercase the currency and reject anything outside our supported list."""
        ALLOWED_CURRENCIES = {"SAR", "USD", "EUR", "INR", "PKR"}
        normalized = value.upper()
        if normalized not in ALLOWED_CURRENCIES:
            raise ValueError(f"Invalid currency: {value}. Must be one of: {', '.join(ALLOWED_CURRENCIES)}")
        return normalized

    @field_validator("provider")
    @classmethod
    def validate_provider_name(cls, value: str) -> str:
        """Lowercase the provider name so it matches our strategy keys."""
        return value.lower()


class PaymentResponse(BaseModel):
    """Payment response shape returned to the client."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    amount: Decimal
    currency: str
    customer_id: str
    provider: str
    provider_reference: Optional[str] = None
    status: str
    raw_response: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class RefundCreate(BaseModel):
    """Refund request body (POST /payments/{payment_id}/refund per spec)."""
    amount: Decimal = Field(..., gt=0, description="Amount to refund. Can be partial or full.")
    reason: Optional[str] = Field(None, max_length=255, description="Optional note regarding why the refund was issued.")


class RefundResponse(BaseModel):
    """Refund response shape returned to the client."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payment_id: uuid.UUID
    amount: Decimal
    status: str
    provider_reference: Optional[str] = None
    reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
