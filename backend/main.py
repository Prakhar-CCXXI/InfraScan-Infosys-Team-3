from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from backend.api.routes.health import router as health_router
from backend.api.routes.predictions import (
    images_router,
    router as predictions_router,
)

from backend.api.routes.users import router as users_router
from backend.core.config import settings
from backend.db.session import Base, engine
from backend.services.ai_inference import get_ai_inference_service
import backend.models  # noqa: F401

from backend.app.core.config import settings
from backend.app.db.session import Base, engine
from backend.app.routers.admin import router as admin_router
from backend.app.routers.assets import router as assets_router
from backend.app.routers.auth import router as auth_router
from backend.app.routers.inspections import router as inspections_router
from backend.app.routers.users import router as users_router
import backend.app.models  # noqa: F401


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure runtime directories exist, verify tables, and create the shared InferenceService."""
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass


    # One shared InferenceService for the whole process. Model weights load lazily on the first
    # request of each profile; if anything is missing, requests get 503 (never fake predictions).
    ai_service = get_ai_inference_service()
    await run_in_threadpool(ai_service.initialise)
    h = ai_service.health()
    logger.info("Inference health at startup: status=%s profiles=%s mock_allowed=%s",
                h["status"], h["profiles"], h["mock_allowed"])

    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE infrastructure_assets ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE;"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_infrastructure_assets_is_archived ON infrastructure_assets (is_archived);"))
    except Exception:
        pass

    yield


app = FastAPI(
    title="InfraScan API",
    description="Backend API for AI-powered civil infrastructure crack and damage assessment.",
    version="1.0.0",
    lifespan=lifespan,
)

# Session middleware for Google OAuth2 state management
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY,
)

# CORS middleware
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


@app.get("/health/models", tags=["Health"])
def models_health():
    """Inference readiness: per-profile checkpoint availability, loaded model hashes, mock flag.

    HTTP 503 when neither profile can run (and mock output is not allowed)."""
    info = get_ai_inference_service().health()
    code = 503 if info["status"] == "unavailable" else 200
    return JSONResponse(info, status_code=code)


# Core domain routers (accessible directly and via /api/v1 prefix)
app.include_router(auth_router)

# Module 1 Routers

app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(auth_router)

app.include_router(users_router, prefix=settings.API_PREFIX)
app.include_router(users_router)

app.include_router(admin_router, prefix=settings.API_PREFIX)
app.include_router(admin_router)

# Module 2 Routers (Assets & Inspections)
app.include_router(assets_router, prefix=settings.API_PREFIX)
from backend.api.routes.assets import router as dropdown_assets_router
app.include_router(dropdown_assets_router)

app.include_router(inspections_router, prefix=settings.API_PREFIX)
app.include_router(inspections_router)

# Image upload routers
app.include_router(images_router, prefix=settings.API_PREFIX)
app.include_router(images_router)

# Phase 3 AI Inference & Predictions Router
app.include_router(predictions_router, prefix=settings.API_PREFIX)
app.include_router(predictions_router)


@app.get("/", tags=["Root"])
def root():
    """Basic API welcome endpoint."""
    return {
        "name": "InfraScan API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "model_health": "/health/models",
        "endpoints": {
            "auth_register": f"{settings.API_PREFIX}/auth/register",
            "auth_login": f"{settings.API_PREFIX}/auth/login",
            "assets": f"{settings.API_PREFIX}/assets",
            "inspections": f"{settings.API_PREFIX}/inspections",
            "users_me": f"{settings.API_PREFIX}/users/me",
            "admin_users": f"{settings.API_PREFIX}/admin/users",
            "admin_audit_logs": f"{settings.API_PREFIX}/admin/audit-logs",
            "image_upload": "/images/upload",
            "predictions_analyze": f"{settings.API_PREFIX}/predictions/analyze",
        },
    }
