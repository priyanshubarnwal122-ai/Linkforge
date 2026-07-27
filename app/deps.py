"""
app/deps.py — FastAPI dependency injection.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.exceptions import AuthenticationError, AuthorizationError
from app.security import get_user_id_from_token

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

_bearer = HTTPBearer(auto_error=False)
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


async def get_current_user_id(credentials: BearerToken) -> str:
    if credentials is None:
        raise AuthenticationError("Authorization header is required.")
    return get_user_id_from_token(credentials.credentials)


# Shorthand used in route signatures: user_id: CurrentUserId
CurrentUserId = Annotated[str, Depends(get_current_user_id)]


async def get_current_user(user_id: CurrentUserId, db: DbSession):  # type: ignore[return]
    """Returns the full User object — use when you need more than just the ID."""
    from app.services.auth import AuthService
    return await AuthService(db).get_user(user_id)


async def require_verified(user_id: CurrentUserId, db: DbSession):  # type: ignore[return]
    """Like get_current_user but blocks unverified accounts."""
    from app.services.auth import AuthService
    user = await AuthService(db).get_user(user_id)
    if not user.is_verified:
        raise AuthorizationError("Please verify your email address before using this feature.")
    return user
