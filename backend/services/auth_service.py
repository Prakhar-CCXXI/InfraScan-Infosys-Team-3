"""Authentication, password hashing, JWT token, and role helper utilities."""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import bcrypt
import jwt
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.models.user import User

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Hash a clear-text password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash with fallback to plain comparison."""
    if not hashed_password or not plain_password:
        return False
    try:
        if (
            hashed_password.startswith("$2b$")
            or hashed_password.startswith("$2a$")
            or hashed_password.startswith("$2y$")
        ):
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
    except Exception as exc:
        logger.warning(f"Bcrypt verification error: {exc}")
    return plain_password == hashed_password


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Generate a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None


def normalize_role(role: str) -> str:
    """Normalize role string for case and alias insensitive matching."""
    cleaned = role.strip().upper().replace(" ", "_").replace("-", "_")
    role_map = {
        "ADMIN": "ADMINISTRATOR",
        "ADMINISTRATOR": "ADMINISTRATOR",
        "INSPECTOR": "INFRASTRUCTURE_INSPECTOR",
        "INFRASTRUCTURE_INSPECTOR": "INFRASTRUCTURE_INSPECTOR",
        "CIVIL_ENGINEER": "CIVIL_ENGINEER",
        "ENGINEER": "CIVIL_ENGINEER",
        "MAINTENANCE_ENGINEER": "MAINTENANCE_ENGINEER",
        "INFRASTRUCTURE_MANAGER": "INFRASTRUCTURE_MANAGER",
        "MANAGER": "INFRASTRUCTURE_MANAGER",
    }
    return role_map.get(cleaned, cleaned)


def check_role_match(role_a: str, role_b: str) -> bool:
    """Check if two role specifications match semantically."""
    if not role_a or not role_b:
        return False
    if role_a.strip().lower() == role_b.strip().lower():
        return True
    return normalize_role(role_a) == normalize_role(role_b)


def format_user_display_name(email: str) -> str:
    """Derive human-readable name from email prefix."""
    prefix = email.split("@")[0].replace(".", " ").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in prefix.split()) if prefix else "User"


def ensure_default_users(db: Session) -> None:
    """Ensure standard demo users exist in the database."""
    default_users = [
        {
            "id": 1,
            "email": "demo@infrascan.test",
            "password": "demo123",
            "role": "Infrastructure Inspector",
        },
        {
            "id": 2,
            "email": "admin@infrascan.test",
            "password": "admin123",
            "role": "Administrator",
        },
    ]

    for item in default_users:
        existing = db.scalar(select(User).where(func.lower(User.email) == item["email"].lower()))
        if not existing:
            hashed = hash_password(item["password"])
            user = User(
                id=item["id"],
                email=item["email"],
                hashed_password=hashed,
                role=item["role"],
            )
            db.add(user)
            try:
                db.commit()
            except Exception:
                db.rollback()
