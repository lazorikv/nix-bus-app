"""Translate domain exceptions to HTTP responses.

Registered last in `create_app()` so they wrap all routers and middleware.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AlreadyExistError,
    AuthenticationError,
    BadRequestError,
    BaseServiceError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnprocessableEntityError,
)

_STATUS_BY_EXCEPTION: dict[type[BaseServiceError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    AlreadyExistError: status.HTTP_409_CONFLICT,
    ConflictError: status.HTTP_409_CONFLICT,
    BadRequestError: status.HTTP_400_BAD_REQUEST,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    UnprocessableEntityError: 422,
}

_DEFAULT_DETAIL = {
    status.HTTP_404_NOT_FOUND: "Not Found",
    status.HTTP_401_UNAUTHORIZED: "Unauthorized",
    status.HTTP_409_CONFLICT: "Conflict",
    status.HTTP_400_BAD_REQUEST: "Bad Request",
    status.HTTP_403_FORBIDDEN: "Forbidden",
    422: "Unprocessable Entity",
}


def _status_for(exc: BaseServiceError) -> int:
    # Walk the MRO so a module-specific subclass maps to its base's status.
    for klass in type(exc).__mro__:
        if klass in _STATUS_BY_EXCEPTION:
            return _STATUS_BY_EXCEPTION[klass]
    return status.HTTP_500_INTERNAL_SERVER_ERROR


def _service_error_handler(request: Request, exc: BaseServiceError) -> JSONResponse:
    status_code = _status_for(exc)
    detail = str(exc) or _DEFAULT_DETAIL.get(status_code, "Error")
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(BaseServiceError, _service_error_handler)  # type: ignore[arg-type]
