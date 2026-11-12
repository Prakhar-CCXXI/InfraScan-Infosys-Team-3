"""Authentication endpoints for user login, registration, and session info."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.user import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserResponse,
)
from backend.services.auth_service import (
    check_role_match,
    create_access_token,
    decode_access_token,
    ensure_default_users,
    format_user_display_name,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def parse_id_value(val: Any) -> int | None:
    """Parse raw ID value into an integer if possible."""
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        cleaned = val.strip()
        if cleaned.isdigit():
            return int(cleaned)
        # Handle formats like USR-001 or INF-001
        digits = "".join(c for c in cleaned if c.isdigit())
        if digits:
            return int(digits)
    return None


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticate user with their ID, password, email, and role.",
)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user by checking id, email, password, and role."""
    ensure_default_users(db)

    parsed_id = parse_id_value(payload.id)
    email_clean = payload.email.strip().lower()

    # Step 1: Look up user in database
    user = None
    if parsed_id is not None:
        user = db.scalar(select(User).where(User.id == parsed_id))

    if user is None:
        # Search by email
        user = db.scalar(select(User).where(func.lower(User.email) == email_clean))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. User not found.",
        )

    # Step 2: Validate ID matches
    if parsed_id is not None and user.id != parsed_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User ID mismatch: ID '{payload.id}' does not match account ID {user.id}.",
        )

    # Step 3: Validate Email matches
    if user.email.lower() != email_clean:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User email does not match registered account email.",
        )

    # Step 4: Validate Password
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password.",
        )

    # Step 5: Validate Role
    if not check_role_match(user.role, payload.role):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Role mismatch: account is registered as '{user.role}', but '{payload.role}' was supplied.",
        )

    # Step 6: Generate JWT access token
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    }
    access_token = create_access_token(token_data)

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        name=format_user_display_name(user.email),
        created_at=user.created_at,
    )

    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        token=access_token,
        user=user_response,
        message="Login successful",
    )


@router.post(
    "/register",
    response_model=UserLoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with email, password, role, and optional ID.",
)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user in the system."""
    email_clean = payload.email.strip().lower()

    # Check for existing user with identical email
    existing_email = db.scalar(select(User).where(func.lower(User.email) == email_clean))
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    parsed_id = parse_id_value(payload.id) if payload.id is not None else None
    if parsed_id is not None:
        existing_id = db.scalar(select(User).where(User.id == parsed_id))
        if existing_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User ID {parsed_id} is already taken.",
            )

    hashed = hash_password(payload.password)
    user = User(
        email=email_clean,
        hashed_password=hashed,
        role=payload.role.strip(),
    )
    if parsed_id is not None:
        user.id = parsed_id

    db.add(user)
    db.commit()
    db.refresh(user)

    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
    }
    access_token = create_access_token(token_data)

    user_response = UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        name=payload.name or format_user_display_name(user.email),
        created_at=user.created_at,
    )

    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        token=access_token,
        user=user_response,
        message="Registration successful",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user details",
    description="Retrieve account details of the currently authenticated user.",
)
def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    """Retrieve current user from authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header.",
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    user_id = parse_id_value(payload["sub"])
    user = db.scalar(select(User).where(User.id == user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        name=format_user_display_name(user.email),
        created_at=user.created_at,
    )
