from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.models.mixins import TimestampMixin
from app.infrastructure.db.session import Base


class City(TimestampMixin, Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
