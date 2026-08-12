from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BusBase(BaseModel):
    color: str = Field(min_length=1, max_length=50)
    seats_quantity: int = Field(ge=0)
    number_plate: str = Field(min_length=1, max_length=20)


class BusCreate(BusBase):
    pass


class BusUpdate(BaseModel):
    color: str | None = Field(default=None, min_length=1, max_length=50)
    seats_quantity: int | None = Field(default=None, ge=0)
    number_plate: str | None = Field(default=None, min_length=1, max_length=20)


class BusOut(BusBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    photo_url: str | None = None
    thumbnail_url: str | None = None
    created_at: datetime
    updated_at: datetime
