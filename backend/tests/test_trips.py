def _route(o_time="2026-08-01T08:00:00", d_time="2026-08-01T15:00:00"):
    return [
        {"city_id": 1, "city_name": "Kyiv", "time": o_time, "position": 0},
        {"city_id": 2, "city_name": "Lviv", "time": d_time, "position": 1},
    ]


def _create_trip(client, admin_headers, bus_id, name="T", price=25, route=None):
    return client.post(
        "/trips",
        json={
            "name": name,
            "price": price,
            "bus_id": bus_id,
            "route": route or _route(),
        },
        headers=admin_headers,
    )


def test_seats_left_initialized_from_bus(client, admin_headers, sample_bus):
    r = _create_trip(client, admin_headers, sample_bus.id)
    assert r.status_code == 201
    assert r.json()["seats_left"] == sample_bus.seats_quantity


def test_route_requires_two_stops(client, admin_headers, sample_bus):
    r = _create_trip(
        client,
        admin_headers,
        sample_bus.id,
        route=[{"city_id": 1, "city_name": "Kyiv", "time": "2026-08-01T08:00:00", "position": 0}],
    )
    assert r.status_code == 422


def test_route_requires_chronological_order(client, admin_headers, sample_bus):
    r = _create_trip(
        client,
        admin_headers,
        sample_bus.id,
        route=_route(o_time="2026-08-01T20:00:00", d_time="2026-08-01T08:00:00"),
    )
    assert r.status_code == 422


def test_trip_crud_is_admin_only(client, user_headers, sample_bus):
    r = _create_trip(client, user_headers, sample_bus.id)
    assert r.status_code == 403


def test_public_can_read_trip(client, admin_headers, sample_bus):
    trip_id = _create_trip(client, admin_headers, sample_bus.id).json()["id"]
    r = client.get(f"/trips/{trip_id}")
    assert r.status_code == 200
    assert r.json()["bus"]["number_plate"] == sample_bus.number_plate


def test_search_filters_and_pagination(client, admin_headers, sample_bus):
    # three trips at different prices
    for i, price in enumerate([10, 20, 30], start=1):
        _create_trip(client, admin_headers, sample_bus.id, name=f"T{i}", price=price)

    r = client.get("/trips", params={"min_price": 15, "sort": "price"})
    body = r.json()
    assert r.status_code == 200
    assert body["total"] == 2
    assert [i["price"] for i in body["items"]] == ["20.00", "30.00"]

    r = client.get("/trips", params={"page_size": 1, "page": 1, "sort": "-price"})
    body = r.json()
    assert body["total"] == 3
    assert body["pages"] == 3
    assert len(body["items"]) == 1
    assert body["items"][0]["price"] == "30.00"


def test_admin_can_update_and_delete_trip(client, admin_headers, sample_bus):
    trip_id = _create_trip(client, admin_headers, sample_bus.id).json()["id"]

    r = client.patch(f"/trips/{trip_id}", json={"name": "Renamed"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed"

    r = client.delete(f"/trips/{trip_id}", headers=admin_headers)
    assert r.status_code == 204
    assert client.get(f"/trips/{trip_id}").status_code == 404


def test_search_by_origin_destination(client, admin_headers, sample_bus):
    _create_trip(client, admin_headers, sample_bus.id)  # Kyiv(1) -> Lviv(2)
    # Origin 1 before destination 2 -> match
    assert client.get("/trips", params={"origin": 1, "destination": 2}).json()["total"] == 1
    # Reversed direction -> no match
    assert client.get("/trips", params={"origin": 2, "destination": 1}).json()["total"] == 0
    # Date filter
    assert (
        client.get("/trips", params={"origin": 1, "departure_date": "2026-08-01"}).json()["total"]
        == 1
    )
    assert client.get("/trips", params={"departure_date": "2026-09-09"}).json()["total"] == 0
