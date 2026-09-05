from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.infrastructure.db.models import OrderStatus


class PassengerIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    age: int = Field(ge=0, le=150)


class PassengerOut(PassengerIn):
    ticket_price: Decimal


class OrderCreate(BaseModel):
    trip_id: int
    passengers: list[PassengerIn] = Field(min_length=1, max_length=50)


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    trip_id: int
    user_id: int | None
    status: OrderStatus
    price: Decimal
    passengers: list[PassengerOut]
    ticket_pdf_url: str | None = None
    created_at: datetime
    updated_at: datetime


class CancelResult(BaseModel):
    order_id: int
    status: OrderStatus
    applied: bool  # False when the cancel was a no-op (already terminal)
