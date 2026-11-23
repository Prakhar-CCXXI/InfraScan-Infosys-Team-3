"""SQLAlchemy model representing scheduled and completed infrastructure inspections."""

from datetime import datetime
import enum
from typing import TYPE_CHECKING
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.session import Base

if TYPE_CHECKING:
    from backend.app.models.asset import InfrastructureAsset
    from backend.app.models.user import User


class InspectionStatus(str, enum.Enum):
    """Allowed lifecycle states for an infrastructure inspection workflow."""

    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    IMAGE_UPLOADED = "IMAGE_UPLOADED"
    ANALYSIS_PENDING = "ANALYSIS_PENDING"
    COMPLETED = "COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"

    @classmethod
    def from_str(cls, value: str) -> "InspectionStatus":
        """Normalize and validate inspection status values."""
        if isinstance(value, cls):
            return value
        cleaned = str(value).strip().upper()
        for member in cls:
            if member.value == cleaned:
                return member
        raise ValueError(
            f"Invalid inspection status '{value}'. Must be one of: {[s.value for s in cls]}"
        )


class Inspection(Base):
    """SQLAlchemy model for inspections table with asset and inspector relationships."""

    __tablename__ = "inspections"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("infrastructure_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    inspector_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    inspection_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=InspectionStatus.CREATED.value,
        index=True,
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    asset: Mapped["InfrastructureAsset"] = relationship(
        "InfrastructureAsset",
        back_populates="inspections",
    )
    inspector: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[inspector_id],
    )

    def __repr__(self) -> str:
        return f"<Inspection(id={self.id}, asset_id={self.asset_id}, status='{self.status}')>"
