from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> parents[3] is the repository root
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "InfraScan API"
    ENVIRONMENT: str = "development"
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://infrascan_user:InfosysSP-Team3@localhost:5432/infrascan_db"
    ASYNC_DATABASE_URL: str | None = None

    # Security & JWT Tokens
    SECRET_KEY: str = "infrascan-secret-key-super-secure-change-in-production"
    SESSION_SECRET_KEY: str = "infrascan-session-encryption-secret-key-change-in-prod"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # 15 minutes as per Module 1 specification
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7     # 7 days as per Module 1 specification

    # Google OAuth2 Credentials
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Seed Admin Account
    FIRST_ADMIN_EMAIL: str = "admin@infrascan.gov"
    FIRST_ADMIN_PASSWORD: str = "Admin@Secure2026!"
    FIRST_ADMIN_NAME: str = "System Administrator"

    # Image upload configuration
    UPLOAD_DIR: str = "uploads"
    MAX_IMAGE_SIZE_MB: int = 15
    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
    ]

    # ML inference (data/ml/service/inference_service.py)
    # Relative paths are resolved against the repo root, not the CWD.
    # Both the plain name (UNET_CKPT) and the ML package's own env var
    # (INFRASCAN_UNET_CKPT) are accepted.
    # ------------------------------------------------------------------
    UNET_CKPT: str | None = Field(
        default="data/Crack500-YOLO-Segmentation/checkpoints/unet_best.pt",
        validation_alias=AliasChoices("UNET_CKPT", "INFRASCAN_UNET_CKPT"),
    )
    RDD_CKPT: str | None = Field(
        default="data/rdd2022_detection/checkpoints/yolo11s_rdd2022_s42/best.pt",
        validation_alias=AliasChoices("RDD_CKPT", "INFRASCAN_RDD_CKPT"),
    )
    # Optional crack-YOLO (hybrid close_up). Leave unset for U-Net-only mode.
    CRACK_YOLO_CKPT: str | None = Field(
        default=None,
        validation_alias=AliasChoices("CRACK_YOLO_CKPT", "INFRASCAN_YOLO_CKPT"),
    )
    HYBRID_CONFIG: str | None = Field(
        default=None,
        validation_alias=AliasChoices("HYBRID_CONFIG", "INFRASCAN_HYBRID_CONFIG"),
    )
    SEVERITY_CONFIG: str | None = Field(
        default=None,  # None -> severity_config.json next to severity_engine.py
        validation_alias=AliasChoices("SEVERITY_CONFIG", "INFRASCAN_SEVERITY_CONFIG"),
    )
    MODEL_REGISTRY_PATH: str | None = Field(
        default="data/ml/registry/model_registry.json",
        validation_alias=AliasChoices("MODEL_REGISTRY_PATH", "INFRASCAN_REGISTRY"),
    )
    VERIFY_MODEL_HASHES: bool = Field(
        default=True,
        validation_alias=AliasChoices("VERIFY_MODEL_HASHES", "INFRASCAN_VERIFY_HASHES"),
    )
    INFERENCE_DEVICE: str | None = Field(
        default=None,  # None -> auto (cuda if available)
        validation_alias=AliasChoices("INFERENCE_DEVICE", "INFRASCAN_DEVICE"),
    )
    DEFAULT_INFERENCE_PROFILE: str = "close_up"  # "close_up" | "road_scene"

    # Mock output is OFF by default. When true AND real models are unavailable,
    # the API returns clearly tagged mock data (source="mock") instead of 503.
    ALLOW_MOCK_INFERENCE: bool = False

    @property
    def async_database_url(self) -> str:
        """Resolve the async SQLAlchemy connection string with asyncpg/aiosqlite."""
        if self.ASYNC_DATABASE_URL:
            return self.ASYNC_DATABASE_URL
        if self.DATABASE_URL.startswith("postgresql+psycopg://"):
            return self.DATABASE_URL.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        if self.DATABASE_URL.startswith("sqlite:///"):
            return self.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
        if self.DATABASE_URL.startswith("sqlite://"):
            return self.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        return self.DATABASE_URL

    @property
    def max_image_size_bytes(self) -> int:
        return self.MAX_IMAGE_SIZE_MB * 1024 * 1024

    def resolve_path(self, value: str | None) -> str | None:
        """Absolute path for a configured file (relative -> repo root); '' / None -> None."""
        if value is None or not str(value).strip():
            return None
        p = Path(str(value).strip())
        return str(p if p.is_absolute() else (REPO_ROOT / p).resolve())


settings = Settings()