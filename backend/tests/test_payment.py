"""Payment webhook: idempotency, seat restoration on failure, status transitions."""

from decimal import Decimal

from app.models import Order, OrderStatus, Trip
from app.services.payment import OrderNotFound, process_payment
from app.services.seats import reserve_seats


def _make_order(db, trip: Trip, passenger_count: int = 2) -> Order:
    reserve_seats(db, trip.id, passenger_count)
    order = Order(
        trip_id=trip.id,
        user_id=None,
        status=OrderStatus.pending,
        price=Decimal(trip.price) * passenger_count,
        passengers=[
            {
                "first_name": f"P{i}",
                "last_name": "Test",
                "email": f"p{i}@example.com",
                "age": 30,
                "ticket_price": str(trip.price),
            }
            for i in range(passenger_count)
        ],
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def test_success_transitions_to_paid_and_generates_ticket(db, sample_trip):
    order = _make_order(db, sample_trip, 2)

    result = process_payment(db, order.id, success=True)

    assert result.status == OrderStatus.paid
    assert result.applied is True
    db.refresh(order)
    assert order.status == OrderStatus.paid
    assert order.ticket_pdf_key is not None


def test_failure_transitions_to_failed_and_restores_seats(db, sample_trip):
    start_seats = sample_trip.seats_left
    order = _make_order(db, sample_trip, 3)
    db.refresh(sample_trip)
    assert sample_trip.seats_left == start_seats - 3

    result = process_payment(db, order.id, success=False)

    assert result.status == OrderStatus.failed
    assert result.applied is True
    db.refresh(sample_trip)
    assert sample_trip.seats_left == start_seats  # seats restored


def test_webhook_is_idempotent_on_repeated_success(db, sample_trip):
    order = _make_order(db, sample_trip, 1)

    first = process_payment(db, order.id, success=True)
    second = process_payment(db, order.id, success=True)
    third = process_payment(db, order.id, success=False)  # contradictory replay

    assert first.applied is True
    assert second.applied is False  # no-op
    assert third.applied is False  # no-op — terminal status wins
    db.refresh(order)
    assert order.status == OrderStatus.paid


def test_repeated_failure_does_not_double_restore_seats(db, sample_trip):
    start_seats = sample_trip.seats_left
    order = _make_order(db, sample_trip, 2)

    process_payment(db, order.id, success=False)
    process_payment(db, order.id, success=False)  # duplicate delivery

    db.refresh(sample_trip)
    assert sample_trip.seats_left == start_seats  # restored exactly once


def test_unknown_order_raises(db):
    try:
        process_payment(db, 999999, success=True)
        raise AssertionError("expected OrderNotFound")
    except OrderNotFound:
        pass
