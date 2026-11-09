from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_async_db
from backend.models.asset import InfrastructureAsset

router = APIRouter(prefix="/assets", tags=["Assets"])


@router.get("", summary="List all infrastructure assets")
@router.get("/", summary="List all infrastructure assets")
async def list_assets(db: AsyncSession = Depends(get_async_db)):
    """Retrieve all monitored assets for dashboard and upload selection."""
    query = select(InfrastructureAsset).order_by(InfrastructureAsset.id.asc())
    result = await db.execute(query)
    assets = result.scalars().all()

    # If database has assets, format with formatted ID (INF-001, etc.)
    items = []
    for a in assets:
        formatted_id = f"INF-{a.id:03d}"
        items.append({
            "id": formatted_id,
            "db_id": a.id,
            "name": a.name,
            "type": a.type.capitalize() if a.type else "Structure",
            "location": a.location,
            "status": a.status,
        })

    # Fallback to default assets if table is empty
    if not items:
        items = [
            {"id": "INF-001", "db_id": 1, "name": "Marina Flyover", "type": "Bridges", "location": "Chennai, TN"},
            {"id": "INF-002", "db_id": 2, "name": "Adyar Retaining Wall B", "type": "Retaining walls", "location": "Adyar, Chennai"},
            {"id": "INF-003", "db_id": 3, "name": "Metro Tunnel Section 4", "type": "Tunnels", "location": "Anna Salai, Chennai"},
        ]

    return items
