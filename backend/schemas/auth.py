"""Backward compatibility wrapper for auth schemas."""

from backend.app.schemas.auth import (
    LogoutRequest,
    PasswordChangeRequest,
    RoleUpdateRequest,
    TokenRefreshRequest,
    TokenRefreshResponse,
    TokenResponse,
    UserBasicResponse,
    UserLoginRequest,
    UserRegisterRequest,
)

__all__ = [
    "LogoutRequest",
    "PasswordChangeRequest",
    "RoleUpdateRequest",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "TokenResponse",
    "UserBasicResponse",
    "UserLoginRequest",
    "UserRegisterRequest",
]
