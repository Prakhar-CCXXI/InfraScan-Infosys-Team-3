"""Pydantic v2 validation schemas for infrastructure asset management."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.asset import AssetType


class AssetCreateRequest(BaseModel):
    """Schema for registering a new civil infrastructure asset."""

    asset_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Official name or identifier of the infrastructure asset",
        examples=["Hooghly River Suspension Bridge"],
    )
    asset_type: str | AssetType = Field(
        ...,
        description="Structural category (allowed: BRIDGE, ROAD, BUILDING, TUNNEL, DAM)",
        examples=["BRIDGE"],
    )
    location: str = Field(
        ...,
        min_length=2,
        description="Physical address, intersection, or geographic description",
        examples=["Kolkata - Howrah Connector, West Bengal"],
    )
    latitude: float | None = Field(
        default=None,
        ge=-90.0,
        le=90.0,
        description="WGS84 GPS Latitude coordinate",
        examples=[22.5851],
    )
    longitude: float | None = Field(
        default=None,
        ge=-180.0,
        le=180.0,
        description="WGS84 GPS Longitude coordinate",
        examples=[88.3468],
    )
    construction_year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
        description="Year of construction or commissioning",
        examples=[1943],
    )
    material_type: str | None = Field(
        default=None,
        max_length=100,
        description="Primary structural material (e.g., Reinforced Concrete, Structural Steel)",
        examples=["High-Tensile Structural Steel"],
    )
    department: str | None = Field(
        default=None,
        max_length=100,
        description="Overseeing municipal or national department",
        examples=["National Highways Authority"],
    )
    inspection_frequency: int | None = Field(
        default=None,
        gt=0,
        description="Standard recurring inspection cadence in days",
        examples=[90],
    )

    @field_validator("asset_type", mode="before")
    @classmethod
    def validate_asset_type(cls, val: Any) -> str:
        enum_member = AssetType.from_str(str(val))
        return enum_member.value


class AssetUpdateRequest(BaseModel):
    """Schema for updating existing asset details."""

    asset_name: str | None = Field(default=None, min_length=2, max_length=255)
    asset_type: str | AssetType | None = Field(default=None)
    location: str | None = Field(default=None, min_length=2)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    construction_year: int | None = Field(default=None, ge=1800, le=2100)
    material_type: str | None = Field(default=None, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    inspection_frequency: int | None = Field(default=None, gt=0)

    @field_validator("asset_type", mode="before")
    @classmethod
    def validate_asset_type(cls, val: Any) -> str | None:
        if val is None:
            return None
        return AssetType.from_str(str(val)).value


class AssetResponse(BaseModel):
    """Public representation of an infrastructure asset."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_name: str
    asset_type: str
    location: str
    latitude: float | None = None
    longitude: float | None = None
    construction_year: int | None = None
    material_type: str | None = None
    department: str | None = None
    inspection_frequency: int | None = None
    is_archived: bool = False
    created_at: datetime
