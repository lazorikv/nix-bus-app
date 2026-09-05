"""Concurrency proof for atomic seat reservation.

Many independent connections race to book the last seats of a trip. The
invariant under test: total successful reservations never exceeds capacity and
``seats_left`` never goes negative — no oversell, no phantom reads.
"""

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.db.models import Bus, Trip
from app.modules.orders.seats import SeatsService
from tests.conftest import TEST_DATABASE_URL


def test_concurrent_reservations_never_oversell(db):
    capacity = 20
    attempts = 60  # far more than capacity

    bus = Bus(color="blue", seats_quantity=capacity, number_plate="CONC-1")
    db.add(bus)
    db.commit()
    trip = Trip(
        name="race",
        price=10,
        bus_id=bus.id,
        seats_left=capacity,
        route=[
            {"city_id": 1, "city_name": "A", "time": "2026-08-01T08:00:00", "position": 0},
            {"city_id": 2, "city_name": "B", "time": "2026-08-01T10:00:00", "position": 1},
        ],
    )
    db.add(trip)
    db.commit()
    trip_id = trip.id

    # Each thread gets its own engine/connection to create genuine DB concurrency.
    engine = create_engine(TEST_DATABASE_URL, pool_size=attempts + 5, max_overflow=0)
    Session = sessionmaker(bind=engine)

    results: list[bool] = []
    results_lock = threading.Lock()
    barrier = threading.Barrier(attempts)

    def worker() -> None:
        session = Session()
        try:
            barrier.wait()  # release all threads at once
            ok = SeatsService(session).reserve(trip_id, 1)
            session.commit()
            with results_lock:
                results.append(ok)
        finally:
            session.close()

    threads = [threading.Thread(target=worker) for _ in range(attempts)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    engine.dispose()

    successes = sum(results)
    assert successes == capacity, (
        f"expected exactly {capacity} successful bookings, got {successes}"
    )

    db.expire_all()
    refreshed = db.get(Trip, trip_id)
    assert refreshed.seats_left == 0
    assert refreshed.seats_left >= 0


def test_reserve_fails_when_insufficient(db):
    bus = Bus(color="green", seats_quantity=2, number_plate="CONC-2")
    db.add(bus)
    db.commit()
    trip = Trip(
        name="small",
        price=10,
        bus_id=bus.id,
        seats_left=2,
        route=[
            {"city_id": 1, "city_name": "A", "time": "2026-08-01T08:00:00", "position": 0},
            {"city_id": 2, "city_name": "B", "time": "2026-08-01T10:00:00", "position": 1},
        ],
    )
    db.add(trip)
    db.commit()

    seats = SeatsService(db)
    assert seats.reserve(trip.id, 3) is False  # not enough
    db.commit()
    db.refresh(trip)
    assert trip.seats_left == 2  # unchanged

    assert seats.reserve(trip.id, 2) is True
    db.commit()
    db.refresh(trip)
    assert trip.seats_left == 0
