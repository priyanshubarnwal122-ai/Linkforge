"""
app/routers/links.py — URL shortener endpoints + redirect.
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import RedirectResponse

from app.deps import CurrentUserId, DbSession
from app.exceptions import AuthenticationError
from app.schemas import AliasRecommendRequest, AliasRecommendResponse, LinkCreate, LinkResponse
from app.services.analytics import record_click
from app.services.links import LinkService, build_response, pick_destination

# /api/v1/links  — CRUD for authenticated users
router = APIRouter(prefix="/links", tags=["Links"])

# /{short_code}  — public redirect (no /api/v1 prefix)
redirect_router = APIRouter(tags=["Redirect"])


@router.post("/recommend-alias", response_model=AliasRecommendResponse, summary="Get AI smart custom alias recommendations")
async def recommend_alias(data: AliasRecommendRequest, db: DbSession) -> AliasRecommendResponse:
    from app.services.recommender import AliasRecommenderService
    return await AliasRecommenderService(db).recommend(data.url)


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

@redirect_router.get("/s/{short_code}", include_in_schema=False)
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
    if short_code in {"favicon.ico", "styles.css", "app.js", "index.html", "robots.txt"} or "." in short_code:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not a short link")
    try:
        link = await LinkService(db).redirect(short_code, password=pw)
    except AuthenticationError as err:
        from fastapi.responses import HTMLResponse
        error_msg = f"<p style='color:#ef4444; font-size:0.875rem; margin-top:0.5rem;'>{err.message}</p>" if pw else ""
        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Password Protected Link — LinkForge</title>
  <link rel="stylesheet" href="/styles.css">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
</head>
<body style="display:flex; justify-content:center; align-items:center; min-height:100vh; background:#f8fafc;">
  <div class="card" style="width:100%; max-width:400px; text-align:center;">
    <h2 style="font-size:1.25rem; font-weight:700; margin-bottom:0.5rem;">🔒 Password Protected Link</h2>
    <p style="font-size:0.875rem; color:#64748b; margin-bottom:1.5rem;">This short link requires a password to access.</p>
    <form method="GET" action="">
      <input type="password" name="pw" class="input-text" placeholder="Enter link password" style="width:100%; margin-bottom:0.5rem;" required autofocus />
      {error_msg}
      <button type="submit" class="btn-primary" style="width:100%; justify-content:center; margin-top:1rem;">Unlock & Continue</button>
    </form>
  </div>
</body>
</html>"""
        return HTMLResponse(content=html, status_code=401 if pw else 200)

    destination = pick_destination(link, request.headers.get("User-Agent"))
    background_tasks.add_task(record_click, link.id, request)
    return RedirectResponse(url=destination, status_code=302)

