"""
app/models/url.py
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin, UUIDMixin


class URL(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "links"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    short_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    custom_alias: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)

    # Expiry
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_clicks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    click_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # -----------------------------------------------------------------------
    # Innovation 1: Password protection
    # -----------------------------------------------------------------------
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # -----------------------------------------------------------------------
    # Innovation 2: One-time / self-destructing links
    # -----------------------------------------------------------------------
    is_one_time: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    # -----------------------------------------------------------------------
    # Innovation 3: Device-specific redirect
    # -----------------------------------------------------------------------
    ios_url: Mapped[str | None] = mapped_column(Text, nullable=True)      # iPhone / iPad
    android_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # Android phones

    def __repr__(self) -> str:
        return f"<URL {self.short_code!r} → {self.original_url[:50]!r}>"
