import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # ML Model Settings
    CLASSIFIER_WEIGHTS_PATH: str = "data/sdnet2018_classification/checkpoints/mobilenet_v3_large/best.pt"
    YOLO_SEG_WEIGHTS_PATH: str = "data/Crack500-YOLO-Segmentation/checkpoints/yolo11n-seg.pt"
    UNET_WEIGHTS_PATH: str = "data/Crack500-YOLO-Segmentation/checkpoints/unet_resnet34.pt"
    DEVICE: str = "cuda" if os.environ.get("USE_CUDA") == "1" else "cpu"

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


settings = Settings()
