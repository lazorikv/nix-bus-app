def _passengers(n=2):
    return [
        {
            "first_name": f"First{i}",
            "last_name": "Last",
            "email": f"p{i}@example.com",
            "age": 25 + i,
        }
        for i in range(n)
    ]


def test_authenticated_user_creates_order_and_seats_decrement(client, user_headers, sample_trip):
    start = sample_trip.seats_left
    r = client.post(
        "/orders",
        json={"trip_id": sample_trip.id, "passengers": _passengers(2)},
        headers=user_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending"
    assert body["price"] == "50.00"  # 25 * 2
    assert body["passengers"][0]["ticket_price"] == "25.00"

    trip = client.get(f"/trips/{sample_trip.id}").json()
    assert trip["seats_left"] == start - 2


def test_anonymous_can_create_order(client, sample_trip):
    r = client.post(
        "/orders",
        json={"trip_id": sample_trip.id, "passengers": _passengers(1)},
    )
    assert r.status_code == 201
    assert r.json()["user_id"] is None


def test_order_rejected_when_sold_out(client, user_headers, sample_trip, db):
    # book everything first
    r = client.post(
        "/orders",
        json={"trip_id": sample_trip.id, "passengers": _passengers(1)},
        headers=user_headers,
    )
    assert r.status_code == 201

    from app.infrastructure.db.models import Trip

    trip = db.get(Trip, sample_trip.id)
    trip.seats_left = 0
    db.commit()

    r = client.post(
        "/orders",
        json={"trip_id": sample_trip.id, "passengers": _passengers(1)},
        headers=user_headers,
    )
    assert r.status_code == 409


def test_users_see_only_own_orders_admin_sees_all(client, user_headers, admin_headers, sample_trip):
    client.post(
        "/orders",
        json={"trip_id": sample_trip.id, "passengers": _passengers(1)},
        headers=user_headers,
    )
    client.post(
        "/orders",
        json={"trip_id": sample_trip.id, "passengers": _passengers(1)},
        headers=admin_headers,
    )

    user_list = client.get("/orders", headers=user_headers).json()
    assert user_list["total"] == 1

    admin_list = client.get("/orders", headers=admin_headers).json()
    assert admin_list["total"] == 2


def test_user_cannot_view_another_users_order(client, user_headers, admin_headers, sample_trip):
    order_id = client.post(
        "/orders",
        json={"trip_id": sample_trip.id, "passengers": _passengers(1)},
        headers=admin_headers,
    ).json()["id"]

    # admin's order is not anonymous, so normal user is forbidden
    r = client.get(f"/orders/{order_id}", headers=user_headers)
    assert r.status_code == 403


def test_list_orders_requires_auth(client):
    assert client.get("/orders").status_code == 401
