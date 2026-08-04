"""
app/main.py — FastAPI app setup.
"""
from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cache import close_redis
from app.config import get_settings, setup_logging
from app.database import close_db
from app.exceptions import register_exception_handlers
from app.routers import analytics, auth, health, links

log = structlog.get_logger(__name__)

def create_app() -> FastAPI:
    s = get_settings()
    setup_logging(s.log_level, s.log_format)

    API_PREFIX = "/api/v1"

    app = FastAPI(
        title=s.app_name,
        version=s.app_version,
        description="LinkForge — A smart URL shortener.",
        docs_url=s.docs_url,
        redoc_url=s.redoc_url,
        openapi_url=f"{API_PREFIX}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(auth.router, prefix=API_PREFIX)
    app.include_router(analytics.router, prefix=API_PREFIX)
    app.include_router(links.router, prefix=API_PREFIX)

    import os
    from pathlib import Path
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    current_dir = Path(__file__).resolve().parent
    candidate_paths = [
        current_dir.parent.parent / "frontend",
        current_dir.parent / "frontend",
        Path("/frontend"),
        Path("frontend"),
    ]

    frontend_dir = None
    for candidate in candidate_paths:
        if candidate.exists() and (candidate / "index.html").exists():
            frontend_dir = candidate
            break

    @app.get("/", include_in_schema=False)
    async def serve_index():
        if frontend_dir and (frontend_dir / "index.html").exists():
            return FileResponse(frontend_dir / "index.html")
        return {"message": "LinkForge API is running"}

    @app.get("/styles.css", include_in_schema=False)
    async def serve_css():
        if frontend_dir and (frontend_dir / "styles.css").exists():
            return FileResponse(frontend_dir / "styles.css")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="styles.css not found")

    @app.get("/app.js", include_in_schema=False)
    async def serve_js():
        if frontend_dir and (frontend_dir / "app.js").exists():
            return FileResponse(frontend_dir / "app.js")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="app.js not found")

    app.include_router(links.redirect_router)  # /s/{short_code}

    if frontend_dir and frontend_dir.exists():
        app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
        app.mount("/assets", StaticFiles(directory=str(frontend_dir)), name="assets")

    @app.on_event("startup")
    async def startup() -> None:
        log.info("app_ready", name=s.app_name, env=s.environment)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await close_db()
        await close_redis()

    return app


app = create_app()