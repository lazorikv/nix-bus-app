"""Atomic seat reservation.

Correctness under concurrency relies on a single conditional UPDATE:

    UPDATE trips SET seats_left = seats_left - :n
    WHERE id = :id AND seats_left >= :n
    RETURNING seats_left

Postgres takes a row lock for the duration of the UPDATE, so concurrent
reservations are serialized on that row. The ``seats_left >= n`` predicate is
evaluated against the locked, current value — there is no read-then-write gap
and therefore no phantom read / oversell. The CHECK constraint
``seats_left >= 0`` is a belt-and-suspenders guard at the schema level.
"""

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Trip


def reserve_seats(db: Session, trip_id: int, count: int) -> bool:
    """Atomically reserve ``count`` seats. Returns True on success, False if sold out."""
    if count <= 0:
        raise ValueError("count must be positive")
    result = db.execute(
        update(Trip)
        .where(Trip.id == trip_id, Trip.seats_left >= count)
        .values(seats_left=Trip.seats_left - count)
        .returning(Trip.seats_left)
    )
    return result.first() is not None


def release_seats(db: Session, trip_id: int, count: int) -> None:
    """Return ``count`` seats to the trip (e.g. after a failed payment)."""
    if count <= 0:
        raise ValueError("count must be positive")
    db.execute(update(Trip).where(Trip.id == trip_id).values(seats_left=Trip.seats_left + count))
