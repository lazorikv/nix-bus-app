"""Order creation, listing, retrieval, and cancellation.

Cancellation mirrors the payment webhook's guarantees. The order row is locked
with ``SELECT ... FOR UPDATE`` and the transition is applied only from a
seat-holding status (``pending`` or ``paid``). A repeated cancel finds a
terminal status and becomes a no-op, so seats are restored exactly once.
"""

import logging
from decimal import Decimal
from typing import Annotated

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.logging import log_event
from app.core.pagination import Page
from app.infrastructure.db.models import Order, OrderStatus, Trip, User, UserRole
from app.infrastructure.db.session import get_session
from app.infrastructure.storage import presigned_get_url
from app.modules.orders.schemas import CancelResult, OrderCreate, OrderOut
from app.modules.orders.seats import SeatsService

logger = logging.getLogger("app.orders")

# Statuses that still hold reserved seats and can therefore be cancelled.
_CANCELLABLE = {OrderStatus.pending, OrderStatus.paid}


class OrdersService:
    def __init__(
        self,
        session: Annotated[Session, Depends(get_session)],
        seats: Annotated[SeatsService, Depends()],
    ) -> None:
        self._session = session
        self._seats = seats

    def create_order(self, creation: OrderCreate, current_user: User | None) -> OrderOut:
        trip = self._session.get(Trip, creation.trip_id)
        if trip is None:
            raise NotFoundError(f"Trip(id={creation.trip_id}) not found")

        seat_count = len(creation.passengers)
        # Atomic reservation: fails cleanly if not enough seats remain.
        if not self._seats.reserve(trip.id, seat_count):
            self._session.rollback()
            raise ConflictError("Not enough seats available")

        passengers = [
            {**p.model_dump(mode="json"), "ticket_price": str(trip.price)}
            for p in creation.passengers
        ]
        order = Order(
            trip_id=trip.id,
            user_id=current_user.id if current_user is not None else None,
            status=OrderStatus.pending,
            price=Decimal(trip.price) * seat_count,
            passengers=passengers,
        )
        self._session.add(order)
        self._session.commit()
        self._session.refresh(order)
        return self._to_out(order)

    def list_orders(self, current_user: User, page: int, page_size: int) -> Page[OrderOut]:
        query = select(Order)
        count_query = select(func.count()).select_from(Order)
        if current_user.role != UserRole.admin:
            query = query.where(Order.user_id == current_user.id)
            count_query = count_query.where(Order.user_id == current_user.id)

        total = self._session.execute(count_query).scalar_one()
        query = (
            query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        )
        orders = self._session.execute(query).scalars().all()
        items = [self._to_out(order) for order in orders]
        return Page.create(items=items, total=total, page=page, page_size=page_size)

    def get_order_for_user(self, order_id: int, current_user: User | None) -> OrderOut:
        order = self._session.get(Order, order_id)
        if order is None:
            raise NotFoundError(f"Order(id={order_id}) not found")
        if not self._may_view(order, current_user):
            raise PermissionDeniedError("Forbidden")
        return self._to_out(order)

    def cancel_order(self, order_id: int) -> CancelResult:
        order = self._session.execute(
            select(Order).where(Order.id == order_id).with_for_update()
        ).scalar_one_or_none()
        if order is None:
            raise NotFoundError(f"Order(id={order_id}) not found")

        if order.status not in _CANCELLABLE:
            # Already terminal (failed/refunded) — idempotent replay, do nothing.
            log_event(
                logger,
                logging.INFO,
                "order.cancel.noop",
                order_id=order_id,
                status=order.status.value,
            )
            self._session.commit()
            return CancelResult(order_id=order_id, status=order.status, applied=False)

        self._seats.release(order.trip_id, len(order.passengers))
        order.status = OrderStatus.refunded
        log_event(
            logger,
            logging.INFO,
            "order.cancel.refunded",
            order_id=order_id,
            seats_restored=len(order.passengers),
        )
        self._session.commit()
        self._session.refresh(order)
        return CancelResult(order_id=order_id, status=order.status, applied=True)

    @staticmethod
    def _may_view(order: Order, current_user: User | None) -> bool:
        is_admin = current_user is not None and current_user.role == UserRole.admin
        is_owner = current_user is not None and order.user_id == current_user.id
        # Owner or admin may view; anonymous orders are viewable by id (needed for
        # status polling in the anonymous booking flow).
        is_anonymous_order = order.user_id is None
        return is_admin or is_owner or is_anonymous_order

    @staticmethod
    def _to_out(order: Order) -> OrderOut:
        out = OrderOut.model_validate(order)
        if order.ticket_pdf_key:
            out.ticket_pdf_url = presigned_get_url(order.ticket_pdf_key)
        return out
