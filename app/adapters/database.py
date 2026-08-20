"""SQLAlchemy 2.0 async engine and session maker."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

_engine: AsyncEngine | None = None
_async_session_maker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the shared async engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600,
            # asyncpg prepared statements are incompatible with PgBouncer
            # transaction pooling; disabling the statement cache uses the
            # simple protocol and works across pooled backend connections.
            connect_args={"statement_cache_size": 0},
        )
    return _engine


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Return the shared session maker."""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _async_session_maker


async def close_engine() -> None:
    """Dispose the engine pool on shutdown."""
    global _engine, _async_session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
