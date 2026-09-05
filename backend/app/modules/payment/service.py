"""Idempotent payment webhook processing.

Idempotency: the order row is locked with ``SELECT ... FOR UPDATE`` and the
transition is applied only when the order is still ``pending``. A repeated
webhook (same order) finds a terminal status and becomes a no-op, so a payment
can never be double-applied and seats can never be double-restored.
"""

import logging
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import log_event
from app.infrastructure.db.models import Order, OrderStatus, Trip
from app.infrastructure.db.session import get_session
from app.modules.orders.seats import SeatsService
from app.modules.payment.schemas import PaymentResult
from app.modules.payment.tickets import generate_and_store_ticket

logger = logging.getLogger("app.payment")


class PaymentService:
    def __init__(
        self,
        session: Annotated[Session, Depends(get_session)],
        seats: Annotated[SeatsService, Depends()],
    ) -> None:
        self._session = session
        self._seats = seats

    def process(self, order_id: int, success: bool) -> PaymentResult:
        order = self._session.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        ).scalar_one_or_none()
        if order is None:
            raise NotFoundError(f"Order(id={order_id}) not found")

        if order.status != OrderStatus.pending:
            # Terminal status already reached — idempotent replay, do nothing.
            log_event(
                logger,
                logging.INFO,
                "payment.webhook.noop",
                order_id=order_id,
                status=order.status.value,
            )
            self._session.commit()
            return PaymentResult(order_id=order_id, status=order.status, applied=False)

        if success:
            order.status = OrderStatus.paid
            trip = self._session.get(Trip, order.trip_id)
            if trip is not None:
                order.ticket_pdf_key = generate_and_store_ticket(order, trip)
            log_event(logger, logging.INFO, "payment.webhook.paid", order_id=order_id)
        else:
            order.status = OrderStatus.failed
            self._seats.release(order.trip_id, len(order.passengers))
            log_event(
                logger,
                logging.INFO,
                "payment.webhook.failed",
                order_id=order_id,
                seats_restored=len(order.passengers),
            )

        self._session.commit()
        self._session.refresh(order)
        return PaymentResult(order_id=order_id, status=order.status, applied=True)
