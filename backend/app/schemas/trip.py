from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RouteStop(BaseModel):
    city_id: int
    city_name: str
    time: datetime
    position: int = Field(ge=0)


def validate_route(route: list[RouteStop]) -> list[RouteStop]:
    if len(route) < 2:
        raise ValueError("route must contain at least 2 stops")
    # Positions must be unique and increasing along the stop order.
    positions = [stop.position for stop in route]
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise ValueError("route positions must be unique and increasing")
    # Times must be in chronological order following the stop order.
    times = [stop.time for stop in route]
    if times != sorted(times):
        raise ValueError("route stop times must be in chronological order")
    return route


class TripBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    bus_id: int
    route: list[RouteStop]

    @field_validator("route")
    @classmethod
    def _validate_route(cls, route: list[RouteStop]) -> list[RouteStop]:
        return validate_route(route)


class TripCreate(TripBase):
    pass


class TripUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    bus_id: int | None = None
    route: list[RouteStop] | None = None

    @field_validator("route")
    @classmethod
    def _validate_route(cls, route: list[RouteStop] | None) -> list[RouteStop] | None:
        if route is None:
            return route
        return validate_route(route)


class TripOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price: Decimal
    bus_id: int
    seats_left: int
    route: list[RouteStop]
    # Presigned bus thumbnail, populated by trip search so result cards can show a photo.
    bus_thumbnail_url: str | None = None
    created_at: datetime
    updated_at: datetime


class TripDetailOut(TripOut):
    bus: "BusOut | None" = None


class TripSearchPage(BaseModel):
    items: list[TripOut]
    total: int
    page: int
    page_size: int
    pages: int


from app.schemas.bus import BusOut  # noqa: E402

TripDetailOut.model_rebuild()
