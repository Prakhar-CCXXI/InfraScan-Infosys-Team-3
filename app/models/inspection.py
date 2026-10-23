from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base , get_db
from app.schemas.inspection import InfrastructureType


class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    infrastructure_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    infrastructure_type: Mapped[InfrastructureType] = mapped_column(
        SAEnum(InfrastructureType, name="infrastructure_type", native_enum=False), nullable=False
    )
    location: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending", server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
