"""Async SQLAlchemy engine and session management for APES persistence."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://apes_user:apes_secret@localhost:5432/apes_db",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=os.environ.get("SQL_ECHO", "false").lower() == "true",
    pool_size=int(os.environ.get("DB_POOL_SIZE", "10")),
    max_overflow=int(os.environ.get("DB_MAX_OVERFLOW", "20")),
    pool_pre_ping=True,
    pool_recycle=int(os.environ.get("DB_POOL_RECYCLE", "3600")),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one transaction-scoped async session."""

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create tables when running outside Docker's init SQL flow."""

    from backend.app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified")


def db_enabled() -> bool:
    """Return whether persistence should be attempted for this process."""

    return os.environ.get("APES_ENABLE_DB", "false").lower() in {"1", "true", "yes", "on"}


def db_required() -> bool:
    """Return whether DB startup failures should crash the backend."""

    return os.environ.get("APES_DB_REQUIRED", "false").lower() in {"1", "true", "yes", "on"}
