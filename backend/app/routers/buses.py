from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_admin
from app.database import get_db
from app.models import Bus
from app.schemas.bus import BusCreate, BusOut, BusUpdate
from app.services.photos import InvalidImageError, photo_urls, process_and_upload

router = APIRouter(prefix="/buses", tags=["buses"], dependencies=[Depends(require_admin)])


def _to_out(bus: Bus) -> BusOut:
    photo_url, thumb_url = photo_urls(bus.photo_key, bus.thumbnail_key)
    return BusOut(
        id=bus.id,
        color=bus.color,
        seats_quantity=bus.seats_quantity,
        number_plate=bus.number_plate,
        photo_url=photo_url,
        thumbnail_url=thumb_url,
        created_at=bus.created_at,
        updated_at=bus.updated_at,
    )


@router.get("", response_model=list[BusOut])
def list_buses(db: Session = Depends(get_db)) -> list[BusOut]:
    buses = db.execute(select(Bus).order_by(Bus.id)).scalars().all()
    return [_to_out(b) for b in buses]


@router.get("/{bus_id}", response_model=BusOut)
def get_bus(bus_id: int, db: Session = Depends(get_db)) -> BusOut:
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    return _to_out(bus)


@router.post("", response_model=BusOut, status_code=status.HTTP_201_CREATED)
def create_bus(payload: BusCreate, db: Session = Depends(get_db)) -> BusOut:
    if db.execute(select(Bus).where(Bus.number_plate == payload.number_plate)).scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="number_plate already exists"
        )
    bus = Bus(**payload.model_dump())
    db.add(bus)
    db.commit()
    db.refresh(bus)
    return _to_out(bus)


@router.patch("/{bus_id}", response_model=BusOut)
def update_bus(bus_id: int, payload: BusUpdate, db: Session = Depends(get_db)) -> BusOut:
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(bus, field, value)
    db.commit()
    db.refresh(bus)
    return _to_out(bus)


@router.delete("/{bus_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bus(bus_id: int, db: Session = Depends(get_db)) -> None:
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    db.delete(bus)
    db.commit()


@router.post("/{bus_id}/photo", response_model=BusOut)
def upload_bus_photo(
    bus_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> BusOut:
    bus = db.get(Bus, bus_id)
    if bus is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bus not found")
    data = file.file.read()
    try:
        photo_key, thumb_key = process_and_upload(file.content_type or "", data)
    except InvalidImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    bus.photo_key = photo_key
    bus.thumbnail_key = thumb_key
    db.commit()
    db.refresh(bus)
    return _to_out(bus)
