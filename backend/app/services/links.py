"""
app/services/links.py — URL shortening service.
Features: short code generation, custom alias, click budget, password protection, self-destruct, device routing, background title fetching.
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
_ALPHABET = string.ascii_letters + string.digits


async def _unique_code(session: AsyncSession, length: int) -> str:
    for _ in range(10):
        code = "".join(secrets.choice(_ALPHABET) for _ in range(length))
        if not (await session.execute(select(URL).where(URL.short_code == code))).scalars().first():
            return code
    raise ConflictError("Could not generate a unique short code. Try again.")


def pick_destination(link: URL, user_agent: str | None) -> str:
    """Pick destination URL based on visitor's device (iOS, Android, or fallback)."""
    if user_agent:
        ua = user_agent.lower()
        if link.ios_url and ("iphone" in ua or "ipad" in ua):
            return link.ios_url
        if link.android_url and "android" in ua:
            return link.android_url
    return link.original_url


def build_response(link: URL) -> LinkResponse:
    s = get_settings()
    code = link.custom_alias or link.short_code
    return LinkResponse(
        id=link.id,
        short_code=link.short_code,
        custom_alias=link.custom_alias,
        original_url=link.original_url,
        title=link.title,
        short_url=f"{s.base_url}/{code}",
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


async def _fetch_title(link_id: uuid.UUID, url: str) -> None:
    from app.database import SessionLocal
    try:
        async with httpx.AsyncClient(timeout=5, follow_redirects=True) as client:
            res = await client.get(url, headers={"User-Agent": "LinkForge/1.0 (+title-fetch)"})

        match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', res.text, re.I) or re.search(r'<title[^>]*>([^<]+)</title>', res.text, re.I)
        title = match.group(1).strip()[:300] if match else None
        if not title:
            return

        async with SessionLocal() as session:
            link = (await session.execute(select(URL).where(URL.id == link_id))).scalars().first()
            if link and not link.title:
                link.title = title
                await session.commit()
    except Exception:
        pass


class LinkService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: LinkCreate, user_id: str, background_tasks: BackgroundTasks) -> URL:
        s = get_settings()
        alias = None
        if data.custom_alias:
            alias = data.custom_alias.lower().strip()
            if (await self.session.execute(select(URL).where(URL.custom_alias == alias, URL.deleted_at.is_(None)))).scalars().first():
                raise ConflictError(f"Alias '{alias}' is already taken.")

        short_code = await _unique_code(self.session, s.short_code_length)
        link = URL(
            user_id=uuid.UUID(user_id),
            original_url=data.original_url,
            short_code=short_code,
            custom_alias=alias,
            expires_at=data.expires_at,
            max_clicks=data.max_clicks,
            password_hash=hash_password(data.password) if data.password else None,
            is_one_time=data.is_one_time,
            ios_url=data.ios_url,
            android_url=data.android_url,
        )
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)

        background_tasks.add_task(_fetch_title, link.id, data.original_url)
        return link

    async def get_user_links(self, user_id: str, skip: int = 0, limit: int = 20) -> list[URL]:
        res = await self.session.execute(
            select(URL)
            .where(URL.user_id == uuid.UUID(user_id), URL.deleted_at.is_(None))
            .order_by(URL.created_at.desc())
            .offset(skip).limit(min(limit, 100))
        )
        return list(res.scalars().all())

    async def get_one_public(self, link_id: str) -> URL:
        try:
            target_uuid = uuid.UUID(link_id)
            stmt = select(URL).where(URL.id == target_uuid, URL.deleted_at.is_(None))
        except ValueError:
            stmt = select(URL).where(
                (URL.short_code == link_id) | (URL.custom_alias == link_id),
                URL.deleted_at.is_(None)
            )
        link = (await self.session.execute(stmt)).scalars().first()
        if not link:
            raise NotFoundError("Link not found.")
        return link

    async def get_one(self, link_id: str, user_id: str) -> URL:
        uid = uuid.UUID(user_id)
        try:
            target_uuid = uuid.UUID(link_id)
            stmt = select(URL).where(URL.id == target_uuid, URL.user_id == uid, URL.deleted_at.is_(None))
        except ValueError:
            stmt = select(URL).where(
                (URL.short_code == link_id) | (URL.custom_alias == link_id),
                URL.user_id == uid,
                URL.deleted_at.is_(None)
            )
        link = (await self.session.execute(stmt)).scalars().first()
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

    async def redirect(self, code: str, password: str | None = None) -> URL:
        link = (await self.session.execute(
            select(URL).where(((URL.short_code == code) | (URL.custom_alias == code)), URL.is_active.is_(True), URL.deleted_at.is_(None))
        )).scalars().first()

        if not link:
            raise NotFoundError(f"'{code}' — link not found or removed.")

        if link.password_hash:
            if not password:
                raise AuthenticationError("Password required. Add ?pw=yourpassword to URL.")
            if not verify_password(password, link.password_hash):
                raise AuthenticationError("Incorrect password.")

        if link.expires_at and link.expires_at < datetime.now(UTC):
            raise LinkExpiredError("This link has expired.")

        if link.max_clicks is not None and link.click_count >= link.max_clicks:
            raise LinkExpiredError(f"Link reached its {link.max_clicks}-click limit.")

        if link.is_one_time:
            link.deleted_at = datetime.now(UTC)
        else:
            link.click_count += 1

        self.session.add(link)
        await self.session.flush()
        return link
