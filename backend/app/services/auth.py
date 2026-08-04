"""
app/services/auth.py — Authentication service (password + Google OAuth + Redis security).
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
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
# Database Helpers
# ---------------------------------------------------------------------------

async def _get_by_email(session: AsyncSession, email: str) -> User | None:
    res = await session.execute(select(User).where(User.email == email.lower().strip(), User.deleted_at.is_(None)))
    return res.scalars().first()


async def _get_by_username(session: AsyncSession, username: str) -> User | None:
    res = await session.execute(select(User).where(User.username == username.lower().strip(), User.deleted_at.is_(None)))
    return res.scalars().first()


async def _get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    res = await session.execute(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    return res.scalars().first()


async def _get_by_google_id(session: AsyncSession, google_id: str) -> User | None:
    res = await session.execute(select(User).where(User.google_id == google_id, User.deleted_at.is_(None)))
    return res.scalars().first()


# ---------------------------------------------------------------------------
# Auth Service
# ---------------------------------------------------------------------------

class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- Redis Security & Session Helpers ---

    @staticmethod
    def _bf_key(ip: str, email: str) -> str:
        return f"bf:{ip}:{email.lower()}"

    @staticmethod
    def _rt_key(jti: str) -> str:
        return f"rt:{jti}"

    async def _check_lockout(self, ip: str, email: str) -> None:
        r = await get_redis()
        if r is None:
            return   # Redis down — skip lockout check
        attempts = await r.get(self._bf_key(ip, email))
        if attempts and int(attempts) >= _MAX_ATTEMPTS:
            ttl = await r.ttl(self._bf_key(ip, email))
            raise AuthenticationError(f"Too many failed attempts. Locked for {ttl // 60 + 1} minutes.")

    async def _record_failure(self, ip: str, email: str) -> None:
        r = await get_redis()
        if r is None:
            return   # Redis down — skip failure recording
        pipe = r.pipeline()
        pipe.incr(self._bf_key(ip, email))
        pipe.expire(self._bf_key(ip, email), _LOCKOUT_SECONDS)
        await pipe.execute()

    async def _issue_tokens(self, user: User) -> dict[str, str]:
        """Issue access + refresh token pair and store refresh JTI in Redis."""
        user.login_count = (user.login_count or 0) + 1
        user.last_login_at = datetime.now(UTC)
        self.session.add(user)
        await self.session.flush()

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        payload = decode_token(refresh_token, expected_type="refresh")

        s = get_settings()
        r = await get_redis()
        if r is not None:
            await r.setex(self._rt_key(payload["jti"]), s.refresh_token_expire_days * 86400, str(user.id))

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

    # --- Authentication Methods ---

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
            raise AuthenticationError("Incorrect email or password.")

        if not user.is_active:
            raise AuthorizationError("Account deactivated.")

        r = await get_redis()
        if r is not None:
            await r.delete(self._bf_key(ip, email))
        log.info("login_success", user_id=str(user.id), ip=ip)
        return await self._issue_tokens(user)

    async def refresh(self, refresh_token: str) -> dict[str, str]:
        payload = decode_token(refresh_token, expected_type="refresh")
        jti, user_id = payload.get("jti", ""), payload.get("sub", "")

        r = await get_redis()
        if r is not None:
            if not await r.exists(self._rt_key(jti)):
                raise AuthenticationError("Session expired. Log in again.")
            await r.delete(self._rt_key(jti))
        user = await _get_by_id(self.session, uuid.UUID(user_id))
        if not user:
            raise NotFoundError("User not found.")

        log.info("token_rotated", user_id=user_id)
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_token(refresh_token, expected_type="refresh")
            r = await get_redis()
            if r is not None:
                await r.delete(self._rt_key(payload.get("jti", "")))
            log.info("logout", user_id=payload.get("sub"))
        except AuthenticationError:
            pass

    async def verify_email(self, token: str) -> User:
        payload = decode_token(token, expected_type="verification")
        user = await _get_by_id(self.session, uuid.UUID(payload["sub"]))
        if not user:
            raise AuthenticationError("User not found.")

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

    # --- Google OAuth ---

    @staticmethod
    def get_google_auth_url() -> str:
        s = get_settings()
        if not s.google_client_id or "your_google_client_id" in s.google_client_id or s.google_client_id == "dummy_google_client_id":
            return "/?oauth_notice=1"
        params = {
            "client_id": s.google_client_id,
            "redirect_uri": s.effective_google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    async def google_login_callback(self, code: str) -> dict[str, str]:
        s = get_settings()
        if not s.google_client_id or not s.google_client_secret:
            raise ConflictError("Google OAuth credentials missing in .env.")

        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": s.google_client_id,
                    "client_secret": s.google_client_secret,
                    "redirect_uri": s.effective_google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if res.status_code != 200:
                raise AuthenticationError("Failed to authenticate with Google.")

            token = res.json().get("access_token")
            user_res = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )
            if user_res.status_code != 200:
                raise AuthenticationError("Failed to fetch Google user profile.")

            info = user_res.json()

        google_id, email = info.get("id"), info.get("email", "").lower().strip()
        if not google_id or not email:
            raise AuthenticationError("Invalid Google profile data.")

        user = await _get_by_google_id(self.session, google_id) or await _get_by_email(self.session, email)

        if user:
            user.google_id = google_id
            if info.get("picture") and not user.avatar_url:
                user.avatar_url = info.get("picture")
        else:
            base_username = email.split("@")[0]
            username = base_username
            counter = 1
            while await _get_by_username(self.session, username):
                username = f"{base_username}{counter}"
                counter += 1

            user = User(
                email=email,
                username=username,
                full_name=info.get("name"),
                google_id=google_id,
                avatar_url=info.get("picture"),
                is_verified=True,
            )
            self.session.add(user)

        return await self._issue_tokens(user)


# ---------------------------------------------------------------------------
# Background Task
# ---------------------------------------------------------------------------

async def _send_verification_email(user: User) -> None:
    s = get_settings()
    token = create_verification_token(str(user.id), user.email)
    verify_url = f"{s.base_url}/api/v1/auth/verify-email?token={token}"
    if not s.is_production:
        log.info("verification_link", email=user.email, url=verify_url)
