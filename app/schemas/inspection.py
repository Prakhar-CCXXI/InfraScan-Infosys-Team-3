from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator


class InfrastructureType(str, Enum):
    bridge = "bridge"
    building = "building"
    road = "road"
    dam = "dam"
    other = "other"


class InspectionCreate(BaseModel):
    """Validate data submitted when creating an infrastructure inspection."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    infrastructure_name: str = Field(
        min_length=2,
        max_length=100,
        description="Name or identifier of the infrastructure asset",
    )
    infrastructure_type: InfrastructureType
    location: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("infrastructure_name", "location")
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
