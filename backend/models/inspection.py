"""Backward compatibility wrapper for Inspection model."""

from backend.app.models.inspection import Inspection, InspectionStatus

__all__ = ["Inspection", "InspectionStatus"]
