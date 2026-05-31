def test_create_payment_happy_path_provider_a(client):
    """Create Payment with provider_a — happy path returns 201 + SUCCESS."""
    response = client.post(
        "/payments",
        headers={"X-Idempotency-Key": "test-a-1"},
        json={
            "amount": 100.50,
            "currency": "SAR",
            "customer_id": "cust_9874",
            "provider": "provider_a",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["provider"] == "provider_a"
    assert body["provider_reference"].startswith("pay_A_")
    assert body["customer_id"] == "cust_9874"


def test_create_payment_unknown_provider_returns_400(client):
    """Unknown provider name is rejected with 400."""
    response = client.post(
        "/payments",
        headers={"X-Idempotency-Key": "test-bad-1"},
        json={
            "amount": 50,
            "currency": "SAR",
            "customer_id": "cust_x",
            "provider": "stripe",
        },
    )
    assert response.status_code == 400


def test_get_payment_not_found_returns_404(client):
    """Get Payment for an unknown id returns 404."""
    response = client.get("/payments/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_idempotent_retry_returns_cached_response(client):
    """Retrying Create Payment with the same idempotency key returns the same payment (no double charge)."""
    payload = {
        "amount": 25,
        "currency": "SAR",
        "customer_id": "cust_idem",
        "provider": "provider_a",
    }
    headers = {"X-Idempotency-Key": "idem-test"}

    first = client.post("/payments", headers=headers, json=payload)
    second = client.post("/payments", headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
