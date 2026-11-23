"""Pydantic v2 schemas for user profiles and audit log queries."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.user import UserRole


class UserResponse(BaseModel):
    """Public user response schema without exposing sensitive credentials."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole
    is_active: bool = True
    created_at: datetime | None = None

    @property
    def name(self) -> str:
        """Alias for UI compatibility."""
        return self.full_name


class UserProfileUpdateRequest(BaseModel):
    """Schema for updating authenticated user profile."""

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        description="Updated full name",
    )
    # Optional password rotation within profile update for backwards compatibility
    current_password: str | None = Field(default=None, description="Current password")
    new_password: str | None = Field(default=None, min_length=6, description="New password")


class AuditLogResponse(BaseModel):
    """Schema for recorded system audit log entries."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    resource_type: str
    resource_id: uuid.UUID | None = None
    timestamp: datetime
    ip_address: str | None = None
