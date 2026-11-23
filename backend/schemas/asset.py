"""Backward compatibility wrapper for asset schemas."""

from backend.app.schemas.asset import (
    AssetCreateRequest,
    AssetResponse,
    AssetUpdateRequest,
)

__all__ = [
    "AssetCreateRequest",
    "AssetResponse",
    "AssetUpdateRequest",
]
