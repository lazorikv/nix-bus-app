from decimal import Decimal
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_current_user_optional
from app.database import get_db
from app.models import Order, OrderStatus, Trip, User, UserRole
from app.schemas.order import OrderCreate, OrderOut, OrderPage
from app.services.seats import reserve_seats
from app.storage import presigned_get_url

router = APIRouter(prefix="/orders", tags=["orders"])


def _to_out(order: Order) -> OrderOut:
    out = OrderOut.model_validate(order)
    if order.ticket_pdf_key:
        out.ticket_pdf_url = presigned_get_url(order.ticket_pdf_key)
    return out


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current: User | None = Depends(get_current_user_optional),
) -> OrderOut:
    trip = db.get(Trip, payload.trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    seat_count = len(payload.passengers)
    # Atomic reservation: fails cleanly if not enough seats remain.
    if not reserve_seats(db, trip.id, seat_count):
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Not enough seats available"
        )

    passengers = [
        {**p.model_dump(mode="json"), "ticket_price": str(trip.price)} for p in payload.passengers
    ]
    order = Order(
        trip_id=trip.id,
        user_id=current.id if current is not None else None,
        status=OrderStatus.pending,
        price=Decimal(trip.price) * seat_count,
        passengers=passengers,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _to_out(order)


@router.get("", response_model=OrderPage)
def list_orders(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> OrderPage:
    stmt = select(Order)
    count_stmt = select(func.count()).select_from(Order)
    if current.role != UserRole.admin:
        stmt = stmt.where(Order.user_id == current.id)
        count_stmt = count_stmt.where(Order.user_id == current.id)

    total = db.execute(count_stmt).scalar_one()
    stmt = stmt.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    orders = db.execute(stmt).scalars().all()
    return OrderPage(
        items=[_to_out(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if page_size else 0,
    )


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current: User | None = Depends(get_current_user_optional),
) -> OrderOut:
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    is_admin = current is not None and current.role == UserRole.admin
    is_owner = current is not None and order.user_id == current.id
    is_anonymous_order = order.user_id is None
    # Owner or admin may view; anonymous orders are viewable by id (needed for
    # status polling in the anonymous booking flow).
    if not (is_admin or is_owner or is_anonymous_order):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return _to_out(order)
