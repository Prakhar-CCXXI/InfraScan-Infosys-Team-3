"""Backward compatibility wrapper exposing the app inspections router."""

from backend.app.routers.inspections import router

__all__ = ["router"]
