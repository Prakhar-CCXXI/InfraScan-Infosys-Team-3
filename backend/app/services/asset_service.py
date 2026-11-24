"""Asset service handling asynchronous database transactions, filtering, and audit logging."""

import logging
from typing import Sequence
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.asset import AssetType, InfrastructureAsset
from backend.app.models.inspection import Inspection
from backend.app.schemas.asset import AssetCreateRequest, AssetUpdateRequest
from backend.app.services.audit_service import record_audit_event

logger = logging.getLogger(__name__)


async def create_asset(
    db: AsyncSession,
    data: AssetCreateRequest,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> InfrastructureAsset:
    """Create a new infrastructure asset and write audit trail."""
    # Ensure asset_type is valid
    normalized_type = AssetType.from_str(str(data.asset_type)).value

    asset = InfrastructureAsset(
        id=uuid.uuid4(),
        asset_name=data.asset_name.strip(),
        asset_type=normalized_type,
        location=data.location.strip(),
        latitude=data.latitude,
        longitude=data.longitude,
        construction_year=data.construction_year,
        material_type=data.material_type.strip() if data.material_type else None,
        department=data.department.strip() if data.department else None,
        inspection_frequency=data.inspection_frequency,
        is_archived=False,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    await record_audit_event(
        db,
        action="ASSET_CREATED",
        resource_type="ASSET",
        resource_id=asset.id,
        user_id=user_id,
        ip_address=ip_address,
    )
    logger.info("Asset created: id=%s name='%s' type=%s", asset.id, asset.asset_name, asset.asset_type)
    return asset


async def get_asset_by_id(
    db: AsyncSession,
    asset_id: uuid.UUID,
    include_archived: bool = False,
) -> InfrastructureAsset | None:
    """Retrieve an asset by UUID. Ignores archived records unless specified."""
    query = select(InfrastructureAsset).where(InfrastructureAsset.id == asset_id)
    if not include_archived:
        query = query.where(InfrastructureAsset.is_archived == False)  # noqa: E712
    result = await db.scalar(query)
    return result


async def list_assets(
    db: AsyncSession,
    *,
    asset_type: str | None = None,
    department: str | None = None,
    search: str | None = None,
    include_archived: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> Sequence[InfrastructureAsset]:
    """Retrieve non-archived infrastructure assets with optional filtering and search."""
    query = select(InfrastructureAsset)

    if not include_archived:
        query = query.where(InfrastructureAsset.is_archived == False)  # noqa: E712

    if asset_type:
        try:
            norm_type = AssetType.from_str(asset_type).value
            query = query.where(InfrastructureAsset.asset_type == norm_type)
        except ValueError:
            # If invalid filter passed, return empty list cleanly
            return []

    if department:
        query = query.where(func.lower(InfrastructureAsset.department) == department.strip().lower())

    if search:
        search_pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(InfrastructureAsset.asset_name).ilike(search_pattern),
                func.lower(InfrastructureAsset.location).ilike(search_pattern),
            )
        )

    query = query.order_by(InfrastructureAsset.created_at.desc()).offset(offset).limit(limit)
    result = await db.scalars(query)
    return result.all()


async def update_asset(
    db: AsyncSession,
    asset: InfrastructureAsset,
    data: AssetUpdateRequest,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> InfrastructureAsset:
    """Update fields on an existing infrastructure asset."""
    if data.asset_name is not None:
        asset.asset_name = data.asset_name.strip()
    if data.asset_type is not None:
        asset.asset_type = AssetType.from_str(str(data.asset_type)).value
    if data.location is not None:
        asset.location = data.location.strip()
    if data.latitude is not None:
        asset.latitude = data.latitude
    if data.longitude is not None:
        asset.longitude = data.longitude
    if data.construction_year is not None:
        asset.construction_year = data.construction_year
    if data.material_type is not None:
        asset.material_type = data.material_type.strip()
    if data.department is not None:
        asset.department = data.department.strip()
    if data.inspection_frequency is not None:
        asset.inspection_frequency = data.inspection_frequency

    await db.commit()
    await db.refresh(asset)

    await record_audit_event(
        db,
        action="ASSET_UPDATED",
        resource_type="ASSET",
        resource_id=asset.id,
        user_id=user_id,
        ip_address=ip_address,
    )
    return asset


async def archive_asset(
    db: AsyncSession,
    asset: InfrastructureAsset,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> InfrastructureAsset:
    """Soft-delete an infrastructure asset by setting is_archived = True."""
    asset.is_archived = True
    await db.commit()
    await db.refresh(asset)

    await record_audit_event(
        db,
        action="ASSET_ARCHIVED",
        resource_type="ASSET",
        resource_id=asset.id,
        user_id=user_id,
        ip_address=ip_address,
    )
    logger.info("Asset archived: id=%s name='%s'", asset.id, asset.asset_name)
    return asset


async def get_asset_inspections(
    db: AsyncSession,
    asset_id: uuid.UUID,
) -> Sequence[Inspection]:
    """Retrieve the chronological historical inspection timeline for an asset."""
    query = (
        select(Inspection)
        .where(Inspection.asset_id == asset_id)
        .order_by(Inspection.inspection_date.desc(), Inspection.created_at.desc())
    )
    result = await db.scalars(query)
    return result.all()
