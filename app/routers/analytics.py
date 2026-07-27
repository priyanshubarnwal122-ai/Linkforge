"""
app/routers/analytics.py — Link stats and QR code generation.
"""
from __future__ import annotations

import io

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.deps import CurrentUserId, DbSession
from app.schemas import LinkStats
from app.services.analytics import get_link_stats
from app.services.links import LinkService, build_response

router = APIRouter(prefix="/links", tags=["Analytics"])


@router.get("/{link_id}/stats", response_model=LinkStats, summary="Get click analytics for a link")
async def link_stats(link_id: str, db: DbSession) -> LinkStats:
    """
    Returns total clicks, today's count, last 7 days breakdown,
    and top browsers / devices.
    """
    link = await LinkService(db).get_one_public(link_id)
    raw = await get_link_stats(db, link.id)

    return LinkStats(
        total_clicks=raw["total_clicks"],
        today_clicks=raw["today_clicks"],
        last_7_days=raw["last_7_days"],
        top_browsers=raw["top_browsers"],
        top_devices=raw["top_devices"],
    )


@router.get("/{link_id}/qr", summary="Download QR code for a link")
async def get_qr_code(link_id: str, db: DbSession) -> StreamingResponse:
    """
    Generates a PNG QR code for the short URL.
    The QR code points to the short link, not the original URL.
    """
    import qrcode  # import here so app starts even if qrcode not installed

    link = await LinkService(db).get_one_public(link_id)
    s = get_settings()
    short_url = build_response(link).short_url  # handles custom_alias fallback

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(short_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="qr_{link.short_code}.png"'},
    )
