def _create_payment(client, idem_key="ref-pay-1"):
    """Helper — creates a payment and returns its id."""
    response = client.post(
        "/payments",
        headers={"X-Idempotency-Key": idem_key},
        json={
            "amount": 100,
            "currency": "SAR",
            "customer_id": "cust_refund",
            "provider": "provider_a",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_create_refund_happy_path(client):
    """Refund (full amount) on an existing payment returns 201."""
    payment_id = _create_payment(client)
    response = client.post(
        f"/payments/{payment_id}/refund",
        headers={"X-Idempotency-Key": "ref-1"},
        json={"amount": 100, "reason": "customer request"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["payment_id"] == payment_id


def test_refund_partial_amount_rejected(client):
    """Partial refund is rejected — spec requires full-amount refunds."""
    payment_id = _create_payment(client, idem_key="ref-pay-2")
    response = client.post(
        f"/payments/{payment_id}/refund",
        headers={"X-Idempotency-Key": "ref-2"},
        json={"amount": 50, "reason": "partial"},
    )
    assert response.status_code == 400
