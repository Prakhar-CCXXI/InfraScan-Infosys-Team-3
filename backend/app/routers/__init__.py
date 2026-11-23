from backend.app.routers.auth import router as auth_router
from backend.app.routers.users import router as users_router
from backend.app.routers.admin import router as admin_router
from backend.app.routers.assets import router as assets_router
from backend.app.routers.inspections import router as inspections_router

__all__ = [
    "auth_router",
    "users_router",
    "admin_router",
    "assets_router",
    "inspections_router",
]
