import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import configure_logging, get_logger, log_event
from app.infrastructure.db.session import get_session
from app.router import create_router


def create_app() -> FastAPI:
    configure_logging()
    logger = get_logger("app.request")

    app = FastAPI(title=settings.app_name, version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid.uuid4())
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log_event(
                logger,
                logging.ERROR,
                "request.error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
            )
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log_event(
            logger,
            logging.INFO,
            "request.completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            logger,
            logging.ERROR,
            "request.unhandled_exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness probe — the process is up. No external dependencies checked."""
        return {"status": "ok"}

    @app.get("/health/ready", tags=["meta"])
    def readiness(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
        """Readiness probe — verifies the database is reachable."""
        try:
            session.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=503, detail="Database unavailable") from exc
        return {"status": "ready"}

    app.include_router(create_router())
    # Registered last so they wrap all routers and middleware.
    register_exception_handlers(app)
    return app


app = create_app()
