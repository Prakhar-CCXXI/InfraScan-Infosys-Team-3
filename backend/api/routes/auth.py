"""Backward compatibility wrapper exposing the app auth router."""

from backend.app.routers.auth import router

__all__ = ["router"]
