"""
app/services/analytics.py — Record click events and compute link statistics.

Everything is intentionally simple:
  - No external library for user-agent parsing (just string matching)
  - No IP geolocation API call (IP stored, country skipped)
  - Stats queries are plain SQLAlchemy — readable top-to-bottom
"""
from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.click import ClickEvent

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# User-Agent parser — no library, just string matching
# ---------------------------------------------------------------------------

def _parse_ua(ua: str | None) -> tuple[str, str]:
    """Returns (browser, device_type) from a raw User-Agent string."""
    if not ua:
        return "Unknown", "Unknown"

    ua_lower = ua.lower()

    # Device
    if "ipad" in ua_lower:
        device = "Tablet"
    elif any(x in ua_lower for x in ["mobile", "android", "iphone"]):
        device = "Mobile"
    else:
        device = "Desktop"

    # Browser (order matters — Edge/Chrome both contain "chrome")
    if "edg/" in ua_lower or "edga/" in ua_lower:
        browser = "Edge"
    elif "opr/" in ua_lower or "opera" in ua_lower:
        browser = "Opera"
    elif "chrome" in ua_lower and "safari" in ua_lower:
        browser = "Chrome"
    elif "firefox" in ua_lower:
        browser = "Firefox"
    elif "safari" in ua_lower:
        browser = "Safari"
    else:
        browser = "Other"

    return browser, device


def _get_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _get_referer(request: Request) -> str | None:
    referer = request.headers.get("Referer") or request.headers.get("Origin")
    if referer and len(referer) > 500:
        return referer[:500]
    return referer


# ---------------------------------------------------------------------------
# Record a click (called as a background task from the redirect router)
# ---------------------------------------------------------------------------

async def record_click(link_id: uuid.UUID, request: Request) -> None:
    from app.database import SessionLocal

    ua_string = request.headers.get("User-Agent")
    browser, device = _parse_ua(ua_string)

    event = ClickEvent(
        link_id=link_id,
        clicked_at=datetime.now(UTC),
        ip_address=_get_ip(request),
        referer=_get_referer(request),
        browser=browser,
        device_type=device,
    )

    try:
        async with SessionLocal() as session:
            session.add(event)
            await session.commit()
        log.info("click_recorded", link_id=str(link_id), browser=browser, device=device)
    except Exception as e:
        log.warning("click_record_failed", link_id=str(link_id), error=str(e))


# ---------------------------------------------------------------------------
# Stats queries
# ---------------------------------------------------------------------------

async def get_link_stats(session: AsyncSession, link_id: uuid.UUID) -> dict:
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.now(UTC) - timedelta(days=7)

    # Total clicks (all time)
    total_result = await session.execute(
        select(func.count()).select_from(ClickEvent).where(ClickEvent.link_id == link_id)
    )
    total_clicks = total_result.scalar_one()

    # Today's clicks
    today_result = await session.execute(
        select(func.count()).select_from(ClickEvent).where(
            ClickEvent.link_id == link_id,
            ClickEvent.clicked_at >= today_start,
        )
    )
    today_clicks = today_result.scalar_one()

    # Last 7 days — grouped by date
    daily_result = await session.execute(
        select(
            func.date(ClickEvent.clicked_at).label("day"),
            func.count().label("clicks"),
        )
        .where(ClickEvent.link_id == link_id, ClickEvent.clicked_at >= week_ago)
        .group_by(func.date(ClickEvent.clicked_at))
        .order_by(func.date(ClickEvent.clicked_at))
    )
    last_7_days = [{"date": str(row.day), "clicks": row.clicks} for row in daily_result]

    # Top browsers
    browser_result = await session.execute(
        select(ClickEvent.browser, func.count().label("count"))
        .where(ClickEvent.link_id == link_id, ClickEvent.browser.isnot(None))
        .group_by(ClickEvent.browser)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_browsers = [{"name": row.browser, "count": row.count} for row in browser_result]

    # Top device types
    device_result = await session.execute(
        select(ClickEvent.device_type, func.count().label("count"))
        .where(ClickEvent.link_id == link_id, ClickEvent.device_type.isnot(None))
        .group_by(ClickEvent.device_type)
        .order_by(func.count().desc())
    )
    top_devices = [{"name": row.device_type, "count": row.count} for row in device_result]

    return {
        "total_clicks": total_clicks,
        "today_clicks": today_clicks,
        "last_7_days": last_7_days,
        "top_browsers": top_browsers,
        "top_devices": top_devices,
    }
