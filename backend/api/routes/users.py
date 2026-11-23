"""Backward compatibility wrapper exposing the app users router."""

from backend.app.routers.users import router

__all__ = ["router"]
