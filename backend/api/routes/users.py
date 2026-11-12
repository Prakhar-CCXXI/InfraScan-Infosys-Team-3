"""User management endpoints for retrieving and managing user accounts."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.routes.auth import login as auth_login, register as auth_register
from backend.db.session import get_db
from backend.models.user import User
from backend.schemas.user import (
    UserLoginRequest,
    UserLoginResponse,
    UserRegisterRequest,
    UserResponse,
)
from backend.services.auth_service import ensure_default_users, format_user_display_name

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/login",
    response_model=UserLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login via /users/login",
    description="Authenticate user with their ID, password, email, and role.",
)
def login_user(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """Delegate login to the authentication handler."""
    return auth_login(payload, db)


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List all users",
    description="Retrieve all registered user accounts without exposing passwords.",
)
@router.get(
    "/",
    response_model=list[UserResponse],
    summary="List all users",
    description="Retrieve all registered user accounts without exposing passwords.",
)
def list_users(db: Session = Depends(get_db)):
    """Retrieve all users in the system."""
    ensure_default_users(db)

    users = db.scalars(select(User).order_by(User.id.asc())).all()

    return [
        UserResponse(
            id=u.id,
            email=u.email,
            role=u.role,
            name=format_user_display_name(u.email),
            created_at=u.created_at,
        )
        for u in users
    ]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieve a user account by its unique numeric ID.",
)
def get_user_by_id(user_id: int, db: Session = Depends(get_db)):
    """Retrieve user account by ID."""
    user = db.scalar(select(User).where(User.id == user_id))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        name=format_user_display_name(user.email),
        created_at=user.created_at,
    )


@router.post(
    "",
    response_model=UserLoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create / Register User",
    description="Register a new user account.",
)
@router.post(
    "/",
    response_model=UserLoginResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create / Register User",
    description="Register a new user account.",
)
def create_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Delegate user creation to the registration handler."""
    return auth_register(payload, db)
