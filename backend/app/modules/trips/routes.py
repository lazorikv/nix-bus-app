from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import require_admin
from app.core.pagination import Page
from app.infrastructure.db.models import Trip
from app.modules.trips.schemas import (
    TripCreate,
    TripDetailOut,
    TripOut,
    TripSearchParams,
    TripUpdate,
)
from app.modules.trips.service import TripsService

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("", response_model=Page[TripOut])
def search_trips(
    service: Annotated[TripsService, Depends()],
    params: Annotated[TripSearchParams, Query()],
) -> Page[TripOut]:
    return service.search_trips(params)


@router.get("/{trip_id}", response_model=TripDetailOut)
def get_trip(trip_id: int, service: Annotated[TripsService, Depends()]) -> TripDetailOut:
    return service.get_trip_by_id(trip_id)


@router.post(
    "",
    response_model=TripOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_trip(creation: TripCreate, service: Annotated[TripsService, Depends()]) -> Trip:
    return service.create_trip(creation)


@router.patch("/{trip_id}", response_model=TripOut, dependencies=[Depends(require_admin)])
def update_trip(
    trip_id: int, updates: TripUpdate, service: Annotated[TripsService, Depends()]
) -> Trip:
    return service.update_trip(trip_id, updates)


@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_admin)],
)
def delete_trip(trip_id: int, service: Annotated[TripsService, Depends()]) -> None:
    service.delete_trip_by_id(trip_id)
