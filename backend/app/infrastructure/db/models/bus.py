from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.mixins import TimestampMixin
from app.infrastructure.db.session import Base


class Bus(TimestampMixin, Base):
    __tablename__ = "buses"
    __table_args__ = (CheckConstraint("seats_quantity >= 0", name="ck_bus_seats_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    color: Mapped[str] = mapped_column(String(50), nullable=False)
    seats_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    number_plate: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    # Object keys in MinIO/S3; presigned URLs are generated on read.
    photo_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
