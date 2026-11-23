"""Router for inspection scheduling, assignments, status transitions, and queries."""

import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.permissions import (
    require_inspection_creator,
    require_inspector_assigner,
    require_viewer,
)
from backend.app.db.session import get_async_db
from backend.app.models.user import User
from backend.app.schemas.inspection import (
    InspectionAssignRequest,
    InspectionCreateRequest,
    InspectionImageResponse,
    InspectionResponse,
    InspectionStatusUpdateRequest,
    InspectionUpdateRequest,
)
from backend.app.services.audit_service import extract_client_ip
from backend.app.services.inspection_service import (
    assign_inspector,
    create_inspection,
    get_inspection_by_id,
    get_inspection_images,
    list_inspections,
    update_inspection,
    update_inspection_status,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/inspections", tags=["Infrastructure Inspections"])


@router.post(
    "",
    response_model=InspectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Infrastructure Inspection",
    description="Schedule a new inspection. Verifies asset existence and active inspector status.",
)
@router.post(
    "/",
    response_model=InspectionResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def create_new_inspection(
    payload: InspectionCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_inspection_creator)],
    db: AsyncSession = Depends(get_async_db),
) -> InspectionResponse:
    """Schedule a new inspection workflow."""
    client_ip = extract_client_ip(request)
    inspection = await create_inspection(
        db,
        data=payload,
        user_id=current_user.id,
        ip_address=client_ip,
    )
    return InspectionResponse.model_validate(inspection)


@router.get(
    "",
    response_model=list[InspectionResponse],
    summary="List Inspections",
    description="Retrieve inspections filtered by status, asset, or inspector.",
)
@router.get(
    "/",
    response_model=list[InspectionResponse],
    include_in_schema=False,
)
async def get_all_inspections(
    _user: Annotated[User, Depends(require_viewer)],
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status (e.g., ASSIGNED, COMPLETED)"),
    asset_id: str | None = Query(default=None, description="Filter by asset UUID"),
    inspector_id: str | None = Query(default=None, description="Filter by inspector UUID"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_db),
) -> list[InspectionResponse]:
    """Retrieve inspections with optional filters."""
    parsed_asset_uuid = None
    if asset_id:
        try:
            parsed_asset_uuid = uuid.UUID(asset_id)
        except ValueError:
            return []

    parsed_inspector_uuid = None
    if inspector_id:
        try:
            parsed_inspector_uuid = uuid.UUID(inspector_id)
        except ValueError:
            return []

    inspections = await list_inspections(
        db,
        status_filter=status_filter,
        asset_id=parsed_asset_uuid,
        inspector_id=parsed_inspector_uuid,
        limit=limit,
        offset=offset,
    )
    return [InspectionResponse.model_validate(i) for i in inspections]


@router.get(
    "/{inspection_id}",
    response_model=InspectionResponse,
    summary="Get Inspection Details",
    description="Retrieve full details for an inspection.",
)
async def get_inspection_details(
    inspection_id: str,
    _user: Annotated[User, Depends(require_viewer)],
    db: AsyncSession = Depends(get_async_db),
) -> InspectionResponse:
    """Retrieve an inspection by its UUID."""
    try:
        parsed_uuid = uuid.UUID(inspection_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    inspection = await get_inspection_by_id(db, parsed_uuid)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )
    return InspectionResponse.model_validate(inspection)


@router.put(
    "/{inspection_id}",
    response_model=InspectionResponse,
    summary="Update Inspection Details",
    description="Update scheduled inspection date or notes/remarks.",
)
async def update_inspection_record(
    inspection_id: str,
    payload: InspectionUpdateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_inspection_creator)],
    db: AsyncSession = Depends(get_async_db),
) -> InspectionResponse:
    """Update date or notes of an inspection."""
    try:
        parsed_uuid = uuid.UUID(inspection_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    inspection = await get_inspection_by_id(db, parsed_uuid)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    client_ip = extract_client_ip(request)
    updated = await update_inspection(
        db,
        inspection=inspection,
        data=payload,
        user_id=current_user.id,
        ip_address=client_ip,
    )
    return InspectionResponse.model_validate(updated)


@router.patch(
    "/{inspection_id}/assign",
    response_model=InspectionResponse,
    summary="Assign Inspector",
    description="Assign an active inspector to an inspection. Restricted to Engineers, Managers, and Admins.",
)
async def assign_inspection_inspector(
    inspection_id: str,
    payload: InspectionAssignRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_inspector_assigner)],
    db: AsyncSession = Depends(get_async_db),
) -> InspectionResponse:
    """Assign or reassign an active inspector to an inspection."""
    try:
        parsed_uuid = uuid.UUID(inspection_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    inspection = await get_inspection_by_id(db, parsed_uuid)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    client_ip = extract_client_ip(request)
    assigned = await assign_inspector(
        db,
        inspection=inspection,
        inspector_id=payload.inspector_id,
        user_id=current_user.id,
        ip_address=client_ip,
    )
    return InspectionResponse.model_validate(assigned)


@router.patch(
    "/{inspection_id}/status",
    response_model=InspectionResponse,
    summary="Update Inspection Status",
    description="Advance or update inspection lifecycle status.",
)
async def update_inspection_status_endpoint(
    inspection_id: str,
    payload: InspectionStatusUpdateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_inspection_creator)],
    db: AsyncSession = Depends(get_async_db),
) -> InspectionResponse:
    """Update status of an inspection."""
    try:
        parsed_uuid = uuid.UUID(inspection_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    inspection = await get_inspection_by_id(db, parsed_uuid)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    client_ip = extract_client_ip(request)
    updated = await update_inspection_status(
        db,
        inspection=inspection,
        new_status=payload.status,
        user_id=current_user.id,
        ip_address=client_ip,
    )
    return InspectionResponse.model_validate(updated)


@router.get(
    "/{inspection_id}/images",
    response_model=list[InspectionImageResponse],
    summary="Get Inspection Images",
    description="Retrieve images captured during this inspection.",
)
async def get_images_for_inspection(
    inspection_id: str,
    _user: Annotated[User, Depends(require_viewer)],
    db: AsyncSession = Depends(get_async_db),
) -> list[InspectionImageResponse]:
    """Retrieve images uploaded for this inspection."""
    try:
        parsed_uuid = uuid.UUID(inspection_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found.",
        )

    images = await get_inspection_images(db, parsed_uuid)
    return [InspectionImageResponse.model_validate(img) for img in images]
