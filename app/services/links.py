"""
app/services/links.py — URL shortening service.

Features:
  1. Click-budget expiry      — link dies after N clicks (original)
  2. Auto-title fetch         — og:title grabbed in background (original)
  3. Password protection      — bcrypt-verify before redirecting (new)
  4. One-time / self-destruct — link soft-deletes after first click (new)
  5. Device-specific redirect — iOS/Android/desktop get different URLs (new)
"""
from __future__ import annotations

import re
import secrets
import string
import uuid
from datetime import UTC, datetime

import httpx
import structlog
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import AuthenticationError, ConflictError, LinkExpiredError, NotFoundError
from app.models.url import URL
from app.schemas import LinkCreate, LinkResponse
from app.security import hash_password, verify_password

log = structlog.get_logger(__name__)

_ALPHABET = string.ascii_letters + string.digits  # A-Za-z0-9  (62 chars)


# ---------------------------------------------------------------------------
# Short code generator
# ---------------------------------------------------------------------------

async def _unique_code(session: AsyncSession, length: int) -> str:
    for _ in range(10):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        taken = await session.execute(select(URL).where(URL.short_code == code))
        if not taken.scalars().first():
            return code
    raise ConflictError("Couldn't generate a unique code — please try again.")


# ---------------------------------------------------------------------------
# Device-specific redirect (Innovation 3)
# ---------------------------------------------------------------------------

def pick_destination(link: URL, user_agent: str | None) -> str:
    """
    Pick the right destination URL based on the visitor's device.
    Falls back to original_url if no device-specific URL is configured.
    """
    if user_agent:
        ua = user_agent.lower()
        if link.ios_url and ("iphone" in ua or "ipad" in ua):
            return link.ios_url
        if link.android_url and "android" in ua:
            return link.android_url
    return link.original_url


# ---------------------------------------------------------------------------
# Response builder
# ---------------------------------------------------------------------------

def build_response(link: URL) -> LinkResponse:
    s = get_settings()
    active_code = link.custom_alias or link.short_code
    return LinkResponse(
        id=link.id,
        short_code=link.short_code,
        custom_alias=link.custom_alias,
        original_url=link.original_url,
        title=link.title,
        short_url=f"{s.base_url}/{active_code}",
        expires_at=link.expires_at,
        max_clicks=link.max_clicks,
        click_count=link.click_count,
        is_active=link.is_active,
        created_at=link.created_at,
        is_password_protected=link.password_hash is not None,
        is_one_time=link.is_one_time,
        ios_url=link.ios_url,
        android_url=link.android_url,
    )


# ---------------------------------------------------------------------------
# Background task — auto-fetch page title
# ---------------------------------------------------------------------------

async def _fetch_title(link_id: uuid.UUID, url: str) -> None:
    from app.database import SessionLocal

    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "LinkForge/1.0 (+title-fetch)"})

        match = re.search(
            r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
            resp.text, re.IGNORECASE,
        ) or re.search(r'<title[^>]*>([^<]+)</title>', resp.text, re.IGNORECASE)

        title = match.group(1).strip()[:300] if match else None
        if not title:
            return

        async with SessionLocal() as session:
            result = await session.execute(select(URL).where(URL.id == link_id))
            link = result.scalars().first()
            if link and not link.title:
                link.title = title
                await session.commit()
                log.info("title_fetched", link_id=str(link_id), title=title)

    except Exception:
        pass


# ---------------------------------------------------------------------------
# Link Service
# ---------------------------------------------------------------------------

class LinkService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: LinkCreate, user_id: str, background_tasks: BackgroundTasks) -> URL:
        s = get_settings()

        if data.custom_alias:
            alias = data.custom_alias.lower().strip()
            taken = await self.session.execute(
                select(URL).where(URL.custom_alias == alias, URL.deleted_at.is_(None))
            )
            if taken.scalars().first():
                raise ConflictError(f"Alias '{alias}' is already taken. Choose a different one.")
        else:
            alias = None

        short_code = await _unique_code(self.session, s.short_code_length)

        link = URL(
            user_id=uuid.UUID(user_id),
            original_url=data.original_url,
            short_code=short_code,
            custom_alias=alias,
            expires_at=data.expires_at,
            max_clicks=data.max_clicks,
            # Innovation 1
            password_hash=hash_password(data.password) if data.password else None,
            # Innovation 2
            is_one_time=data.is_one_time,
            # Innovation 3
            ios_url=data.ios_url,
            android_url=data.android_url,
        )
        self.session.add(link)
        await self.session.flush()
        await self.session.refresh(link)

        log.info("link_created", link_id=str(link.id), code=short_code, user_id=user_id,
                 password_protected=data.password is not None,
                 one_time=data.is_one_time,
                 device_redirect=bool(data.ios_url or data.android_url))

        background_tasks.add_task(_fetch_title, link.id, data.original_url)
        return link

    async def get_user_links(self, user_id: str, skip: int = 0, limit: int = 20) -> list[URL]:
        result = await self.session.execute(
            select(URL)
            .where(URL.user_id == uuid.UUID(user_id), URL.deleted_at.is_(None))
            .order_by(URL.created_at.desc())
            .offset(skip).limit(min(limit, 100))
        )
        return list(result.scalars().all())

    async def get_one(self, link_id: str, user_id: str) -> URL:
        result = await self.session.execute(
            select(URL).where(
                URL.id == uuid.UUID(link_id),
                URL.user_id == uuid.UUID(user_id),
                URL.deleted_at.is_(None),
            )
        )
        link = result.scalars().first()
        if not link:
            raise NotFoundError("Link not found.")
        return link

    async def toggle_active(self, link_id: str, user_id: str) -> URL:
        link = await self.get_one(link_id, user_id)
        link.is_active = not link.is_active
        self.session.add(link)
        await self.session.flush()
        await self.session.refresh(link)
        return link

    async def delete(self, link_id: str, user_id: str) -> None:
        link = await self.get_one(link_id, user_id)
        link.deleted_at = datetime.now(UTC)
        self.session.add(link)
        await self.session.flush()
        log.info("link_deleted", link_id=link_id, user_id=user_id)

    async def redirect(self, code: str, password: str | None = None) -> URL:
        """
        The redirect hot path — handles all three innovations:
          1. Password check before serving
          2. Device routing (done in router via pick_destination)
          3. One-time: soft-delete immediately after serving
        """
        result = await self.session.execute(
            select(URL).where(
                ((URL.short_code == code) | (URL.custom_alias == code)),
                URL.is_active.is_(True),
                URL.deleted_at.is_(None),
            )
        )
        link = result.scalars().first()

        if not link:
            raise NotFoundError(f"'{code}' — link not found or has been removed.")

        # Innovation 1: Password check
        if link.password_hash:
            if not password:
                raise AuthenticationError(
                    "This link is password-protected. "
                    "Add ?pw=yourpassword to the URL."
                )
            if not verify_password(password, link.password_hash):
                log.warning("wrong_password", code=code)
                raise AuthenticationError("Incorrect password.")

        # Expiry checks
        if link.expires_at and link.expires_at < datetime.now(UTC):
            raise LinkExpiredError("This link has expired.")

        if link.max_clicks is not None and link.click_count >= link.max_clicks:
            raise LinkExpiredError(
                f"This link reached its {link.max_clicks}-click limit and is no longer active."
            )

        # Innovation 2: One-time link — soft delete immediately
        if link.is_one_time:
            link.deleted_at = datetime.now(UTC)
            log.info("one_time_link_consumed", code=code, link_id=str(link.id))
        else:
            link.click_count += 1

        self.session.add(link)
        await self.session.flush()

        return link
