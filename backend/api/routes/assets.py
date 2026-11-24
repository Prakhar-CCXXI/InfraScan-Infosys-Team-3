from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_db
from backend.models.asset import InfrastructureAsset

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", summary="List all infrastructure assets (Frontend Dropdown)")
@router.get("/", summary="List all infrastructure assets (Frontend Dropdown)")
async def list_assets(db: AsyncSession = Depends(get_async_db)):
    """Retrieve assets formatted for frontend dropdown selection."""
    query = select(InfrastructureAsset).where(InfrastructureAsset.is_archived == False).order_by(InfrastructureAsset.created_at.desc())
    result = await db.scalars(query)
    assets = result.all()

    items = []
    for idx, a in enumerate(assets, 1):
        items.append({
            "id": str(a.id),
            "name": a.asset_name,
            "type": a.asset_type.capitalize() if a.asset_type else "Structure",
            "location": a.location,
            "status": "OPERATIONAL",
        })

    # Fallback to default mock assets if table is empty
    if not items:
        items = [
            {"id": "INF-001", "name": "Marina Flyover", "type": "Bridges", "location": "Chennai, TN"},
            {"id": "INF-002", "name": "Adyar Retaining Wall B", "type": "Retaining walls", "location": "Adyar, Chennai"},
            {"id": "INF-003", "name": "Metro Tunnel Section 4", "type": "Tunnels", "location": "Anna Salai, Chennai"},
        ]

    return items
