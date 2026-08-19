"""Order cancellation: seat restoration, idempotency, status transitions.

Mirrors the payment webhook guarantees — a cancel restores seats exactly once
and a repeated cancel is a no-op.
"""

from decimal import Decimal

from app.models import Order, OrderStatus, Trip
from app.services.orders import OrderNotFound, cancel_order
from app.services.seats import reserve_seats


def _make_order(
    db, trip: Trip, passenger_count: int = 2, status: OrderStatus = OrderStatus.paid
) -> Order:
    reserve_seats(db, trip.id, passenger_count)
    order = Order(
        trip_id=trip.id,
        user_id=None,
        status=status,
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


def test_cancel_paid_order_restores_seats_and_sets_refunded(db, sample_trip):
    start_seats = sample_trip.seats_left
    order = _make_order(db, sample_trip, 3, status=OrderStatus.paid)
    db.refresh(sample_trip)
    assert sample_trip.seats_left == start_seats - 3

    result = cancel_order(db, order.id)

    assert result.status == OrderStatus.refunded
    assert result.applied is True
    db.refresh(order)
    assert order.status == OrderStatus.refunded
    db.refresh(sample_trip)
    assert sample_trip.seats_left == start_seats  # seats restored


def test_cancel_is_idempotent_and_restores_seats_once(db, sample_trip):
    start_seats = sample_trip.seats_left
    order = _make_order(db, sample_trip, 2, status=OrderStatus.paid)

    first = cancel_order(db, order.id)
    second = cancel_order(db, order.id)  # duplicate request

    assert first.applied is True
    assert second.applied is False  # no-op
    db.refresh(order)
    assert order.status == OrderStatus.refunded
    db.refresh(sample_trip)
    assert sample_trip.seats_left == start_seats  # restored exactly once


def test_cancel_pending_order_also_restores_seats(db, sample_trip):
    start_seats = sample_trip.seats_left
    order = _make_order(db, sample_trip, 1, status=OrderStatus.pending)

    result = cancel_order(db, order.id)

    assert result.applied is True
    assert result.status == OrderStatus.refunded
    db.refresh(sample_trip)
    assert sample_trip.seats_left == start_seats


def test_cancel_failed_order_is_noop(db, sample_trip):
    order = _make_order(db, sample_trip, 2, status=OrderStatus.failed)

    result = cancel_order(db, order.id)

    assert result.applied is False
    db.refresh(order)
    assert order.status == OrderStatus.failed  # unchanged


def test_cancel_unknown_order_raises(db):
    try:
        cancel_order(db, 999999)
        raise AssertionError("expected OrderNotFound")
    except OrderNotFound:
        pass
