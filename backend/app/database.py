"""
app/database.py — Database setup.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

import structlog
from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Base class all models inherit from
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# Every model gets a UUID primary key + created_at/updated_at automatically
class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4, server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------------------------------------------------------------------------
# Engine + Session
# ---------------------------------------------------------------------------

def _make_engine():
    s = get_settings()
    engine = create_async_engine(
        s.database_url,
        pool_size=s.db_pool_size,
        echo=s.db_echo,
        pool_pre_ping=True,   # test connections before using them
        pool_recycle=3600,    # replace connections every hour
    )
    log.info("db_connected", host=s.postgres_host, db=s.postgres_db)
    return engine


# Created once when the app starts, reused for every request
engine = _make_engine()
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Gives each request its own DB session. Auto-commits on success, rolls back on error."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    """Call this on app shutdown to cleanly close all DB connections."""
    await engine.dispose()
    log.info("db_disconnected")


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

async def create_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_all_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
