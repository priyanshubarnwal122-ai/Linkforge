"""
app/security.py — Password hashing and JWT tokens.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings
from app.exceptions import AuthenticationError


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _make_token(subject: str, token_type: str, expires: timedelta, extra: dict[str, Any] | None = None) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires,
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, s.secret_key, algorithm=s.jwt_algorithm)


def create_access_token(user_id: str, extra: dict[str, Any] | None = None) -> str:
    s = get_settings()
    return _make_token(user_id, "access", timedelta(minutes=s.access_token_expire_minutes), extra)


def create_refresh_token(user_id: str) -> str:
    s = get_settings()
    return _make_token(user_id, "refresh", timedelta(days=s.refresh_token_expire_days))


def create_verification_token(user_id: str, email: str) -> str:
    """Short-lived token for email verification (24h). No DB storage needed."""
    return _make_token(user_id, "verification", timedelta(hours=24), {"email": email})


def decode_token(token: str, expected_type: str = "access") -> dict[str, Any]:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.secret_key, algorithms=[s.jwt_algorithm])
    except JWTError as exc:
        raise AuthenticationError(f"Invalid or expired token: {exc}") from exc

    if payload.get("type") != expected_type:
        raise AuthenticationError(f"Expected token type '{expected_type}', got '{payload.get('type')}'.")
    return payload


def get_user_id_from_token(token: str, token_type: str = "access") -> str:
    payload = decode_token(token, expected_type=token_type)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token is missing subject claim.")
    return user_id
