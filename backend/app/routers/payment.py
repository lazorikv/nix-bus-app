from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.payment import PaymentResult, PaymentWebhook
from app.services.payment import OrderNotFound, process_payment

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/webhook", response_model=PaymentResult)
def payment_webhook(payload: PaymentWebhook, db: Session = Depends(get_db)) -> PaymentResult:
    """Idempotent payment callback. Safe to deliver more than once per order."""
    try:
        return process_payment(db, payload.order_id, payload.success)
    except OrderNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/simulate/{order_id}", response_model=PaymentResult)
def simulate_payment(
    order_id: int, success: bool = True, db: Session = Depends(get_db)
) -> PaymentResult:
    """Developer helper that triggers the webhook for an order (mock gateway)."""
    try:
        return process_payment(db, order_id, success)
    except OrderNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
