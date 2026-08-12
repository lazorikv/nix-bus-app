from datetime import date
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models import Bus, Trip
from app.schemas.bus import BusOut
from app.schemas.trip import (
    TripCreate,
    TripDetailOut,
    TripOut,
    TripSearchPage,
    TripUpdate,
)
from app.services.photos import photo_urls

router = APIRouter(prefix="/trips", tags=["trips"])

SortField = str


def _stop_index(route: list[dict], city_id: int) -> int | None:
    for i, stop in enumerate(route):
        if stop.get("city_id") == city_id:
            return i
    return None


def _matches_search(
    trip: Trip,
    origin: int | None,
    destination: int | None,
    departure_date: date | None,
) -> bool:
    route = trip.route or []
    origin_idx = _stop_index(route, origin) if origin is not None else None
    dest_idx = _stop_index(route, destination) if destination is not None else None

    if origin is not None and origin_idx is None:
        return False
    if destination is not None and dest_idx is None:
        return False
    # Origin must come before destination on the route.
    if origin_idx is not None and dest_idx is not None and origin_idx >= dest_idx:
        return False

    if departure_date is not None:
        ref_idx = origin_idx if origin_idx is not None else 0
        stop_time = route[ref_idx].get("time", "") if route else ""
        if not str(stop_time).startswith(departure_date.isoformat()):
            return False
    return True


@router.get("", response_model=TripSearchPage)
def search_trips(
    db: Session = Depends(get_db),
    origin: int | None = Query(default=None, description="Origin city id"),
    destination: int | None = Query(default=None, description="Destination city id"),
    departure_date: date | None = Query(default=None),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_seats: int | None = Query(default=None, ge=0),
    sort: str = Query(default="price", pattern="^(price|-price|seats_left|-seats_left)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
) -> TripSearchPage:
    stmt = select(Trip)
    if min_price is not None:
        stmt = stmt.where(Trip.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Trip.price <= max_price)
    if min_seats is not None:
        stmt = stmt.where(Trip.seats_left >= min_seats)

    trips = list(db.execute(stmt).scalars().all())
    # Route-aware filters (origin/destination ordering, date) applied in Python.
    trips = [t for t in trips if _matches_search(t, origin, destination, departure_date)]

    reverse = sort.startswith("-")
    key = sort.lstrip("-")
    trips.sort(key=lambda t: getattr(t, key), reverse=reverse)

    total = len(trips)
    start = (page - 1) * page_size
    page_items = trips[start : start + page_size]

    items = []
    for t in page_items:
        out = TripOut.model_validate(t)
        if t.bus is not None and t.bus.thumbnail_key:
            _, out.bus_thumbnail_url = photo_urls(None, t.bus.thumbnail_key)
        items.append(out)

    return TripSearchPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if page_size else 0,
    )


@router.get("/{trip_id}", response_model=TripDetailOut)
def get_trip(trip_id: int, db: Session = Depends(get_db)) -> TripDetailOut:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    detail = TripDetailOut.model_validate(trip)
    if trip.bus is not None:
        photo_url, thumb_url = photo_urls(trip.bus.photo_key, trip.bus.thumbnail_key)
        detail.bus = BusOut(
            id=trip.bus.id,
            color=trip.bus.color,
            seats_quantity=trip.bus.seats_quantity,
            number_plate=trip.bus.number_plate,
            photo_url=photo_url,
            thumbnail_url=thumb_url,
            created_at=trip.bus.created_at,
            updated_at=trip.bus.updated_at,
        )
    return detail


@router.post(
    "",
    response_model=TripOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_trip(payload: TripCreate, db: Session = Depends(get_db)) -> Trip:
    bus = db.get(Bus, payload.bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="bus_id does not exist")
    data = payload.model_dump(mode="json")
    trip = Trip(
        name=data["name"],
        price=payload.price,
        bus_id=payload.bus_id,
        route=data["route"],
        seats_left=bus.seats_quantity,  # seats_left starts at bus capacity
    )
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.patch("/{trip_id}", response_model=TripOut, dependencies=[Depends(require_admin)])
def update_trip(trip_id: int, payload: TripUpdate, db: Session = Depends(get_db)) -> Trip:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    data = payload.model_dump(mode="json", exclude_unset=True)
    if "bus_id" in data and data["bus_id"] is not None:
        if db.get(Bus, data["bus_id"]) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="bus_id does not exist"
            )
    for field, value in data.items():
        setattr(trip, field, value)
    db.commit()
    db.refresh(trip)
    return trip


@router.delete(
    "/{trip_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)]
)
def delete_trip(trip_id: int, db: Session = Depends(get_db)) -> None:
    trip = db.get(Trip, trip_id)
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    db.delete(trip)
    db.commit()
