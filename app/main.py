from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.health import router as health_router
from app.api.routes.inspections import router as inspections_router
from app.db.session import Base, engine
from app.models.inspection import Inspection  # Ensure model is registered on Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="InfraScan API",
    description="Backend API for AI-powered civil infrastructure crack and damage assessment.",
    version="0.1.0",
    lifespan=lifespan,
)

# Update the allowed origins to match the frontend URL when it is available.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["Health"])
app.include_router(inspections_router)


@app.get("/", tags=["Root"])
def root():
    """Basic API welcome endpoint."""
    return {
        "name": "InfraScan API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
