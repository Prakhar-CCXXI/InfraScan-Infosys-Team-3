"""Backward compatibility wrapper for inspection schemas."""

from enum import Enum

from backend.app.schemas.inspection import (
    InspectionAssignRequest,
    InspectionCreateRequest,
    InspectionImageResponse,
    InspectionResponse,
    InspectionStatusUpdateRequest,
    InspectionUpdateRequest,
)


class InfrastructureType(str, Enum):
    bridge = "bridge"
    building = "building"
    road = "road"
    dam = "dam"
    other = "other"


# Legacy aliases
InspectionCreate = InspectionCreateRequest

__all__ = [
    "InfrastructureType",
    "InspectionAssignRequest",
    "InspectionCreate",
    "InspectionCreateRequest",
    "InspectionImageResponse",
    "InspectionResponse",
    "InspectionStatusUpdateRequest",
    "InspectionUpdateRequest",
]
