from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Check API health")
def health_check():
    """Return a simple status response to verify that the API is running."""
    return {"status": "ok", "service": "infrascan-api"}
