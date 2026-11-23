"""Backward compatibility wrapper for audit_service."""

from backend.app.services.audit_service import (
    extract_client_ip,
    list_audit_logs,
    record_audit_event,
)

__all__ = [
    "extract_client_ip",
    "record_audit_event",
    "list_audit_logs",
]
