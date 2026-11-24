"""Audit logging service for tracking authentication events, authorization attempts, and administrative actions."""

from datetime import datetime, timezone
import logging
from typing import Sequence
import uuid

from fastapi import Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def extract_client_ip(request: Request | None) -> str | None:
    """Extract client IP address accounting for reverse proxies (X-Forwarded-For)."""
    if request is None:
        return None
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return None


async def record_audit_event(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Persist an audit entry asynchronously to the audit_logs table."""
    try:
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action=action.strip().upper(),
            resource_type=resource_type.strip().upper(),
            resource_id=resource_id,
            timestamp=datetime.now(timezone.utc),
            ip_address=ip_address,
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)
        logger.info(
            "AUDIT LOG: action=%s user_id=%s resource=%s/%s ip=%s",
            action,
            user_id,
            resource_type,
            resource_id,
            ip_address,
        )
        return audit_entry
    except Exception as exc:
        logger.error("Failed to write audit log entry: %s", exc)
        await db.rollback()
        raise


async def list_audit_logs(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[AuditLog]:
    """Retrieve audit logs with optional filtering and pagination."""
    query = select(AuditLog)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action.upper())
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type.upper())

    query = query.order_by(desc(AuditLog.timestamp)).offset(offset).limit(limit)
    result = await db.scalars(query)
    return result.all()
