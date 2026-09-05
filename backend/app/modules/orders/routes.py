from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import get_current_user, get_current_user_optional
from app.core.pagination import Page
from app.infrastructure.db.models import User
from app.modules.orders.schemas import OrderCreate, OrderOut
from app.modules.orders.service import OrdersService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    creation: OrderCreate,
    service: Annotated[OrdersService, Depends()],
    current: Annotated[User | None, Depends(get_current_user_optional)],
) -> OrderOut:
    return service.create_order(creation, current)


@router.get("", response_model=Page[OrderOut])
def list_orders(
    service: Annotated[OrdersService, Depends()],
    current: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> Page[OrderOut]:
    return service.list_orders(current, page, page_size)


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    service: Annotated[OrdersService, Depends()],
    current: Annotated[User | None, Depends(get_current_user_optional)],
) -> OrderOut:
    return service.get_order_for_user(order_id, current)
