"""Pydantic v2 validation schemas for inspection scheduling and status tracking."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.inspection import InspectionStatus
from backend.app.schemas.asset import AssetResponse


class InspectionCreateRequest(BaseModel):
    """Schema for scheduling a new infrastructure inspection."""

    asset_id: uuid.UUID = Field(
        ...,
        description="UUID of the target infrastructure asset to inspect",
    )
    inspector_id: uuid.UUID | None = Field(
        default=None,
        description="Optional UUID of the assigned inspector. If provided, status becomes ASSIGNED.",
    )
    inspection_date: datetime | None = Field(
        default=None,
        description="Target date and time for inspection. Defaults to current timestamp.",
    )
    remarks: str | None = Field(
        default=None,
        description="Initial notes, inspection scope, or instructions",
        examples=["Annual monsoon post-inspection on south pier."],
    )


class InspectionUpdateRequest(BaseModel):
    """Schema for updating inspection scheduling and remarks."""

    inspection_date: datetime | None = Field(default=None)
    remarks: str | None = Field(default=None)


class InspectionAssignRequest(BaseModel):
    """Schema for assigning or reassigning an active inspector."""

    inspector_id: uuid.UUID = Field(
        ...,
        description="UUID of the active inspector to assign",
    )


class InspectionStatusUpdateRequest(BaseModel):
    """Schema for updating inspection workflow status."""

    status: str | InspectionStatus = Field(
        ...,
        description="Allowed statuses: CREATED, ASSIGNED, IN_PROGRESS, IMAGE_UPLOADED, ANALYSIS_PENDING, COMPLETED, REVIEW_REQUIRED",
    )

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, val: Any) -> str:
        enum_member = InspectionStatus.from_str(str(val))
        return enum_member.value


class InspectionResponse(BaseModel):
    """Public representation of an infrastructure inspection."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    inspector_id: uuid.UUID | None = None
    inspection_date: datetime
    status: str
    remarks: str | None = None
    created_at: datetime


class InspectionDetailResponse(InspectionResponse):
    """Detailed inspection response with nested asset and inspector details."""

    asset: AssetResponse | None = None
    inspector_name: str | None = None


class InspectionImageResponse(BaseModel):
    """Schema for inspection images."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID | str
    inspection_id: uuid.UUID
    file_name: str
    storage_key: str
    uploaded_at: datetime | None = None
