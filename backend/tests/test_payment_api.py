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
    r = client.post("/payment/webhook", json={"order_id": order_id, "success": True})
    assert r.status_code == 200
    assert r.json() == {"order_id": order_id, "status": "paid", "applied": True}

    # replay is idempotent
    r = client.post("/payment/webhook", json={"order_id": order_id, "success": True})
    assert r.json()["applied"] is False


def test_webhook_unknown_order_404(client):
    r = client.post("/payment/webhook", json={"order_id": 424242, "success": True})
    assert r.status_code == 404


def test_simulate_endpoint(client, sample_trip):
    order_id = _create_order(client, sample_trip)
    r = client.post(f"/payment/simulate/{order_id}", params={"success": "false"})
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
