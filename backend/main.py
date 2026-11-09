from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes.assets import router as assets_router
from backend.api.routes.health import router as health_router
from backend.api.routes.inspections import router as inspections_router
from backend.api.routes.predictions import (
    images_router,
    router as predictions_router,
)
from backend.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure runtime directories exist on application startup."""
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="InfraScan API",
    description="Backend API for AI-powered civil infrastructure crack and damage assessment.",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for stored infrastructure inspection images
upload_dir_path = Path(settings.UPLOAD_DIR)
upload_dir_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir_path)), name="uploads")

# Health check & root endpoints
app.include_router(health_router, tags=["Health"])

# Core domain routers (accessible directly and via /api/v1 prefix)
app.include_router(inspections_router)
app.include_router(inspections_router, prefix=settings.API_PREFIX)

app.include_router(assets_router)
app.include_router(assets_router, prefix=settings.API_PREFIX)

# Image upload routers
app.include_router(images_router)
app.include_router(images_router, prefix=settings.API_PREFIX)

# Phase 3 AI Inference & Predictions Router
app.include_router(predictions_router, prefix=settings.API_PREFIX)
app.include_router(predictions_router)


@app.get("/", tags=["Root"])
def root():
    """Basic API welcome endpoint."""
    return {
        "name": "InfraScan API",
        "version": "0.3.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "image_upload": "/images/upload",
            "predictions_analyze": f"{settings.API_PREFIX}/predictions/analyze",
            "assets": f"{settings.API_PREFIX}/assets",
            "inspections": f"{settings.API_PREFIX}/inspections",
        },
    }
