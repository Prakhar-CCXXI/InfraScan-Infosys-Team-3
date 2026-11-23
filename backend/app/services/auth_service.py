"""Authentication business logic, Argon2 credential verification, token rotation, and audit logging."""

import logging
import secrets
from typing import Any
import uuid

from fastapi import HTTPException, status
import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    SECRET_KEY,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    revoke_token_jti,
    verify_password,
)
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import UserRegisterRequest
from backend.app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Retrieve user entity by primary key UUID asynchronously."""
    result = await db.scalar(select(User).where(User.id == user_id))
    return result


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Retrieve user entity by unique email address asynchronously."""
    cleaned = email.strip().lower()
    result = await db.scalar(select(User).where(func.lower(User.email) == cleaned))
    return result


async def register_user(
    db: AsyncSession,
    data: UserRegisterRequest,
    ip_address: str | None = None,
) -> User:
    """Register a new user account with Argon2 password hashing and audit logging.

    Raises:
        HTTPException(409 Conflict): If email is already registered.
    """
    existing_user = await get_user_by_email(db, data.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{data.email}' is already registered.",
        )

    # Normalize role
    role_enum = data.role if isinstance(data.role, UserRole) else UserRole.from_str(str(data.role))

    user = User(
        id=uuid.uuid4(),
        full_name=data.full_name or data.email.split("@")[0].title(),
        email=data.email.strip().lower(),
        password_hash=hash_password(data.password),
        role=role_enum,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await record_audit_event(
        db,
        action="USER_REGISTERED",
        resource_type="USER",
        resource_id=user.id,
        user_id=user.id,
        ip_address=ip_address,
    )
    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
    ip_address: str | None = None,
) -> User:
    """Authenticate credentials and verify active status with Argon2.

    Raises:
        HTTPException(401 Unauthorized): On non-existent user, inactive account, or password mismatch.
    """
    user = await get_user_by_email(db, email)

    if user is None:
        await record_audit_event(
            db,
            action="LOGIN_FAILED",
            resource_type="USER",
            resource_id=None,
            user_id=None,
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: Email or password incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        await record_audit_event(
            db,
            action="LOGIN_BLOCKED_INACTIVE",
            resource_type="USER",
            resource_id=user.id,
            user_id=user.id,
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated. Please contact an administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, user.password_hash):
        await record_audit_event(
            db,
            action="LOGIN_FAILED_PASSWORD_MISMATCH",
            resource_type="USER",
            resource_id=user.id,
            user_id=user.id,
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials: Email or password incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Success
    await record_audit_event(
        db,
        action="LOGIN_SUCCESS",
        resource_type="USER",
        resource_id=user.id,
        user_id=user.id,
        ip_address=ip_address,
    )
    return user


def generate_auth_tokens(user: User) -> dict[str, Any]:
    """Generate 15-minute access token and 7-day refresh token along with user payload."""
    claims = {
        "email": user.email,
        "role": user.role.value,
        "full_name": user.full_name,
    }
    access_token = create_access_token(subject=str(user.id), claims=claims)
    refresh_token = create_refresh_token(subject=str(user.id))
    expires_in = ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "token": access_token,
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
        },
    }


async def rotate_refresh_token(
    db: AsyncSession,
    refresh_token_str: str,
    ip_address: str | None = None,
) -> dict[str, Any]:
    """Validate active refresh token, revoke old JTI, and issue fresh access + refresh token bundle."""
    payload = decode_refresh_token(refresh_token_str)
    old_jti = payload.get("jti")
    user_id_str = payload.get("sub")

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: Missing 'sub' claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_uuid = uuid.UUID(str(user_id_str))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token: Invalid UUID subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_id(db, user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with this session no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Invalidate old refresh token (Rotation / Revocation)
    if old_jti:
        revoke_token_jti(old_jti)

    # Issue fresh tokens
    claims = {
        "email": user.email,
        "role": user.role.value,
        "full_name": user.full_name,
    }
    new_access_token = create_access_token(subject=str(user.id), claims=claims)
    new_refresh_token = create_refresh_token(subject=str(user.id))

    await record_audit_event(
        db,
        action="TOKEN_ROTATION_SUCCESS",
        resource_type="SESSION",
        resource_id=user.id,
        user_id=user.id,
        ip_address=ip_address,
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def logout_user(
    db: AsyncSession,
    user_id: uuid.UUID | None,
    refresh_token_str: str | None = None,
    access_token_str: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Revoke active tokens and record session termination in audit log."""
    # Revoke refresh token JTI if provided
    if refresh_token_str:
        try:
            payload = jwt.decode(
                refresh_token_str,
                SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False},
            )
            jti = payload.get("jti")
            if jti:
                revoke_token_jti(jti)
        except Exception:
            pass

    # Revoke access token JTI if provided
    if access_token_str:
        try:
            payload = jwt.decode(
                access_token_str,
                SECRET_KEY,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False},
            )
            jti = payload.get("jti")
            if jti:
                revoke_token_jti(jti)
        except Exception:
            pass

    await record_audit_event(
        db,
        action="USER_LOGOUT",
        resource_type="SESSION",
        resource_id=user_id,
        user_id=user_id,
        ip_address=ip_address,
    )


async def update_user_profile(
    db: AsyncSession,
    user: User,
    data: Any,
    ip_address: str | None = None,
) -> User:
    """Update profile details (full name and/or password) for an authenticated user."""
    updated = False
    new_password = getattr(data, "new_password", None)
    current_password = getattr(data, "current_password", None)
    full_name = getattr(data, "full_name", None)

    if new_password:
        if not current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is required to set a new password.",
            )
        if not verify_password(current_password, user.password_hash):
            await record_audit_event(
                db,
                action="PASSWORD_CHANGE_FAILED",
                resource_type="USER",
                resource_id=user.id,
                user_id=user.id,
                ip_address=ip_address,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password verification failed.",
            )
        user.password_hash = hash_password(new_password)
        updated = True

    if full_name and full_name.strip() != user.full_name:
        user.full_name = full_name.strip()
        updated = True

    if updated:
        await db.commit()
        await db.refresh(user)
        await record_audit_event(
            db,
            action="PROFILE_UPDATED",
            resource_type="USER",
            resource_id=user.id,
            user_id=user.id,
            ip_address=ip_address,
        )

    return user


async def change_user_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
    ip_address: str | None = None,
) -> User:
    """Securely verify current password and apply Argon2 hash for new password."""
    if not verify_password(current_password, user.password_hash):
        await record_audit_event(
            db,
            action="PASSWORD_CHANGE_FAILED",
            resource_type="USER",
            resource_id=user.id,
            user_id=user.id,
            ip_address=ip_address,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed.",
        )

    user.password_hash = hash_password(new_password)
    await db.commit()
    await db.refresh(user)

    await record_audit_event(
        db,
        action="PASSWORD_CHANGED",
        resource_type="USER",
        resource_id=user.id,
        user_id=user.id,
        ip_address=ip_address,
    )
    return user


async def handle_google_oauth_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    ip_address: str | None = None,
) -> User:
    """Find or register a user authenticated via Google OAuth2.

    Security Rule:
        Never trust a role supplied by Google or the frontend. Always assign a safe
        default role (CIVIL_ENGINEER) and require an Administrator to elevate roles.
    """
    user = await get_user_by_email(db, email)

    if user is None:
        # Safe default role: CIVIL_ENGINEER (or INFRASTRUCTURE_INSPECTOR)
        safe_default_role = UserRole.CIVIL_ENGINEER

        user = User(
            id=uuid.uuid4(),
            full_name=full_name or email.split("@")[0].title(),
            email=email.strip().lower(),
            # Unusable strong Argon2 password hash for OAuth accounts
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=safe_default_role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        await record_audit_event(
            db,
            action="GOOGLE_SSO_REGISTER",
            resource_type="USER",
            resource_id=user.id,
            user_id=user.id,
            ip_address=ip_address,
        )
    else:
        if not user.is_active:
            await record_audit_event(
                db,
                action="GOOGLE_LOGIN_BLOCKED_INACTIVE",
                resource_type="USER",
                resource_id=user.id,
                user_id=user.id,
                ip_address=ip_address,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated. Please contact an administrator.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        await record_audit_event(
            db,
            action="GOOGLE_SSO_LOGIN",
            resource_type="USER",
            resource_id=user.id,
            user_id=user.id,
            ip_address=ip_address,
        )

    return user
