from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.pagination import Page
from app.infrastructure.db.models import Bus, Trip
from app.infrastructure.db.session import get_session
from app.modules.buses.photos import photo_urls
from app.modules.buses.schemas import BusOut
from app.modules.trips.schemas import (
    TripCreate,
    TripDetailOut,
    TripOut,
    TripSearchParams,
    TripUpdate,
)


class TripsService:
    def __init__(self, session: Annotated[Session, Depends(get_session)]) -> None:
        self._session = session

    def search_trips(self, params: TripSearchParams) -> Page[TripOut]:
        query = select(Trip)
        if params.min_price is not None:
            query = query.where(Trip.price >= params.min_price)
        if params.max_price is not None:
            query = query.where(Trip.price <= params.max_price)
        if params.min_seats is not None:
            query = query.where(Trip.seats_left >= params.min_seats)

        trips = list(self._session.execute(query).scalars().all())
        # Route-aware filters (origin/destination ordering, date) applied in Python.
        trips = [trip for trip in trips if self._matches_search(trip, params)]

        reverse = params.sort.startswith("-")
        sort_key = params.sort.lstrip("-")
        trips.sort(key=lambda trip: getattr(trip, sort_key), reverse=reverse)

        start = (params.page - 1) * params.page_size
        page_items = trips[start : start + params.page_size]
        items = [self._to_out(trip) for trip in page_items]
        return Page.create(
            items=items, total=len(trips), page=params.page, page_size=params.page_size
        )

    def get_trip_by_id(self, trip_id: int) -> TripDetailOut:
        trip = self._get_model(trip_id)
        detail = TripDetailOut.model_validate(trip)
        if trip.bus is not None:
            photo_url, thumbnail_url = photo_urls(trip.bus.photo_key, trip.bus.thumbnail_key)
            detail.bus = BusOut(
                id=trip.bus.id,
                color=trip.bus.color,
                seats_quantity=trip.bus.seats_quantity,
                number_plate=trip.bus.number_plate,
                photo_url=photo_url,
                thumbnail_url=thumbnail_url,
                created_at=trip.bus.created_at,
                updated_at=trip.bus.updated_at,
            )
        return detail

    def create_trip(self, creation: TripCreate) -> Trip:
        bus = self._require_bus(creation.bus_id)
        data = creation.model_dump(mode="json")
        trip = Trip(
            name=data["name"],
            price=creation.price,
            bus_id=creation.bus_id,
            route=data["route"],
            seats_left=bus.seats_quantity,  # seats_left starts at bus capacity
        )
        self._session.add(trip)
        self._session.commit()
        self._session.refresh(trip)
        return trip

    def update_trip(self, trip_id: int, updates: TripUpdate) -> Trip:
        trip = self._get_model(trip_id)
        data = updates.model_dump(mode="json", exclude_unset=True)
        if data.get("bus_id") is not None:
            self._require_bus(data["bus_id"])
        for field, value in data.items():
            setattr(trip, field, value)
        self._session.commit()
        self._session.refresh(trip)
        return trip

    def delete_trip_by_id(self, trip_id: int) -> None:
        trip = self._get_model(trip_id)
        self._session.delete(trip)
        self._session.commit()

    def _get_model(self, trip_id: int) -> Trip:
        trip = self._session.get(Trip, trip_id)
        if trip is None:
            raise NotFoundError(f"Trip(id={trip_id}) not found")
        return trip

    def _require_bus(self, bus_id: int) -> Bus:
        bus = self._session.get(Bus, bus_id)
        if bus is None:
            raise BadRequestError("bus_id does not exist")
        return bus

    @staticmethod
    def _to_out(trip: Trip) -> TripOut:
        out = TripOut.model_validate(trip)
        if trip.bus is not None and trip.bus.thumbnail_key:
            _, out.bus_thumbnail_url = photo_urls(None, trip.bus.thumbnail_key)
        return out

    @staticmethod
    def _matches_search(trip: Trip, params: TripSearchParams) -> bool:
        route: list[dict] = trip.route or []
        origin_idx = TripsService._stop_index(route, params.origin)
        dest_idx = TripsService._stop_index(route, params.destination)

        if params.origin is not None and origin_idx is None:
            return False
        if params.destination is not None and dest_idx is None:
            return False
        # Origin must come before destination on the route.
        if origin_idx is not None and dest_idx is not None and origin_idx >= dest_idx:
            return False

        if params.departure_date is not None:
            ref_idx = origin_idx if origin_idx is not None else 0
            stop_time = route[ref_idx].get("time", "") if route else ""
            if not str(stop_time).startswith(params.departure_date.isoformat()):
                return False
        return True

    @staticmethod
    def _stop_index(route: list[dict], city_id: int | None) -> int | None:
        if city_id is None:
            return None
        for index, stop in enumerate(route):
            if stop.get("city_id") == city_id:
                return index
        return None
