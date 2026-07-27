"""
app/routers/links.py — URL shortener endpoints + redirect.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import RedirectResponse

from app.deps import CurrentUserId, DbSession
from app.schemas import LinkCreate, LinkResponse
from app.services.analytics import record_click
from app.services.links import LinkService, build_response, pick_destination

# /api/v1/links  — CRUD for authenticated users
router = APIRouter(prefix="/links", tags=["Links"])

# /{short_code}  — public redirect (no /api/v1 prefix)
redirect_router = APIRouter(tags=["Redirect"])


@router.post("/", response_model=LinkResponse, status_code=201, summary="Shorten a URL")
async def create_link(
    data: LinkCreate, background_tasks: BackgroundTasks, user_id: CurrentUserId, db: DbSession
) -> LinkResponse:
    link = await LinkService(db).create(data, user_id, background_tasks)
    return build_response(link)


@router.get("/", response_model=list[LinkResponse], summary="List my links")
async def list_links(
    user_id: CurrentUserId, db: DbSession, skip: int = 0, limit: int = 20
) -> list[LinkResponse]:
    links = await LinkService(db).get_user_links(user_id, skip, limit)
    return [build_response(link) for link in links]


@router.get("/{link_id}", response_model=LinkResponse, summary="Get a single link")
async def get_link(link_id: str, user_id: CurrentUserId, db: DbSession) -> LinkResponse:
    link = await LinkService(db).get_one(link_id, user_id)
    return build_response(link)


@router.patch("/{link_id}/toggle", response_model=LinkResponse, summary="Enable / disable a link")
async def toggle_link(link_id: str, user_id: CurrentUserId, db: DbSession) -> LinkResponse:
    link = await LinkService(db).toggle_active(link_id, user_id)
    return build_response(link)


@router.delete("/{link_id}", status_code=204, summary="Delete a link")
async def delete_link(link_id: str, user_id: CurrentUserId, db: DbSession) -> None:
    await LinkService(db).delete(link_id, user_id)


# ---------------------------------------------------------------------------
# Public redirect — this is what makes the short URL actually work
# ---------------------------------------------------------------------------

@redirect_router.get("/{short_code}", include_in_schema=False)
async def redirect_to_url(
    short_code: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: DbSession,
    pw: str | None = None,        # ?pw=secret for password-protected links
) -> RedirectResponse:
    """
    The main product: someone visits /xK93pqR → redirected to the right URL.

    Handles all 3 innovations automatically:
      - Password: add ?pw=yourpassword to the URL
      - One-time: link deactivates after this request
      - Device:   iPhone gets ios_url, Android gets android_url, rest get original_url
    """
    link = await LinkService(db).redirect(short_code, password=pw)
    destination = pick_destination(link, request.headers.get("User-Agent"))
    background_tasks.add_task(record_click, link.id, request)
    return RedirectResponse(url=destination, status_code=302)

