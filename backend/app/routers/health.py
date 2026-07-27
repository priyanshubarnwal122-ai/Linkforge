"""
app/routers/health.py — Simple health check.
/live  → is the server running?
/ready → is the database reachable?
"""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.database import get_db_session

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", summary="Is the server running?")
async def liveness() -> dict:
    return {"status": "ok"}


@router.get("/ready", summary="Is the database reachable?")
async def readiness() -> dict:
    try:
        async for session in get_db_session():
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "db": "connected"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}
