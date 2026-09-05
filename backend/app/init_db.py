"""Create tables from the SQLAlchemy models and bootstrap the first admin.

Run once at container/app startup. Idempotent: create_all only adds missing
tables, and the admin is created only if it does not yet exist.
"""

import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import configure_logging, log_event
from app.core.security import hash_password
from app.infrastructure.db.models import User, UserRole  # noqa: F401 (registers models)
from app.infrastructure.db.session import Base, SessionLocal, engine

logger = logging.getLogger("app.init")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

    # Ensure the object-storage bucket exists (best-effort; storage may be
    # unavailable in some environments).
    try:
        from app.infrastructure.storage import ensure_bucket

        ensure_bucket()
        log_event(logger, logging.INFO, "init.bucket_ready")
    except Exception as exc:  # noqa: BLE001
        log_event(logger, logging.WARNING, "init.bucket_failed", error=str(exc))

    if settings.first_admin_email and settings.first_admin_password:
        with SessionLocal() as db:
            exists = db.execute(
                select(User).where(User.email == settings.first_admin_email)
            ).scalar_one_or_none()
            if exists is None:
                admin = User(
                    email=settings.first_admin_email,
                    hashed_password=hash_password(settings.first_admin_password),
                    role=UserRole.admin,
                )
                db.add(admin)
                db.commit()
                log_event(
                    logger, logging.INFO, "init.admin_created", email=settings.first_admin_email
                )


if __name__ == "__main__":
    configure_logging()
    init_db()
