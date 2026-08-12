def test_public_can_list_cities(client, admin_headers):
    client.post(
        "/cities",
        json={"name": "Kyiv", "longitude": 30.5, "latitude": 50.4},
        headers=admin_headers,
    )
    r = client.get("/cities")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_admin_can_crud_city(client, admin_headers):
    r = client.post(
        "/cities",
        json={"name": "Lviv", "longitude": 24.0, "latitude": 49.8},
        headers=admin_headers,
    )
    assert r.status_code == 201
    city_id = r.json()["id"]

    r = client.patch(f"/cities/{city_id}", json={"name": "Lviv-2"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "Lviv-2"

    r = client.delete(f"/cities/{city_id}", headers=admin_headers)
    assert r.status_code == 204
    assert client.get(f"/cities/{city_id}").status_code == 404


def test_non_admin_cannot_create_city(client, user_headers):
    r = client.post(
        "/cities",
        json={"name": "X", "longitude": 1.0, "latitude": 1.0},
        headers=user_headers,
    )
    assert r.status_code == 403


def test_anonymous_cannot_create_city(client):
    r = client.post("/cities", json={"name": "X", "longitude": 1.0, "latitude": 1.0})
    assert r.status_code == 401


def test_coordinate_bounds_validation(client, admin_headers):
    r = client.post(
        "/cities",
        json={"name": "Bad", "longitude": 200.0, "latitude": 50.0},
        headers=admin_headers,
    )
    assert r.status_code == 422
