"""Authentication schemas for login, registration, token refresh, and password management."""

import re
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from backend.app.models.user import UserRole

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email_format(val: str) -> str:
    """Validate and normalize email address string."""
    if not isinstance(val, str):
        raise ValueError("Email must be a string.")
    cleaned = val.strip().lower()
    if not EMAIL_REGEX.match(cleaned):
        raise ValueError("Invalid email address format.")
    return cleaned


class UserRegisterRequest(BaseModel):
    """Schema for registering a new user."""

    email: EmailStr = Field(
        ...,
        description="Operational email address",
        examples=["engineer@infrascan.gov"],
    )
    password: str = Field(
        ...,
        min_length=6,
        description="Password (minimum 6 characters)",
        examples=["SecurePass!2026"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=150,
        description="Full legal name of the user",
        examples=["Alex Morgan"],
    )
    name: str | None = Field(
        default=None,
        description="Frontend alias for full_name",
        examples=["Alex Morgan"],
    )
    role: str | UserRole = Field(
        default=UserRole.CIVIL_ENGINEER,
        description="Role assigned for RBAC authorization",
        examples=["CIVIL_ENGINEER"],
    )
    department: str | None = Field(
        default=None,
        description="Operational division or department",
        examples=["Highways and Bridges Division"],
    )

    @model_validator(mode="before")
    @classmethod
    def reconcile_names_and_roles(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("full_name") and data.get("name"):
                data["full_name"] = data["name"]
            elif not data.get("full_name") and data.get("email"):
                prefix = str(data["email"]).split("@")[0].replace(".", " ").title()
                data["full_name"] = prefix
        return data

    @field_validator("email", mode="before")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_format(v)

    @field_validator("role")
    @classmethod
    def parse_role(cls, v: Any) -> UserRole:
        if isinstance(v, UserRole):
            return v
        if isinstance(v, str):
            return UserRole.from_str(v)
        raise ValueError(f"Invalid role format: {v}")


class UserLoginRequest(BaseModel):
    """Schema for authenticating a user with email and password."""

    email: EmailStr = Field(
        ...,
        description="User email address",
        examples=["engineer@infrascan.gov"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="User account password",
        examples=["SecurePass!2026"],
    )

    @field_validator("email", mode="before")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_format(v)


class UserBasicResponse(BaseModel):
    """Basic user details returned upon authentication."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    role: UserRole

    @property
    def name(self) -> str:
        return self.full_name


class TokenResponse(BaseModel):
    """Standard authentication response with Access Token and Refresh Token."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes (in seconds)
    user: UserBasicResponse
    # Backwards compatibility fields
    token: str | None = None
    message: str = "Authentication successful."


class TokenRefreshRequest(BaseModel):
    """Schema for requesting a new access token via refresh token rotation."""

    refresh_token: str = Field(..., description="Active JWT refresh token")


class TokenRefreshResponse(BaseModel):
    """Response returned upon successful refresh token rotation."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # 15 minutes


class PasswordChangeRequest(BaseModel):
    """Schema for updating authenticated user password."""

    current_password: str = Field(..., min_length=1, description="Existing account password")
    new_password: str = Field(..., min_length=6, description="New account password (min 6 characters)")


class LogoutRequest(BaseModel):
    """Schema for user logout."""

    refresh_token: str | None = Field(default=None, description="Optional refresh token to revoke explicitly")


class RoleUpdateRequest(BaseModel):
    """Schema for administrative role assignment."""

    role: UserRole = Field(..., description="New role to assign to the user")

    @field_validator("role", mode="before")
    @classmethod
    def parse_role(cls, v: Any) -> UserRole:
        if isinstance(v, UserRole):
            return v
        if isinstance(v, str):
            return UserRole.from_str(v)
        raise ValueError(f"Invalid role format: {v}")
