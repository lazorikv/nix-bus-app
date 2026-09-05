from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AlreadyExistError, AuthenticationError
from app.core.security import create_access_token, hash_password, verify_password
from app.infrastructure.db.models import User
from app.infrastructure.db.session import get_session
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse


class AuthService:
    def __init__(self, session: Annotated[Session, Depends(get_session)]) -> None:
        self._session = session

    def register(self, request: RegisterRequest) -> User:
        if self._find_by_email(request.email) is not None:
            raise AlreadyExistError("Email already registered")
        user = User(email=request.email, hashed_password=hash_password(request.password))
        self._session.add(user)
        self._session.commit()
        self._session.refresh(user)
        return user

    def login(self, request: LoginRequest) -> TokenResponse:
        user = self._find_by_email(request.email)
        if user is None or not verify_password(request.password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")
        token = create_access_token(subject=str(user.id), role=user.role.value)
        return TokenResponse(access_token=token)

    def _find_by_email(self, email: str) -> User | None:
        return self._session.execute(select(User).where(User.email == email)).scalar_one_or_none()
