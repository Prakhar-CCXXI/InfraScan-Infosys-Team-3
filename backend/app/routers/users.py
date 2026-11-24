"""User profile and query endpoints."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_active_user
from backend.app.db.session import get_async_db
from backend.app.models.user import User
from backend.app.schemas.user import UserProfileUpdateRequest, UserResponse
from backend.app.services.audit_service import extract_client_ip, record_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get Current User Profile",
    description="Retrieve the profile of the currently authenticated user.",
)
async def get_my_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Retrieve profile of the authenticated caller."""
    return UserResponse.model_validate(current_user)


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update Current User Profile",
    description="Update profile details (such as full name) for the authenticated user.",
)
@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update Current User Profile (PATCH Alias)",
)
async def update_my_profile(
    payload: UserProfileUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Update profile attributes for authenticated user."""
    updated = False
    if payload.full_name and payload.full_name.strip() != current_user.full_name:
        current_user.full_name = payload.full_name.strip()
        updated = True

    if updated:
        await db.commit()
        await db.refresh(current_user)
        client_ip = extract_client_ip(request)
        await record_audit_event(
            db,
            action="USER_PROFILE_UPDATED",
            resource_type="USER",
            resource_id=current_user.id,
            user_id=current_user.id,
            ip_address=client_ip,
        )

    return UserResponse.model_validate(current_user)


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List Users",
    description="Retrieve registered users. Requires authentication.",
)
@router.get(
    "/",
    response_model=list[UserResponse],
    include_in_schema=False,
)
async def list_users(
    _current_user: User = Depends(get_current_active_user),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_db),
) -> list[UserResponse]:
    """List system users."""
    query = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.scalars(query)
    users = result.all()
    return [UserResponse.model_validate(u) for u in users]


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
)
async def get_user_by_id(
    user_id: str,
    _current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Retrieve user account by ID."""
    try:
        parsed_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID string '{user_id}'.",
        )

    user = await db.scalar(select(User).where(User.id == parsed_uuid))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )

    return UserResponse.model_validate(user)
