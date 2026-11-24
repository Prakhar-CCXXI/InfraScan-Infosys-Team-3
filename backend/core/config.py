"""Backward compatibility wrapper for backend.core.config importing from backend.app.core.config."""

from backend.app.core.config import REPO_ROOT, Settings, settings

__all__ = ["REPO_ROOT", "Settings", "settings"]