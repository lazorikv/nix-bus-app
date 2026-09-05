from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AlreadyExistError, NotFoundError
from app.infrastructure.db.models import Bus
from app.infrastructure.db.session import get_session
from app.modules.buses.photos import photo_urls, process_and_upload
from app.modules.buses.schemas import BusCreate, BusOut, BusUpdate


class BusesService:
    def __init__(self, session: Annotated[Session, Depends(get_session)]) -> None:
        self._session = session

    def list_buses(self) -> list[BusOut]:
        buses = self._session.execute(select(Bus).order_by(Bus.id)).scalars().all()
        return [self._to_out(bus) for bus in buses]

    def get_bus_by_id(self, bus_id: int) -> BusOut:
        return self._to_out(self._get_model(bus_id))

    def create_bus(self, creation: BusCreate) -> BusOut:
        if self._plate_taken(creation.number_plate):
            raise AlreadyExistError("number_plate already exists")
        bus = Bus(**creation.model_dump())
        self._session.add(bus)
        self._session.commit()
        self._session.refresh(bus)
        return self._to_out(bus)

    def update_bus(self, bus_id: int, updates: BusUpdate) -> BusOut:
        bus = self._get_model(bus_id)
        for field, value in updates.model_dump(exclude_unset=True).items():
            setattr(bus, field, value)
        self._session.commit()
        self._session.refresh(bus)
        return self._to_out(bus)

    def delete_bus_by_id(self, bus_id: int) -> None:
        bus = self._get_model(bus_id)
        self._session.delete(bus)
        self._session.commit()

    def set_bus_photo(self, bus_id: int, content_type: str, data: bytes) -> BusOut:
        bus = self._get_model(bus_id)
        bus.photo_key, bus.thumbnail_key = process_and_upload(content_type, data)
        self._session.commit()
        self._session.refresh(bus)
        return self._to_out(bus)

    def _get_model(self, bus_id: int) -> Bus:
        bus = self._session.get(Bus, bus_id)
        if bus is None:
            raise NotFoundError(f"Bus(id={bus_id}) not found")
        return bus

    def _plate_taken(self, number_plate: str) -> bool:
        query = select(Bus).where(Bus.number_plate == number_plate)
        return self._session.execute(query).scalar_one_or_none() is not None

    @staticmethod
    def _to_out(bus: Bus) -> BusOut:
        photo_url, thumbnail_url = photo_urls(bus.photo_key, bus.thumbnail_key)
        return BusOut(
            id=bus.id,
            color=bus.color,
            seats_quantity=bus.seats_quantity,
            number_plate=bus.number_plate,
            photo_url=photo_url,
            thumbnail_url=thumbnail_url,
            created_at=bus.created_at,
            updated_at=bus.updated_at,
        )
