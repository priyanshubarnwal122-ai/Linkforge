"""
app/models/click.py — Every redirect creates one of these rows.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, UUIDMixin


class ClickEvent(Base, UUIDMixin):
    __tablename__ = "click_events"

    link_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("links.id", ondelete="CASCADE"), nullable=False, index=True
    )
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Where did the click come from?
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)   # supports IPv6
    referer: Mapped[str | None] = mapped_column(String(500), nullable=True)     # e.g. "twitter.com"

    # Parsed from User-Agent header (no library — just string matching)
    browser: Mapped[str | None] = mapped_column(String(50), nullable=True)      # Chrome, Firefox, Safari…
    device_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # Mobile, Desktop, Tablet

    def __repr__(self) -> str:
        return f"<Click link={self.link_id} at={self.clicked_at}>"
