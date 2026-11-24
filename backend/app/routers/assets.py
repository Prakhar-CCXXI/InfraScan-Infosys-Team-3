"""Router for infrastructure asset registration, querying, updating, and archiving."""

import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.permissions import require_asset_editor, require_viewer
from backend.app.db.session import get_async_db
from backend.app.models.user import User
from backend.app.schemas.asset import AssetCreateRequest, AssetResponse, AssetUpdateRequest
from backend.app.schemas.inspection import InspectionResponse
from backend.app.services.asset_service import (
    archive_asset,
    create_asset,
    get_asset_by_id,
    get_asset_inspections,
    list_assets,
    update_asset,
)
from backend.app.services.audit_service import extract_client_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["Infrastructure Assets"])


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New Infrastructure Asset",
    description="Register a new civil asset (BRIDGE, ROAD, BUILDING, TUNNEL, DAM). Restricted to Engineers, Managers, and Admins.",
)
@router.post(
    "/",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_new_asset(
    payload: AssetCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_asset_editor)],
    db: AsyncSession = Depends(get_async_db),
) -> AssetResponse:
    """Register a new civil infrastructure asset."""
    client_ip = extract_client_ip(request)
    asset = await create_asset(
        db,
        data=payload,
        user_id=current_user.id,
        ip_address=client_ip,
    )
    return AssetResponse.model_validate(asset)


@router.get(
    "",
    response_model=list[AssetResponse],
    summary="List Infrastructure Assets",
    description="Retrieve all non-archived assets with optional filtering and search.",
)
@router.get(
    "/",
    response_model=list[AssetResponse],
    include_in_schema=False,
)
async def get_all_assets(
    _user: Annotated[User, Depends(require_viewer)],
    asset_type: str | None = Query(default=None, description="Filter by category (BRIDGE, ROAD, etc.)"),
    department: str | None = Query(default=None, description="Filter by overseeing department"),
    search: str | None = Query(default=None, description="Search term for asset name or location"),
    include_archived: bool = Query(default=False, description="Include archived records"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_db),
) -> list[AssetResponse]:
    """Retrieve non-archived infrastructure assets."""
    assets = await list_assets(
        db,
        asset_type=asset_type,
        department=department,
        search=search,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    return [AssetResponse.model_validate(a) for a in assets]


@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Get Asset Details",
    description="Retrieve full details of an active infrastructure asset.",
)
async def get_asset_details(
    asset_id: str,
    _user: Annotated[User, Depends(require_viewer)],
    db: AsyncSession = Depends(get_async_db),
) -> AssetResponse:
    """Retrieve an asset by UUID."""
    try:
        parsed_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found.",
        )

    asset = await get_asset_by_id(db, parsed_uuid)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Infrastructure asset '{asset_id}' not found.",
        )
    return AssetResponse.model_validate(asset)


@router.put(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Update Infrastructure Asset",
    description="Modify asset metadata. Restricted to Engineers, Managers, and Admins.",
)
async def update_existing_asset(
    asset_id: str,
    payload: AssetUpdateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_asset_editor)],
    db: AsyncSession = Depends(get_async_db),
) -> AssetResponse:
    """Update fields on an existing asset."""
    try:
        parsed_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found.",
        )

    asset = await get_asset_by_id(db, parsed_uuid)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Infrastructure asset '{asset_id}' not found.",
        )

    client_ip = extract_client_ip(request)
    updated = await update_asset(
        db,
        asset=asset,
        data=payload,
        user_id=current_user.id,
        ip_address=client_ip,
    )
    return AssetResponse.model_validate(updated)


@router.delete(
    "/{asset_id}",
    summary="Soft-Delete (Archive) Asset",
    description="Archive an infrastructure asset. Restricted to Engineers, Managers, and Admins.",
)
async def delete_asset(
    asset_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_asset_editor)],
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, str]:
    """Soft delete an infrastructure asset."""
    try:
        parsed_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found.",
        )

    asset = await get_asset_by_id(db, parsed_uuid)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Infrastructure asset '{asset_id}' not found.",
        )

    client_ip = extract_client_ip(request)
    archived = await archive_asset(
        db,
        asset=asset,
        user_id=current_user.id,
        ip_address=client_ip,
    )
    return {
        "message": f"Asset '{archived.asset_name}' successfully archived.",
        "id": str(archived.id),
        "status": "ARCHIVED",
    }


@router.get(
    "/{asset_id}/inspections",
    response_model=list[InspectionResponse],
    summary="Get Asset Inspection History Timeline",
    description="Retrieve the chronological historical timeline of inspections for an asset.",
)
async def get_asset_inspection_timeline(
    asset_id: str,
    _user: Annotated[User, Depends(require_viewer)],
    db: AsyncSession = Depends(get_async_db),
) -> list[InspectionResponse]:
    """Retrieve all historical inspections for an asset in reverse chronological order."""
    try:
        parsed_uuid = uuid.UUID(asset_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found.",
        )

    asset = await get_asset_by_id(db, parsed_uuid, include_archived=True)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Infrastructure asset '{asset_id}' not found.",
        )

    timeline = await get_asset_inspections(db, parsed_uuid)
    return [InspectionResponse.model_validate(i) for i in timeline]
