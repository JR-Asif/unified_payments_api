from decimal import Decimal
from app.strategies.provider_a import ProviderAStrategy
from app.strategies.provider_b import ProviderBStrategy


def test_provider_a_normalizes_payment_correctly():
    """Provider A Response (id, state, cents amount, currency) normalizes correctly."""
    strategy = ProviderAStrategy()
    response = strategy.process_payment(
        amount=Decimal("100.50"),
        currency="SAR",
        customer_id="cust_1",
    )

    assert response.amount == Decimal("100.50")
    assert response.status == "SUCCESS"
    assert response.provider_reference.startswith("pay_A_")
    assert response.raw_response["state"] == "created"
    assert response.raw_response["amount"] == 10050
    assert response.raw_response["currency"] == "SAR"


def test_provider_b_normalizes_payment_correctly():
    """Provider B Response (transactionId, paymentStatus, string totalAmount, currencyCode) normalizes correctly."""
    strategy = ProviderBStrategy()
    response = strategy.process_payment(
        amount=Decimal("100.50"),
        currency="SAR",
        customer_id="cust_2",
    )

    assert response.amount == Decimal("100.50")
    assert response.status == "SUCCESS"
    assert response.provider_reference.startswith("txn_B_")
    assert response.raw_response["paymentStatus"] == "INITIATED"
    assert response.raw_response["totalAmount"] == "100.50"
    assert response.raw_response["currencyCode"] == "SAR"


def test_provider_b_unique_reference_per_call():
    """Two Provider B calls must produce different references (caught a hardcoded-id bug)."""
    strategy = ProviderBStrategy()
    r1 = strategy.process_payment(amount=Decimal("10"), currency="SAR", customer_id="c1")
    r2 = strategy.process_payment(amount=Decimal("10"), currency="SAR", customer_id="c2")
    assert r1.provider_reference != r2.provider_reference
