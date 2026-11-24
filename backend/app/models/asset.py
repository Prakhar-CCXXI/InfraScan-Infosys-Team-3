"""SQLAlchemy model representing monitored civil infrastructure assets."""

from datetime import datetime
import enum
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base

if TYPE_CHECKING:
    from backend.app.models.inspection import Inspection


class AssetType(str, enum.Enum):
    """Allowed structural infrastructure categories."""

    BRIDGE = "BRIDGE"
    ROAD = "ROAD"
    BUILDING = "BUILDING"
    TUNNEL = "TUNNEL"
    DAM = "DAM"

    @classmethod
    def from_str(cls, value: str) -> "AssetType":
        """Normalize and validate asset category strings."""
        if isinstance(value, cls):
            return value
        cleaned = str(value).strip().upper()
        aliases = {
            "BRIDGES": cls.BRIDGE,
            "ROADS": cls.ROAD,
            "BUILDINGS": cls.BUILDING,
            "TUNNELS": cls.TUNNEL,
            "DAMS": cls.DAM,
        }
        if cleaned in aliases:
            return aliases[cleaned]
        for member in cls:
            if member.value == cleaned:
                return member
        raise ValueError(
            f"Invalid asset_type '{value}'. Must be one of: {[item.value for item in cls]}"
        )


class InfrastructureAsset(Base):
    """SQLAlchemy model for infrastructure_assets table with soft deletion."""

    __tablename__ = "infrastructure_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    construction_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    material_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    inspection_frequency: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # One-to-many relationship with historical inspections
    inspections: Mapped[list["Inspection"]] = relationship(
        "Inspection",
        back_populates="asset",
        cascade="all, delete-orphan",
        order_by="desc(Inspection.inspection_date)",
    )

    # Backward compatibility properties
    @property
    def name(self) -> str:
        return self.asset_name

    @name.setter
    def name(self, val: str) -> None:
        self.asset_name = val

    @property
    def type(self) -> str:
        return self.asset_type

    @type.setter
    def type(self, val: str) -> None:
        self.asset_type = val

    @property
    def status(self) -> str:
        return "ARCHIVED" if self.is_archived else "OPERATIONAL"

    def __repr__(self) -> str:
        return f"<InfrastructureAsset(id={self.id}, name='{self.asset_name}', type='{self.asset_type}', archived={self.is_archived})>"
