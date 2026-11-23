"""FastAPI dependencies backward compatibility wrapper."""

from backend.app.core.dependencies import (
    get_current_active_user,
    get_current_user,
)
from backend.app.core.permissions import (
    RoleChecker,
    require_admin,
    require_civil_engineer,
    require_inspector,
    require_maintenance_engineer,
    require_manager,
    require_role,
)

__all__ = [
    "get_current_user",
    "get_current_active_user",
    "RoleChecker",
    "require_role",
    "require_admin",
    "require_civil_engineer",
    "require_inspector",
    "require_maintenance_engineer",
    "require_manager",
]
