from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.core.deps import require_admin
from app.modules.buses.schemas import BusCreate, BusOut, BusUpdate
from app.modules.buses.service import BusesService

router = APIRouter(prefix="/buses", tags=["buses"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[BusOut])
def list_buses(service: Annotated[BusesService, Depends()]) -> list[BusOut]:
    return service.list_buses()


@router.get("/{bus_id}", response_model=BusOut)
def get_bus(bus_id: int, service: Annotated[BusesService, Depends()]) -> BusOut:
    return service.get_bus_by_id(bus_id)


@router.post("", response_model=BusOut, status_code=status.HTTP_201_CREATED)
def create_bus(creation: BusCreate, service: Annotated[BusesService, Depends()]) -> BusOut:
    return service.create_bus(creation)


@router.patch("/{bus_id}", response_model=BusOut)
def update_bus(
    bus_id: int, updates: BusUpdate, service: Annotated[BusesService, Depends()]
) -> BusOut:
    return service.update_bus(bus_id, updates)


@router.delete("/{bus_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_bus(bus_id: int, service: Annotated[BusesService, Depends()]) -> None:
    service.delete_bus_by_id(bus_id)


@router.post("/{bus_id}/photo", response_model=BusOut)
def upload_bus_photo(
    bus_id: int,
    service: Annotated[BusesService, Depends()],
    file: Annotated[UploadFile, File()],
) -> BusOut:
    return service.set_bus_photo(bus_id, file.content_type or "", file.file.read())
