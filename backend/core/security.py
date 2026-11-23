"""Backward compatibility wrapper for backend.core.security importing from backend.app.core.security."""

from backend.app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    hash_password,
    is_jti_revoked,
    oauth,
    oauth2_scheme,
    revoke_token_jti,
    verify_password,
)

__all__ = [
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "JWT_ALGORITHM",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "SECRET_KEY",
    "create_access_token",
    "create_refresh_token",
    "decode_access_token",
    "decode_refresh_token",
    "hash_password",
    "is_jti_revoked",
    "oauth",
    "oauth2_scheme",
    "revoke_token_jti",
    "verify_password",
]
