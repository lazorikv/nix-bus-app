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

Reserve/release never commit — the caller owns the transaction boundary so a
reservation can be atomically paired with the order write that depends on it.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.infrastructure.db.models import Trip
from app.infrastructure.db.session import get_session


class SeatsService:
    def __init__(self, session: Annotated[Session, Depends(get_session)]) -> None:
        self._session = session

    def reserve(self, trip_id: int, count: int) -> bool:
        """Atomically reserve ``count`` seats. Returns True on success, False if sold out."""
        if count <= 0:
            raise ValueError("count must be positive")
        result = self._session.execute(
            update(Trip)
            .where(Trip.id == trip_id, Trip.seats_left >= count)
            .values(seats_left=Trip.seats_left - count)
            .returning(Trip.seats_left)
        )
        return result.first() is not None

    def release(self, trip_id: int, count: int) -> None:
        """Return ``count`` seats to the trip (e.g. after a failed payment)."""
        if count <= 0:
            raise ValueError("count must be positive")
        self._session.execute(
            update(Trip).where(Trip.id == trip_id).values(seats_left=Trip.seats_left + count)
        )
