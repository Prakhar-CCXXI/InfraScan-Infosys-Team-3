"""Role-Based Access Control (RBAC) permission dependencies and enforcement."""

from collections.abc import Sequence
import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.dependencies import get_current_active_user
from backend.app.db.session import get_async_db
from backend.app.models.user import User, UserRole
from backend.app.services.audit_service import extract_client_ip, record_audit_event

logger = logging.getLogger(__name__)


class RoleChecker:
    """FastAPI dependency enforcing Role-Based Access Control (RBAC) across endpoints.

    Supports verification against:
      - CIVIL_ENGINEER
      - INFRASTRUCTURE_INSPECTOR
      - MAINTENANCE_ENGINEER
      - INFRASTRUCTURE_MANAGER
      - ADMIN
    """

    def __init__(self, allowed_roles: Sequence[UserRole | str]):
        self.allowed_roles: set[UserRole] = {
            r if isinstance(r, UserRole) else UserRole.from_str(str(r))
            for r in allowed_roles
        }

    async def __call__(
        self,
        request: Request,
        current_user: Annotated[User, Depends(get_current_active_user)],
        db: AsyncSession = Depends(get_async_db),
    ) -> User:
        if current_user.role not in self.allowed_roles:
            client_ip = extract_client_ip(request)
            await record_audit_event(
                db,
                action="RBAC_DENIED",
                resource_type="ENDPOINT",
                resource_id=None,
                user_id=current_user.id,
                ip_address=client_ip,
            )
            allowed_names = [r.value for r in self.allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access forbidden: Insufficient permissions. "
                    f"Required roles: {allowed_names}. "
                    f"Current user role: '{current_user.role.value}'."
                ),
            )
        return current_user


def require_role(allowed_roles: Sequence[UserRole | str]) -> RoleChecker:
    """Factory helper to generate reusable role-checking dependencies."""
    return RoleChecker(allowed_roles)


# Role-Based Shortcut Dependencies
require_admin = require_role([UserRole.ADMIN])
require_civil_engineer = require_role([UserRole.CIVIL_ENGINEER, UserRole.ADMIN])
require_inspector = require_role([UserRole.INFRASTRUCTURE_INSPECTOR, UserRole.ADMIN])
require_maintenance_engineer = require_role([UserRole.MAINTENANCE_ENGINEER, UserRole.ADMIN])
require_manager = require_role([UserRole.INFRASTRUCTURE_MANAGER, UserRole.ADMIN])

# Module 2 Asset & Inspection Specific RBAC Gates
require_viewer = require_role([
    UserRole.INFRASTRUCTURE_INSPECTOR,
    UserRole.CIVIL_ENGINEER,
    UserRole.INFRASTRUCTURE_MANAGER,
    UserRole.MAINTENANCE_ENGINEER,
    UserRole.ADMIN,
])
require_asset_editor = require_role([
    UserRole.CIVIL_ENGINEER,
    UserRole.INFRASTRUCTURE_MANAGER,
    UserRole.ADMIN,
])
require_inspection_creator = require_role([
    UserRole.INFRASTRUCTURE_INSPECTOR,
    UserRole.CIVIL_ENGINEER,
    UserRole.INFRASTRUCTURE_MANAGER,
    UserRole.ADMIN,
])
require_inspector_assigner = require_role([
    UserRole.CIVIL_ENGINEER,
    UserRole.INFRASTRUCTURE_MANAGER,
    UserRole.ADMIN,
])
