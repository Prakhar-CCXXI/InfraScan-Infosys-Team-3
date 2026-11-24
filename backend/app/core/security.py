"""Security, Argon2 cryptography, JWT token management, and Authlib OAuth2 configuration."""

from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# FastAPI OAuth2 standard password flow bearer
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_PREFIX}/auth/token",
    auto_error=False,
)

# JWT Constants
JWT_ALGORITHM = getattr(settings, "ALGORITHM", "HS256")
SECRET_KEY = getattr(settings, "SECRET_KEY", "infrascan-secret-key-super-secure")
ACCESS_TOKEN_EXPIRE_MINUTES = getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
REFRESH_TOKEN_EXPIRE_DAYS = getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)

# Argon2 Password Hasher instance (RFC 9106 recommended parameters)
_argon2_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# In-memory storage for revoked token JTIs (with thread-safety/expiration clean-up)
_revoked_token_jtis: set[str] = set()


def revoke_token_jti(jti: str) -> None:
    """Register a token's JTI as revoked."""
    if jti:
        _revoked_token_jtis.add(jti)


def is_jti_revoked(jti: str) -> bool:
    """Check if a token's JTI has been revoked."""
    return jti in _revoked_token_jtis


def hash_password(password: str) -> str:
    """Hash a cleartext password using Argon2 (never store plain-text)."""
    if not password:
        raise ValueError("Password cannot be empty.")
    return _argon2_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against an Argon2 hash (with legacy bcrypt fallback)."""
    if not plain_password or not hashed_password:
        return False
    try:
        return _argon2_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        # Fallback support for legacy bcrypt hashes during system migration
        if hashed_password.startswith("$2b$") or hashed_password.startswith("$2a$"):
            try:
                import bcrypt
                return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
            except Exception:
                return False
        return False
    except Exception as exc:
        logger.warning("Argon2 password verification failed: %s", exc)
        return False


def create_access_token(
    subject: str | Any,
    claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a signed JWT access token (15-minute default lifecycle)."""
    now = datetime.now(timezone.utc)
    expires = now + (
        expires_delta if expires_delta is not None else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "access",
        "jti": secrets.token_hex(16),
    }
    if claims:
        payload.update(claims)

    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a signed JWT refresh token with unique JTI (7-day default lifecycle)."""
    now = datetime.now(timezone.utc)
    expires = now + (
        expires_delta if expires_delta is not None else timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "refresh",
        "jti": secrets.token_hex(16),
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Raises:
        HTTPException(401): If token is expired, invalid, revoked, or not an access token.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired: Access token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"token expired\""},
        )
    except jwt.InvalidTokenError as err:
        logger.debug("Token validation failure: %s", err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed authentication token.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    # Check token type
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: Expected access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check revocation
    jti = payload.get("jti")
    if jti and is_jti_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please authenticate again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT refresh token.

    Raises:
        HTTPException(401): If refresh token is expired, invalid, revoked, or wrong type.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired: Refresh token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"refresh token expired\""},
        )
    except jwt.InvalidTokenError as err:
        logger.debug("Refresh token validation failure: %s", err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed refresh token.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type: Expected refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jti = payload.get("jti")
    if jti and is_jti_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked or already rotated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


# --- Authlib OAuth2 Setup ---
oauth = OAuth()
if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
else:
    # Register with placeholders so tests and initialization succeed even without live credentials
    oauth.register(
        name="google",
        client_id="dummy-google-client-id",
        client_secret="dummy-google-client-secret",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
