"""Order cancellation with seat restoration.

Mirrors the payment webhook's guarantees. The order row is locked with
``SELECT ... FOR UPDATE`` and the transition is applied only from a
seat-holding status (``pending`` or ``paid``). A repeated cancel finds a
terminal status and becomes a no-op, so seats are restored exactly once.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.logging_config import log_event
from app.models import Order, OrderStatus
from app.schemas.order import CancelResult
from app.services.seats import release_seats

logger = logging.getLogger("app.orders")

# Statuses that still hold reserved seats and can therefore be cancelled.
_CANCELLABLE = {OrderStatus.pending, OrderStatus.paid}


class OrderNotFound(Exception):
    pass


def cancel_order(db: Session, order_id: int) -> CancelResult:
    # Lock the order row for the duration of the transaction.
    order = db.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    ).scalar_one_or_none()

    if order is None:
        raise OrderNotFound(f"order {order_id} not found")

    if order.status not in _CANCELLABLE:
        # Already terminal (failed/refunded) — idempotent replay, do nothing.
        log_event(
            logger,
            logging.INFO,
            "order.cancel.noop",
            order_id=order_id,
            status=order.status.value,
        )
        db.commit()
        return CancelResult(order_id=order_id, status=order.status, applied=False)

    release_seats(db, order.trip_id, len(order.passengers))
    order.status = OrderStatus.refunded
    log_event(
        logger,
        logging.INFO,
        "order.cancel.refunded",
        order_id=order_id,
        seats_restored=len(order.passengers),
    )

    db.commit()
    db.refresh(order)
    return CancelResult(order_id=order_id, status=order.status, applied=True)
