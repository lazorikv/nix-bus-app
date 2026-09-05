from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.infrastructure.db.models import City
from app.infrastructure.db.session import get_session
from app.modules.cities.schemas import CityCreate, CityUpdate


class CitiesService:
    def __init__(self, session: Annotated[Session, Depends(get_session)]) -> None:
        self._session = session

    def list_cities(self) -> list[City]:
        return list(self._session.execute(select(City).order_by(City.name)).scalars().all())

    def get_city_by_id(self, city_id: int) -> City:
        city = self._session.get(City, city_id)
        if city is None:
            raise NotFoundError(f"City(id={city_id}) not found")
        return city

    def create_city(self, creation: CityCreate) -> City:
        city = City(**creation.model_dump())
        self._session.add(city)
        self._session.commit()
        self._session.refresh(city)
        return city

    def update_city(self, city_id: int, updates: CityUpdate) -> City:
        city = self.get_city_by_id(city_id)
        for field, value in updates.model_dump(exclude_unset=True).items():
            setattr(city, field, value)
        self._session.commit()
        self._session.refresh(city)
        return city

    def delete_city_by_id(self, city_id: int) -> None:
        city = self.get_city_by_id(city_id)
        self._session.delete(city)
        self._session.commit()
