"""Backward compatibility wrapper for InfrastructureAsset model."""

from backend.app.models.asset import AssetType, InfrastructureAsset

__all__ = ["InfrastructureAsset", "AssetType"]
