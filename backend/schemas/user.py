from datetime import datetime
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email_format(val: str) -> str:
    if not isinstance(val, str):
        raise ValueError("Email must be a string.")
    cleaned = val.strip()
    if not EMAIL_REGEX.match(cleaned):
        raise ValueError("Invalid email address format.")
    return cleaned.lower()


class UserLoginRequest(BaseModel):
    """Schema for user login request asking for ID, Password, Email, and Role."""

    id: int | str = Field(
        ...,
        description="User unique identifier (ID)",
        examples=[1],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="User account password",
        examples=["demo123"],
    )
    email: str = Field(
        ...,
        description="User email address",
        examples=["demo@infrascan.test"],
    )
    role: str = Field(
        ...,
        min_length=1,
        description="User system role (e.g., Civil Engineer, Infrastructure Inspector, Administrator)",
        examples=["Infrastructure Inspector"],
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v: Any) -> int | str:
        if isinstance(v, str):
            cleaned = v.strip()
            if cleaned.isdigit():
                return int(cleaned)
            return cleaned
        return v

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_format(v)


class UserRegisterRequest(BaseModel):
    """Schema for user registration / user creation request."""

    id: int | str | None = Field(
        default=None,
        description="Optional custom user ID",
        examples=[1],
    )
    email: str = Field(
        ...,
        description="User email address",
        examples=["engineer@infrascan.test"],
    )
    password: str = Field(
        ...,
        min_length=6,
        description="User account password (minimum 6 characters)",
        examples=["secret123"],
    )
    role: str = Field(
        ...,
        min_length=1,
        description="User system role",
        examples=["Civil Engineer"],
    )
    name: str | None = Field(
        default=None,
        description="Optional full name of the user",
        examples=["John Doe"],
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, v: Any) -> int | str | None:
        if v is None:
            return None
        if isinstance(v, str):
            cleaned = v.strip()
            if not cleaned:
                return None
            if cleaned.isdigit():
                return int(cleaned)
            return cleaned
        return v

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        return validate_email_format(v)


class UserResponse(BaseModel):
    """Public user response schema without exposing password hashes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    name: str | None = None
    created_at: datetime | None = None


class UserLoginResponse(BaseModel):
    """Response returned upon successful login."""

    access_token: str
    token_type: str = "bearer"
    token: str
    user: UserResponse
    message: str = "Login successful"
