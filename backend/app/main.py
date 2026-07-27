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
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles

    frontend_dir = "/frontend" if os.path.exists("/frontend") else os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend")
    if not os.path.exists(frontend_dir):
        frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
    if not os.path.exists(frontend_dir):
        frontend_dir = "frontend"

    @app.get("/", include_in_schema=False)
    async def serve_index():
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "LinkForge API is running"}

    @app.get("/styles.css", include_in_schema=False)
    async def serve_css():
        return FileResponse(os.path.join(frontend_dir, "styles.css"))

    @app.get("/app.js", include_in_schema=False)
    async def serve_js():
        return FileResponse(os.path.join(frontend_dir, "app.js"))

    app.include_router(links.redirect_router)  # /s/{short_code}

    if os.path.exists(frontend_dir):
        app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
        app.mount("/assets", StaticFiles(directory=frontend_dir), name="assets")

    @app.on_event("startup")
    async def startup() -> None:
        log.info("app_ready", name=s.app_name, env=s.environment)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await close_db()
        await close_redis()

    return app


app = create_app()
