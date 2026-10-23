from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.inspection import Inspection
from app.schemas.inspection import InspectionCreate, InspectionResponse

router = APIRouter(prefix="/inspections", tags=["Inspections"])


@router.post("/", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def create_inspection(payload: InspectionCreate, db: Session = Depends(get_db)):
    """Create a new inspection record."""
    db_inspection = Inspection(
        infrastructure_name=payload.infrastructure_name,
        infrastructure_type=payload.infrastructure_type,
        location=payload.location,
        description=payload.description,
    )
    db.add(db_inspection)
    db.commit()
    db.refresh(db_inspection)
    return db_inspection


@router.get("/", response_model=list[InspectionResponse])
def list_inspections(db: Session = Depends(get_db)):
    """Retrieve all inspection records."""
    inspections = db.scalars(select(Inspection)).all()
    return inspections


@router.get("/{inspection_id}", response_model=InspectionResponse)
def get_inspection(inspection_id: int, db: Session = Depends(get_db)):
    """Retrieve an inspection record by its ID."""
    inspection = db.get(Inspection, inspection_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )
    return inspection
