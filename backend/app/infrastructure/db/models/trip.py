from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.models.mixins import TimestampMixin
from app.infrastructure.db.session import Base


class Trip(TimestampMixin, Base):
    __tablename__ = "trips"
    __table_args__ = (CheckConstraint("seats_left >= 0", name="ck_trip_seats_left_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    bus_id: Mapped[int] = mapped_column(ForeignKey("buses.id", ondelete="RESTRICT"), nullable=False)
    seats_left: Mapped[int] = mapped_column(Integer, nullable=False)
    # Ordered list of stops: [{"city_id": int, "city_name": str, "time": iso8601, "position": int}]
    route: Mapped[list] = mapped_column(JSONB, nullable=False)

    bus = relationship("Bus")
