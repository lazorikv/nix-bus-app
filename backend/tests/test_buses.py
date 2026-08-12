import io

from PIL import Image


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), color="red").save(buf, format="PNG")
    return buf.getvalue()


def test_admin_can_crud_bus(client, admin_headers):
    r = client.post(
        "/buses",
        json={"color": "red", "seats_quantity": 30, "number_plate": "AA-100-BB"},
        headers=admin_headers,
    )
    assert r.status_code == 201
    bus_id = r.json()["id"]

    r = client.patch(f"/buses/{bus_id}", json={"color": "blue"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["color"] == "blue"

    r = client.get(f"/buses/{bus_id}", headers=admin_headers)
    assert r.status_code == 200

    r = client.delete(f"/buses/{bus_id}", headers=admin_headers)
    assert r.status_code == 204


def test_bus_endpoints_are_admin_only(client, user_headers):
    assert client.get("/buses", headers=user_headers).status_code == 403
    assert client.get("/buses").status_code == 401


def test_duplicate_number_plate_rejected(client, admin_headers):
    payload = {"color": "red", "seats_quantity": 10, "number_plate": "DUP-1"}
    assert client.post("/buses", json=payload, headers=admin_headers).status_code == 201
    assert client.post("/buses", json=payload, headers=admin_headers).status_code == 409


def test_negative_seats_rejected(client, admin_headers):
    r = client.post(
        "/buses",
        json={"color": "red", "seats_quantity": -1, "number_plate": "NEG-1"},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_photo_upload_accepts_png(client, admin_headers):
    bus_id = client.post(
        "/buses",
        json={"color": "red", "seats_quantity": 10, "number_plate": "PIC-1"},
        headers=admin_headers,
    ).json()["id"]

    r = client.post(
        f"/buses/{bus_id}/photo",
        files={"file": ("bus.png", _png_bytes(), "image/png")},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["photo_url"] is not None
    assert r.json()["thumbnail_url"] is not None


def test_photo_upload_rejects_non_image(client, admin_headers):
    bus_id = client.post(
        "/buses",
        json={"color": "red", "seats_quantity": 10, "number_plate": "PIC-2"},
        headers=admin_headers,
    ).json()["id"]

    r = client.post(
        f"/buses/{bus_id}/photo",
        files={"file": ("evil.txt", b"not an image", "text/plain")},
        headers=admin_headers,
    )
    assert r.status_code == 422
