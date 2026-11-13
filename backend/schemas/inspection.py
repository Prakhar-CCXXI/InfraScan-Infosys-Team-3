
from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InfrastructureType(str, Enum):
    bridge = "bridge"
    building = "building"
    road = "road"
    dam = "dam"
    other = "other"


class InspectionCreate(BaseModel):
    """Validate data submitted from the inspection form."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    assetId: str = Field(min_length=7, max_length=20)
    date: date
    inspector: str = Field(min_length=2, max_length=100)
    status: str = Field(default="Assigned", max_length=30)

    @field_validator("assetId", "inspector")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be blank")
        return value


class InspectionResponse(BaseModel):
    """Response format for an inspection."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    infrastructure_name: str
    infrastructure_type: InfrastructureType
    location: str
    description: str | None = None
    status: str = "pending"
    asset_id: int | None = None
    inspection_date: date | None = None
    inspector: str | None = None
