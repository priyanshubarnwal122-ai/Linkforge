"""
app/services/auth.py — Authentication service.

Innovations:
  1. Brute-force protection  — Redis counter per IP+email, locks after 5 failed attempts
  2. Refresh token rotation  — each /refresh revokes the old token, issues a fresh pair
  3. Login tracking          — login_count + last_login_at updated on every login
  4. Verification via JWT    — no extra DB table; the signed token IS the proof
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis
from app.config import get_settings
from app.exceptions import AuthenticationError, AuthorizationError, ConflictError, NotFoundError
from app.models.user import User
from app.schemas import UserCreate
from app.security import (
    create_access_token,
    create_refresh_token,
    create_verification_token,
    decode_token,
    hash_password,
    verify_password,
)

log = structlog.get_logger(__name__)

_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900  # 15 minutes


# ---------------------------------------------------------------------------
# User DB helpers (direct queries — no abstract base class needed)
# ---------------------------------------------------------------------------

async def _get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).where(User.email == email.lower().strip(), User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def _get_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(
        select(User).where(User.username == username.lower().strip(), User.deleted_at.is_(None))
    )
    return result.scalars().first()


async def _get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await session.execute(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    return result.scalars().first()


# ---------------------------------------------------------------------------
# Auth Service
# ---------------------------------------------------------------------------

class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Brute force helpers ---

    @staticmethod
    def _bf_key(ip: str, email: str) -> str:
        return f"bf:{ip}:{email.lower()}"

    @staticmethod
    def _rt_key(jti: str) -> str:
        return f"rt:{jti}"

    async def _check_lockout(self, ip: str, email: str) -> None:
        r = await get_redis()
        attempts = await r.get(self._bf_key(ip, email))
        if attempts and int(attempts) >= _MAX_ATTEMPTS:
            ttl = await r.ttl(self._bf_key(ip, email))
            mins = ttl // 60 + 1
            raise AuthenticationError(
                f"Too many failed attempts. Try again in {mins} minute{'s' if mins != 1 else ''}."
            )

    async def _record_failure(self, ip: str, email: str) -> None:
        r = await get_redis()
        key = self._bf_key(ip, email)
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, _LOCKOUT_SECONDS)
        await pipe.execute()

    async def _clear_failures(self, ip: str, email: str) -> None:
        r = await get_redis()
        await r.delete(self._bf_key(ip, email))

    # --- Refresh token store ---

    async def _store_refresh_token(self, jti: str, user_id: str) -> None:
        s = get_settings()
        r = await get_redis()
        await r.setex(self._rt_key(jti), s.refresh_token_expire_days * 86400, user_id)

    async def _revoke_refresh_token(self, jti: str) -> None:
        r = await get_redis()
        await r.delete(self._rt_key(jti))

    async def _is_refresh_valid(self, jti: str) -> bool:
        r = await get_redis()
        return await r.exists(self._rt_key(jti)) == 1

    # --- Auth operations ---

    async def register(self, data: UserCreate, background_tasks: BackgroundTasks) -> User:
        if await _get_by_email(self.session, data.email):
            raise ConflictError(f"Email '{data.email}' is already registered.")
        if await _get_by_username(self.session, data.username):
            raise ConflictError(f"Username '{data.username}' is already taken.")

        user = User(
            email=data.email.lower().strip(),
            username=data.username.lower().strip(),
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)

        log.info("user_registered", user_id=str(user.id), email=user.email)
        background_tasks.add_task(_send_verification_email, user)
        return user

    async def login(self, email: str, password: str, ip: str = "unknown") -> dict[str, str]:
        await self._check_lockout(ip, email)

        user = await _get_by_email(self.session, email)

        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            await self._record_failure(ip, email)
            log.warning("login_failed", email=email, ip=ip)
            raise AuthenticationError("Incorrect email or password.")

        if not user.is_active:
            raise AuthorizationError("Your account has been deactivated. Contact support.")

        await self._clear_failures(ip, email)

        # Update login tracking
        user.login_count = (user.login_count or 0) + 1
        user.last_login_at = datetime.now(UTC)
        self.session.add(user)
        await self.session.flush()

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        payload = decode_token(refresh_token, expected_type="refresh")
        await self._store_refresh_token(payload["jti"], str(user.id))

        log.info("login_success", user_id=str(user.id), ip=ip, login_count=user.login_count)
        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    async def refresh(self, refresh_token: str) -> dict[str, str]:
        """Token rotation: revoke old, issue fresh pair. Prevents replay attacks."""
        payload = decode_token(refresh_token, expected_type="refresh")
        jti, user_id = payload.get("jti", ""), payload.get("sub", "")

        if not await self._is_refresh_valid(jti):
            raise AuthenticationError("Session expired. Please log in again.")

        await self._revoke_refresh_token(jti)
        new_access = create_access_token(user_id)
        new_refresh = create_refresh_token(user_id)
        new_payload = decode_token(new_refresh, expected_type="refresh")
        await self._store_refresh_token(new_payload["jti"], user_id)

        log.info("token_rotated", user_id=user_id)
        return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
            await self._revoke_refresh_token(payload.get("jti", ""))
            log.info("logout", user_id=payload.get("sub"))
        except AuthenticationError:
            pass  # Already invalid — fine

    async def verify_email(self, token: str) -> User:
        try:
            payload = decode_token(token, expected_type="verification")
        except AuthenticationError:
            raise AuthenticationError("This verification link is invalid or has expired.")

        user = await _get_by_id(self.session, uuid.UUID(payload["sub"]))
        if not user:
            raise AuthenticationError("User account not found.")

        if not user.is_verified:
            user.is_verified = True
            self.session.add(user)
            await self.session.flush()
            log.info("email_verified", user_id=str(user.id))
        return user

    async def get_user(self, user_id: str) -> User:
        user = await _get_by_id(self.session, uuid.UUID(user_id))
        if not user:
            raise NotFoundError(f"User '{user_id}' not found.")
        return user


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

async def _send_verification_email(user: User) -> None:
    s = get_settings()
    token = create_verification_token(str(user.id), user.email)
    verify_url = f"{s.base_url}/api/v1/auth/verify-email?token={token}"

    if not s.is_production:
        # In dev: copy this URL into your browser to verify the account
        log.info("verification_link", email=user.email, url=verify_url)
    else:
        # TODO: plug in SendGrid / Resend / SES here
        log.warning("email_not_configured", email=user.email)
