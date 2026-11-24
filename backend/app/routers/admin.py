"""Admin management router for user administration, role assignment, and audit log inspection."""

import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.permissions import require_admin
from backend.app.db.session import get_async_db
from backend.app.models.user import User, UserRole
from backend.app.schemas.auth import RoleUpdateRequest
from backend.app.schemas.user import AuditLogResponse, UserResponse
from backend.app.services.audit_service import extract_client_ip, list_audit_logs, record_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Administration (Admin Only)"])


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users (Admin only)",
    description="Retrieve all registered users with system details. Restricted to Administrators.",
)
async def admin_list_users(
    _admin_user: Annotated[User, Depends(require_admin)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_db),
) -> list[UserResponse]:
    """Retrieve full list of users in the system."""
    query = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await db.scalars(query)
    users = result.all()
    return [UserResponse.model_validate(u) for u in users]


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role (Admin only)",
    description="Elevate or reassign a user's role. Restricted to Administrators.",
)
async def admin_update_user_role(
    user_id: str,
    payload: RoleUpdateRequest,
    request: Request,
    admin_user: Annotated[User, Depends(require_admin)],
    db: AsyncSession = Depends(get_async_db),
) -> UserResponse:
    """Update role of any user account."""
    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid UUID string '{user_id}'.",
        )

    target_user = await db.scalar(select(User).where(User.id == target_uuid))
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found.",
        )

    old_role = target_user.role
    target_user.role = payload.role
    await db.commit()
    await db.refresh(target_user)

    client_ip = extract_client_ip(request)
    await record_audit_event(
        db,
        action="USER_ROLE_UPDATED",
        resource_type="USER",
        resource_id=target_user.id,
        user_id=admin_user.id,
        ip_address=client_ip,
    )
    logger.info("Admin %s updated role of %s from %s to %s", admin_user.email, target_user.email, old_role, target_user.role)

    return UserResponse.model_validate(target_user)


@router.get(
    "/audit-logs",
    response_model=list[AuditLogResponse],
    summary="Retrieve audit logs (Admin only)",
    description="Inspect audit trail of authentication, authorization, and administrative changes.",
)
async def admin_get_audit_logs(
    _admin_user: Annotated[User, Depends(require_admin)],
    user_id: uuid.UUID | None = Query(default=None, description="Filter logs by user UUID"),
    action: str | None = Query(default=None, description="Filter logs by action name"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_db),
) -> list[AuditLogResponse]:
    """Retrieve security audit events."""
    logs = await list_audit_logs(
        db,
        user_id=user_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    return [AuditLogResponse.model_validate(log) for log in logs]
