from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import get_current_user
from app.infrastructure.db.models import User
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest, service: Annotated[AuthService, Depends()]) -> User:
    return service.register(request)


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, service: Annotated[AuthService, Depends()]) -> TokenResponse:
    return service.login(request)


@router.get("/me", response_model=UserOut)
def me(current: Annotated[User, Depends(get_current_user)]) -> User:
    return current
