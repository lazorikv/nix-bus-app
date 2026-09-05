from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import require_admin
from app.infrastructure.db.models import City
from app.modules.cities.schemas import CityCreate, CityOut, CityUpdate
from app.modules.cities.service import CitiesService

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=list[CityOut])
def list_cities(service: Annotated[CitiesService, Depends()]) -> list[City]:
    return service.list_cities()


@router.get("/{city_id}", response_model=CityOut)
def get_city(city_id: int, service: Annotated[CitiesService, Depends()]) -> City:
    return service.get_city_by_id(city_id)


@router.post(
    "",
    response_model=CityOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_city(creation: CityCreate, service: Annotated[CitiesService, Depends()]) -> City:
    return service.create_city(creation)


@router.patch("/{city_id}", response_model=CityOut, dependencies=[Depends(require_admin)])
def update_city(
    city_id: int, updates: CityUpdate, service: Annotated[CitiesService, Depends()]
) -> City:
    return service.update_city(city_id, updates)


@router.delete(
    "/{city_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    dependencies=[Depends(require_admin)],
)
def delete_city(city_id: int, service: Annotated[CitiesService, Depends()]) -> None:
    service.delete_city_by_id(city_id)
