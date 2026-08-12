"""Idempotent payment webhook processing.

Idempotency: the order row is locked with ``SELECT ... FOR UPDATE`` and the
transition is applied only when the order is still ``pending``. A repeated
webhook (same order) finds a terminal status and becomes a no-op, so a payment
can never be double-applied and seats can never be double-restored.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logging_config import log_event
from app.models import Order, OrderStatus, Trip
from app.schemas.payment import PaymentResult
from app.services.seats import release_seats
from app.services.tickets import generate_and_store_ticket

logger = logging.getLogger("app.payment")


class OrderNotFound(Exception):
    pass


def process_payment(db: Session, order_id: int, success: bool) -> PaymentResult:
    # Lock the order row for the duration of the transaction.
    order = db.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    ).scalar_one_or_none()

    if order is None:
        raise OrderNotFound(f"order {order_id} not found")

    if order.status != OrderStatus.pending:
        # Terminal status already reached — idempotent replay, do nothing.
        log_event(
            logger,
            logging.INFO,
            "payment.webhook.noop",
            order_id=order_id,
            status=order.status.value,
        )
        db.commit()
        return PaymentResult(order_id=order_id, status=order.status, applied=False)

    if success:
        order.status = OrderStatus.paid
        trip = db.get(Trip, order.trip_id)
        if trip is not None:
            order.ticket_pdf_key = generate_and_store_ticket(order, trip)
        log_event(logger, logging.INFO, "payment.webhook.paid", order_id=order_id)
    else:
        order.status = OrderStatus.failed
        release_seats(db, order.trip_id, len(order.passengers))
        log_event(
            logger,
            logging.INFO,
            "payment.webhook.failed",
            order_id=order_id,
            seats_restored=len(order.passengers),
        )

    db.commit()
    db.refresh(order)
    return PaymentResult(order_id=order_id, status=order.status, applied=True)
