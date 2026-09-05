import app.routers.payment as payment_module
from app.config import settings


def _secret_headers() -> dict[str, str]:
    return {"X-Webhook-Secret": settings.payment_webhook_secret}


def _create_order(client, sample_trip, n=1):
    return client.post(
        "/orders",
        json={
            "trip_id": sample_trip.id,
            "passengers": [
                {"first_name": "A", "last_name": "B", "email": "a@b.com", "age": 30}
                for _ in range(n)
            ],
        },
    ).json()["id"]


def test_webhook_marks_order_paid(client, sample_trip):
    order_id = _create_order(client, sample_trip)
    r = client.post(
        "/payment/webhook",
        json={"order_id": order_id, "success": True},
        headers=_secret_headers(),
    )
    assert r.status_code == 200
    assert r.json() == {"order_id": order_id, "status": "paid", "applied": True}

    # replay is idempotent
    r = client.post(
        "/payment/webhook",
        json={"order_id": order_id, "success": True},
        headers=_secret_headers(),
    )
    assert r.json()["applied"] is False


def test_webhook_unknown_order_404(client):
    r = client.post(
        "/payment/webhook",
        json={"order_id": 424242, "success": True},
        headers=_secret_headers(),
    )
    assert r.status_code == 404


def test_webhook_rejects_missing_secret(client, sample_trip):
    """An unauthenticated caller must not be able to flip an order to paid."""
    order_id = _create_order(client, sample_trip)
    r = client.post("/payment/webhook", json={"order_id": order_id, "success": True})
    assert r.status_code == 401
    # ...and the order stays pending (no side effect leaked past the guard).
    got = client.get(f"/orders/{order_id}").json()
    assert got["status"] == "pending"


def test_webhook_rejects_wrong_secret(client, sample_trip):
    order_id = _create_order(client, sample_trip)
    r = client.post(
        "/payment/webhook",
        json={"order_id": order_id, "success": True},
        headers={"X-Webhook-Secret": "not-the-secret"},
    )
    assert r.status_code == 401


def test_simulate_endpoint(client, sample_trip):
    order_id = _create_order(client, sample_trip)
    r = client.post(f"/payment/simulate/{order_id}", params={"success": "false"})
    assert r.status_code == 200
    assert r.json()["status"] == "failed"


def test_simulate_disabled_in_production(client, sample_trip, monkeypatch):
    """The mock-gateway trigger is a dev helper and must not exist in production."""
    order_id = _create_order(client, sample_trip)
    monkeypatch.setattr(payment_module.settings, "environment", "production")
    r = client.post(f"/payment/simulate/{order_id}", params={"success": "true"})
    assert r.status_code == 404
