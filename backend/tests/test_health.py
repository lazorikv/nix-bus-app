"""Health/readiness probe tests."""

from collections.abc import Generator

from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app.main import app


def test_health_is_ok(client) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_readiness_ok_when_db_reachable(client) -> None:
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


def test_readiness_503_when_db_unreachable(client) -> None:
    class _BrokenSession:
        def execute(self, *args: object, **kwargs: object) -> None:
            raise SQLAlchemyError("connection refused")

        def close(self) -> None:
            pass

    def _broken_db() -> Generator[_BrokenSession, None, None]:
        yield _BrokenSession()

    app.dependency_overrides[get_db] = _broken_db
    try:
        resp = client.get("/health/ready")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 503
    assert resp.json()["detail"] == "Database unavailable"
