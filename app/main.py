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
    app.include_router(links.router, prefix=API_PREFIX)
    app.include_router(analytics.router, prefix=API_PREFIX)
    app.include_router(links.redirect_router)  # no prefix — /{short_code} at root

    @app.on_event("startup")
    async def startup() -> None:
        log.info("app_ready", name=s.app_name, env=s.environment)

    @app.on_event("shutdown")
    async def shutdown() -> None:
        await close_db()
        await close_redis()

    return app


app = create_app()
