from pydantic import BaseModel

from app.models import OrderStatus


class PaymentWebhook(BaseModel):
    order_id: int
    success: bool


class PaymentResult(BaseModel):
    order_id: int
    status: OrderStatus
    applied: bool  # False when the webhook was a no-op (idempotent replay)
