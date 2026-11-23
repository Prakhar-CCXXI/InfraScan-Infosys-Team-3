"""Backward compatibility wrapper for User model."""

from backend.app.models.user import User, UserRole

__all__ = ["User", "UserRole"]
