import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.infrastructure.db.models import User, UserRole
from app.infrastructure.db.session import get_session

# auto_error=False so the same scheme works for optional auth (anonymous orders).
bearer_scheme = HTTPBearer(auto_error=False)


def _user_from_credentials(
    credentials: HTTPAuthorizationCredentials | None, session: Session
) -> User | None:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    sub = payload.get("sub")
    if sub is None:
        return None
    return session.get(User, int(sub))


def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User | None:
    """Return the authenticated user, or None for anonymous access."""
    return _user_from_credentials(credentials, session)


def get_current_user(
    user: Annotated[User | None, Depends(get_current_user_optional)],
) -> User:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def verify_webhook_secret(x_webhook_secret: Annotated[str | None, Header()] = None) -> None:
    """Authenticate an incoming payment webhook via a shared secret.

    A real gateway signs its callbacks; without this, anyone who can guess an
    ``order_id`` could flip an arbitrary order to ``paid`` (free tickets) or
    ``failed`` (release another customer's seats). Compared in constant time.
    """
    expected = settings.payment_webhook_secret
    if x_webhook_secret is None or not hmac.compare_digest(x_webhook_secret, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user
