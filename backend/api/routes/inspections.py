
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.models.asset import InfrastructureAsset
from backend.models.inspection import Inspection
from backend.schemas.inspection import (
    InfrastructureType,
    InspectionCreate,
    InspectionResponse,
)

router = APIRouter(prefix="/inspections", tags=["Inspections"])


def get_asset_type(asset_type: str) -> InfrastructureType:
    normalized = asset_type.lower().strip().rstrip("s")

    if normalized in {"bridge", "building", "road", "dam"}:
        return InfrastructureType(normalized)

    return InfrastructureType.other


@router.post(
    "/",
    response_model=InspectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inspection(
    payload: InspectionCreate,
    db: Session = Depends(get_db),
):
    """Create an inspection for an existing infrastructure asset."""

    match = re.fullmatch(r"INF-(\d+)", payload.assetId)

    if not match:
        raise HTTPException(
            status_code=400,
            detail="Invalid infrastructure asset ID",
        )

    asset_id = int(match.group(1))
    asset = db.get(InfrastructureAsset, asset_id)

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Infrastructure asset not found",
        )

    db_inspection = Inspection(
        asset_id=asset.id,
        inspection_date=payload.date,
        inspector=payload.inspector,
        infrastructure_name=asset.name,
        infrastructure_type=get_asset_type(asset.type),
        location=asset.location,
        status=payload.status,
        description=None,
    )

    db.add(db_inspection)
    db.commit()
    db.refresh(db_inspection)

    return db_inspection


@router.get("/", response_model=list[InspectionResponse])
def list_inspections(db: Session = Depends(get_db)):
    """Retrieve all inspection records."""
    return db.scalars(
        select(Inspection).order_by(Inspection.id.asc())
    ).all()


@router.get("/{inspection_id}", response_model=InspectionResponse)
def get_inspection(
    inspection_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve an inspection record by its ID."""

    inspection = db.get(Inspection, inspection_id)

    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    return inspection
