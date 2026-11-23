"""Backward compatibility wrapper for auth_service."""

from backend.app.services.auth_service import (
    authenticate_user,
    change_user_password,
    generate_auth_tokens,
    get_user_by_email,
    get_user_by_id,
    handle_google_oauth_user,
    logout_user,
    register_user,
    rotate_refresh_token,
    update_user_profile,
)

__all__ = [
    "get_user_by_id",
    "get_user_by_email",
    "authenticate_user",
    "register_user",
    "generate_auth_tokens",
    "rotate_refresh_token",
    "logout_user",
    "change_user_password",
    "handle_google_oauth_user",
    "update_user_profile",
]
