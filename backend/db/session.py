"""Backward compatibility session module pointing to backend.app.db.session."""

from backend.app.db.session import (
    AsyncSessionLocal,
    Base,
    SessionLocal,
    async_engine,
    engine,
    get_async_db,
    get_db,
)

__all__ = [
    "AsyncSessionLocal",
    "Base",
    "SessionLocal",
    "async_engine",
    "engine",
    "get_async_db",
    "get_db",
]
