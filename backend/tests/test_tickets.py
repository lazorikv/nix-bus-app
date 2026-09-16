"""Ticket route rendering: booked segment vs whole trip."""

from app.infrastructure.db.models import Order, Trip
from app.modules.payment.tickets import segment_endpoints


def _trip() -> Trip:
    return Trip(
        name="Poltava - Vinnytsia Nightline",
        price=20,
        bus_id=1,
        seats_left=10,
        route=[
            {"city_id": 1, "city_name": "Poltava", "time": "2026-08-01T08:00:00", "position": 0},
            {"city_id": 2, "city_name": "Kharkiv", "time": "2026-08-01T10:00:00", "position": 1},
            {"city_id": 3, "city_name": "Vinnytsia", "time": "2026-08-01T14:00:00", "position": 2},
        ],
    )


def test_segment_endpoints_uses_booked_segment():
    order = Order(origin_city_name="Kharkiv", destination_city_name="Vinnytsia")
    assert segment_endpoints(order, _trip()) == ("Kharkiv", "Vinnytsia")


def test_segment_endpoints_falls_back_to_whole_trip():
    order = Order()
    assert segment_endpoints(order, _trip()) == ("Poltava", "Vinnytsia")
