"""Backward compatibility wrapper for user and auth schemas."""

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
from backend.app.schemas.user import (
    AuditLogResponse,
    UserProfileUpdateRequest,
    UserResponse,
)

# Alias for backwards compatibility
UserLoginResponse = TokenResponse

__all__ = [
    "AuditLogResponse",
    "LogoutRequest",
    "PasswordChangeRequest",
    "RoleUpdateRequest",
    "TokenRefreshRequest",
    "TokenRefreshResponse",
    "TokenResponse",
    "UserBasicResponse",
    "UserLoginRequest",
    "UserLoginResponse",
    "UserProfileUpdateRequest",
    "UserRegisterRequest",
    "UserResponse",
]
