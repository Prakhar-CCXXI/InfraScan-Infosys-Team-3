"""Backward compatibility wrapper for backend.core.config importing from backend.app.core.config."""

from backend.app.core.config import Settings, settings

__all__ = ["Settings", "settings"]
