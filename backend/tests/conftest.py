import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Point the app at the test database *before* importing app modules.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://bus:bus@localhost:5433/bus_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Bus, Trip, User, UserRole  # noqa: E402

engine = create_engine(TEST_DATABASE_URL, future=True)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@pytest.fixture(scope="session", autouse=True)
def _create_schema() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables() -> Generator[None, None, None]:
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.exec_driver_sql(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE')


@pytest.fixture
def db() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _mock_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub object storage so tests never touch MinIO."""
    import app.routers.orders as orders_mod
    import app.services.photos as photos_mod
    import app.services.tickets as tickets_mod

    monkeypatch.setattr(photos_mod, "upload_bytes", lambda *a, **k: None)
    monkeypatch.setattr(
        photos_mod, "presigned_get_url", lambda key, *a, **k: f"https://minio.test/{key}"
    )
    monkeypatch.setattr(tickets_mod, "upload_bytes", lambda *a, **k: None)
    monkeypatch.setattr(
        orders_mod, "presigned_get_url", lambda key, *a, **k: f"https://minio.test/{key}"
    )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---- Domain fixtures -------------------------------------------------------


@pytest.fixture
def admin_user(db: Session) -> User:
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def normal_user(db: Session) -> User:
    user = User(
        email="user@example.com",
        hashed_password=hash_password("password123"),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    token = create_access_token(subject=str(admin_user.id), role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(normal_user: User) -> dict[str, str]:
    token = create_access_token(subject=str(normal_user.id), role="user")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_bus(db: Session) -> Bus:
    bus = Bus(color="red", seats_quantity=40, number_plate="AA-123-BB")
    db.add(bus)
    db.commit()
    db.refresh(bus)
    return bus


@pytest.fixture
def sample_trip(db: Session, sample_bus: Bus) -> Trip:
    trip = Trip(
        name="Kyiv - Lviv",
        price=25.00,
        bus_id=sample_bus.id,
        seats_left=sample_bus.seats_quantity,
        route=[
            {"city_id": 1, "city_name": "Kyiv", "time": "2026-08-01T08:00:00", "position": 0},
            {"city_id": 2, "city_name": "Lviv", "time": "2026-08-01T15:00:00", "position": 1},
        ],
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip
