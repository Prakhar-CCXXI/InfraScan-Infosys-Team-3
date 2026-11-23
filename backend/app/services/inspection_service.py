"""Inspection service handling scheduling, inspector assignments, status updates, and audit trails."""

from datetime import datetime, timezone
import logging
from typing import Sequence
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.asset import InfrastructureAsset
from backend.app.models.inspection import Inspection, InspectionStatus
from backend.app.models.user import User
from backend.app.schemas.inspection import (
    InspectionCreateRequest,
    InspectionUpdateRequest,
)
from backend.app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)


async def create_inspection(
    db: AsyncSession,
    data: InspectionCreateRequest,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> Inspection:
    """Schedule a new inspection, verifying asset validity and inspector active status."""
    # 1. Validate that the asset exists and is not archived
    asset = await db.scalar(
        select(InfrastructureAsset).where(
            InfrastructureAsset.id == data.asset_id,
            InfrastructureAsset.is_archived == False,  # noqa: E712
        )
    )
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Infrastructure asset '{data.asset_id}' not found or is archived.",
        )

    # 2. If inspector_id is provided, verify user exists and is active
    initial_status = InspectionStatus.CREATED.value
    if data.inspector_id is not None:
        inspector = await db.scalar(select(User).where(User.id == data.inspector_id))
        if inspector is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assigned inspector user account '{data.inspector_id}' not found.",
            )
        if not inspector.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign inactive user as inspector.",
            )
        initial_status = InspectionStatus.ASSIGNED.value

    # 3. Create Inspection record
    inspection_dt = data.inspection_date or datetime.now(timezone.utc)
    inspection = Inspection(
        id=uuid.uuid4(),
        asset_id=data.asset_id,
        inspector_id=data.inspector_id,
        inspection_date=inspection_dt,
        status=initial_status,
        remarks=data.remarks.strip() if data.remarks else None,
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)

    await record_audit_event(
        db,
        action="INSPECTION_CREATED",
        resource_type="INSPECTION",
        resource_id=inspection.id,
        user_id=user_id,
        ip_address=ip_address,
    )
    logger.info("Inspection created: id=%s asset_id=%s status=%s", inspection.id, inspection.asset_id, inspection.status)
    return inspection


async def get_inspection_by_id(
    db: AsyncSession,
    inspection_id: uuid.UUID,
) -> Inspection | None:
    """Retrieve full inspection details including asset and assigned inspector."""
    query = (
        select(Inspection)
        .options(
            selectinload(Inspection.asset),
            selectinload(Inspection.inspector),
        )
        .where(Inspection.id == inspection_id)
    )
    result = await db.scalar(query)
    return result


async def list_inspections(
    db: AsyncSession,
    *,
    status_filter: str | None = None,
    asset_id: uuid.UUID | None = None,
    inspector_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[Inspection]:
    """Retrieve filtered inspections."""
    query = select(Inspection).options(
        selectinload(Inspection.asset),
        selectinload(Inspection.inspector),
    )

    if status_filter:
        try:
            norm_status = InspectionStatus.from_str(status_filter).value
            query = query.where(Inspection.status == norm_status)
        except ValueError:
            return []

    if asset_id:
        query = query.where(Inspection.asset_id == asset_id)

    if inspector_id:
        query = query.where(Inspection.inspector_id == inspector_id)

    query = query.order_by(Inspection.inspection_date.desc(), Inspection.created_at.desc()).offset(offset).limit(limit)
    result = await db.scalars(query)
    return result.all()


async def update_inspection(
    db: AsyncSession,
    inspection: Inspection,
    data: InspectionUpdateRequest,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> Inspection:
    """Update inspection date or notes."""
    if data.inspection_date is not None:
        inspection.inspection_date = data.inspection_date
    if data.remarks is not None:
        inspection.remarks = data.remarks.strip() if data.remarks else None

    await db.commit()
    await db.refresh(inspection)

    await record_audit_event(
        db,
        action="INSPECTION_UPDATED",
        resource_type="INSPECTION",
        resource_id=inspection.id,
        user_id=user_id,
        ip_address=ip_address,
    )
    return inspection


async def assign_inspector(
    db: AsyncSession,
    inspection: Inspection,
    inspector_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> Inspection:
    """Assign or reassign an active inspector and transition status to ASSIGNED."""
    inspector = await db.scalar(select(User).where(User.id == inspector_id))
    if inspector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspector account '{inspector_id}' not found.",
        )
    if not inspector.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign inactive user as inspector.",
        )

    inspection.inspector_id = inspector_id
    if inspection.status in [InspectionStatus.CREATED.value, InspectionStatus.ASSIGNED.value]:
        inspection.status = InspectionStatus.ASSIGNED.value

    await db.commit()
    await db.refresh(inspection)

    await record_audit_event(
        db,
        action="INSPECTION_ASSIGNED",
        resource_type="INSPECTION",
        resource_id=inspection.id,
        user_id=user_id,
        ip_address=ip_address,
    )
    logger.info("Inspection %s assigned to inspector %s", inspection.id, inspector.email)
    return inspection


async def update_inspection_status(
    db: AsyncSession,
    inspection: Inspection,
    new_status: str | InspectionStatus,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> Inspection:
    """Validate and transition an inspection to a new status."""
    norm_status = InspectionStatus.from_str(str(new_status)).value
    old_status = inspection.status
    inspection.status = norm_status

    await db.commit()
    await db.refresh(inspection)

    await record_audit_event(
        db,
        action="INSPECTION_STATUS_UPDATED",
        resource_type="INSPECTION",
        resource_id=inspection.id,
        user_id=user_id,
        ip_address=ip_address,
    )
    logger.info("Inspection %s status changed from %s to %s", inspection.id, old_status, norm_status)
    return inspection


async def get_inspection_images(
    db: AsyncSession,
    inspection_id: uuid.UUID,
) -> list[dict]:
    """Retrieve inspection images or return empty collection ready for Module 3."""
    # Check if inspection exists
    inspection = await db.scalar(select(Inspection.id).where(Inspection.id == inspection_id))
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    # Clean query stub ready for Module 3 Image Upload integration
    try:
        from backend.models.prediction import Prediction  # noqa: F401
    except Exception:
        pass

    return []
