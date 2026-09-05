"""Domain exceptions.

Services raise these — never `HTTPException`. The exception handlers in
`app.core.exception_handlers` translate them to HTTP responses at the boundary,
so business logic stays free of transport concerns.
"""


class BaseServiceError(Exception):
    pass


class NotFoundError(BaseServiceError):
    """A requested entity does not exist. Maps to 404."""


class AuthenticationError(BaseServiceError):
    """Credentials are missing or invalid. Maps to 401."""


class AlreadyExistError(BaseServiceError):
    """A uniqueness constraint would be violated. Maps to 409."""


class ConflictError(BaseServiceError):
    """The request cannot be applied against current state (e.g. sold out). Maps to 409."""


class BadRequestError(BaseServiceError):
    """The request references invalid data (e.g. an unknown foreign key). Maps to 400."""


class UnprocessableEntityError(BaseServiceError):
    """The payload is well-formed but semantically invalid (e.g. a corrupt image). Maps to 422."""


class PermissionDeniedError(BaseServiceError):
    """The caller is authenticated but not allowed to access this resource. Maps to 403."""
