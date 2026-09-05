"""Payment webhook: idempotency, seat restoration on failure, status transitions."""

from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError
from app.infrastructure.db.models import Order, OrderStatus, Trip
from app.modules.orders.seats import SeatsService
from app.modules.payment.service import PaymentService


def _payment_service(db) -> PaymentService:
    return PaymentService(db, SeatsService(db))


def _make_order(db, trip: Trip, passenger_count: int = 2) -> Order:
    SeatsService(db).reserve(trip.id, passenger_count)
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

    result = _payment_service(db).process(order.id, success=True)

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

    result = _payment_service(db).process(order.id, success=False)

    assert result.status == OrderStatus.failed
    assert result.applied is True
    db.refresh(sample_trip)
    assert sample_trip.seats_left == start_seats  # seats restored


def test_webhook_is_idempotent_on_repeated_success(db, sample_trip):
    order = _make_order(db, sample_trip, 1)
    service = _payment_service(db)

    first = service.process(order.id, success=True)
    second = service.process(order.id, success=True)
    third = service.process(order.id, success=False)  # contradictory replay

    assert first.applied is True
    assert second.applied is False  # no-op
    assert third.applied is False  # no-op — terminal status wins
    db.refresh(order)
    assert order.status == OrderStatus.paid


def test_repeated_failure_does_not_double_restore_seats(db, sample_trip):
    start_seats = sample_trip.seats_left
    order = _make_order(db, sample_trip, 2)
    service = _payment_service(db)

    service.process(order.id, success=False)
    service.process(order.id, success=False)  # duplicate delivery

    db.refresh(sample_trip)
    assert sample_trip.seats_left == start_seats  # restored exactly once


def test_unknown_order_raises(db):
    with pytest.raises(NotFoundError):
        _payment_service(db).process(999999, success=True)
