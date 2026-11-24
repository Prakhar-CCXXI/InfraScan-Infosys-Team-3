import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.session import Base


class UserRole(str, enum.Enum):
    """System roles for InfraScan Role-Based Access Control (RBAC)."""

    CIVIL_ENGINEER = "CIVIL_ENGINEER"
    INFRASTRUCTURE_INSPECTOR = "INFRASTRUCTURE_INSPECTOR"
    MAINTENANCE_ENGINEER = "MAINTENANCE_ENGINEER"
    INFRASTRUCTURE_MANAGER = "INFRASTRUCTURE_MANAGER"
    ADMIN = "ADMIN"

    @property
    def display_name(self) -> str:
        """User-friendly display label."""
        labels = {
            UserRole.CIVIL_ENGINEER: "Civil Engineer",
            UserRole.INFRASTRUCTURE_INSPECTOR: "Infrastructure Inspector",
            UserRole.MAINTENANCE_ENGINEER: "Maintenance Engineer",
            UserRole.INFRASTRUCTURE_MANAGER: "Infrastructure Manager",
            UserRole.ADMIN: "Administrator",
        }
        return labels.get(self, self.value)

    @classmethod
    def from_str(cls, value: str) -> "UserRole":
        """Parse role from either enum key, display name, or legacy aliases."""
        if isinstance(value, cls):
            return value
        cleaned = value.strip().upper().replace(" ", "_").replace("-", "_")
        aliases = {
            "ADMINISTRATOR": cls.ADMIN,
            "ADMIN": cls.ADMIN,
            "CIVIL_ENGINEER": cls.CIVIL_ENGINEER,
            "ENGINEER": cls.CIVIL_ENGINEER,
            "INFRASTRUCTURE_INSPECTOR": cls.INFRASTRUCTURE_INSPECTOR,
            "INSPECTOR": cls.INFRASTRUCTURE_INSPECTOR,
            "MAINTENANCE_ENGINEER": cls.MAINTENANCE_ENGINEER,
            "INFRASTRUCTURE_MANAGER": cls.INFRASTRUCTURE_MANAGER,
            "MANAGER": cls.INFRASTRUCTURE_MANAGER,
        }
        if cleaned in aliases:
            return aliases[cleaned]
        for role in cls:
            if role.value == cleaned:
                return role
        raise ValueError(f"Invalid user role '{value}'. Must be one of: {[r.value for r in cls]}")


class User(Base):
    """SQLAlchemy model representing a system user with RBAC."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            name="user_role",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=UserRole.INFRASTRUCTURE_INSPECTOR,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __init__(self, **kwargs):
        if "hashed_password" in kwargs and "password_hash" not in kwargs:
            kwargs["password_hash"] = kwargs.pop("hashed_password")
        if "name" in kwargs and "full_name" not in kwargs:
            kwargs["full_name"] = kwargs.pop("name")
        if "role" in kwargs and isinstance(kwargs["role"], str):
            kwargs["role"] = UserRole.from_str(kwargs["role"])
        if "full_name" not in kwargs and "email" in kwargs:
            prefix = str(kwargs["email"]).split("@")[0].replace(".", " ").title()
            kwargs["full_name"] = prefix
        super().__init__(**kwargs)

    @property
    def hashed_password(self) -> str:
        """Compatibility property for legacy code referencing hashed_password."""
        return self.password_hash

    @hashed_password.setter
    def hashed_password(self, value: str) -> None:
        self.password_hash = value

    @property
    def name(self) -> str:
        """Compatibility property for legacy code referencing name."""
        return self.full_name

    @name.setter
    def name(self, value: str) -> None:
        self.full_name = value

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
