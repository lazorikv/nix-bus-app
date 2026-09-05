from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.deps import verify_webhook_secret
from app.core.exceptions import NotFoundError
from app.modules.payment.schemas import PaymentResult, PaymentWebhook
from app.modules.payment.service import PaymentService

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post(
    "/webhook", response_model=PaymentResult, dependencies=[Depends(verify_webhook_secret)]
)
def payment_webhook(
    payload: PaymentWebhook, service: Annotated[PaymentService, Depends()]
) -> PaymentResult:
    """Idempotent payment callback. Safe to deliver more than once per order.

    Authenticated with a shared secret (``X-Webhook-Secret``) so only the payment
    gateway can drive order status.
    """
    return service.process(payload.order_id, payload.success)


@router.post("/simulate/{order_id}", response_model=PaymentResult)
def simulate_payment(
    order_id: int,
    service: Annotated[PaymentService, Depends()],
    success: bool = True,
) -> PaymentResult:
    """Developer helper that triggers the webhook for an order (mock gateway).

    Disabled outside non-production environments so it can never stand in for a
    real payment on a deployed instance.
    """
    if settings.environment == "production":
        raise NotFoundError("Not found")
    return service.process(order_id, success)
