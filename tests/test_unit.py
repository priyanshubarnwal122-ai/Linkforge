"""tests/test_unit.py — Unit tests (no DB required)."""
from __future__ import annotations

import pytest

from app.config import Settings, get_settings
from app.exceptions import AuthenticationError
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_user_id_from_token,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestSettings:
    def test_singleton(self) -> None:
        assert get_settings() is get_settings()

    def test_database_url_uses_asyncpg(self, monkeypatch: pytest.MonkeyPatch) -> None:
        get_settings.cache_clear()
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
        monkeypatch.setenv("POSTGRES_USER", "usr")
        monkeypatch.setenv("POSTGRES_HOST", "myhost")
        monkeypatch.setenv("POSTGRES_DB", "mydb")
        s = Settings()  # type: ignore[call-arg]
        assert "postgresql+asyncpg" in s.database_url
        assert "myhost" in s.database_url
        get_settings.cache_clear()

    def test_sync_url_uses_psycopg2(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
        s = Settings()  # type: ignore[call-arg]
        assert "postgresql+psycopg2" in s.database_url_sync

    def test_short_secret_key_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pydantic import ValidationError
        monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
        monkeypatch.setenv("SECRET_KEY", "tooshort")
        with pytest.raises(ValidationError):
            Settings()  # type: ignore[call-arg]

    def test_cors_origins_parsed_from_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
        monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000","https://example.com"]')
        s = Settings()  # type: ignore[call-arg]
        assert "http://localhost:3000" in s.cors_origins
        assert "https://example.com" in s.cors_origins

    def test_docs_disabled_in_production(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
        monkeypatch.setenv("ENVIRONMENT", "production")
        s = Settings()  # type: ignore[call-arg]
        assert s.docs_url is None
        assert s.redoc_url is None

    def test_redis_url_includes_password(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
        monkeypatch.setenv("REDIS_PASSWORD", "myredispass")
        s = Settings()  # type: ignore[call-arg]
        assert "myredispass" in s.redis_url

    def test_is_production_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SECRET_KEY", "a" * 32)
        monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
        monkeypatch.setenv("ENVIRONMENT", "production")
        s = Settings()  # type: ignore[call-arg]
        assert s.is_production is True


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswords:
    def test_hash_differs_from_plain(self) -> None:
        assert hash_password("secret") != "secret"

    def test_correct_password_verifies(self) -> None:
        h = hash_password("correct")
        assert verify_password("correct", h) is True

    def test_wrong_password_rejected(self) -> None:
        h = hash_password("correct")
        assert verify_password("wrong", h) is False

    def test_bcrypt_produces_unique_hashes(self) -> None:
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts

    def test_both_hashes_verify(self) -> None:
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert verify_password("same", h1)
        assert verify_password("same", h2)


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

UID = "550e8400-e29b-41d4-a716-446655440000"


class TestTokens:
    def test_access_token_created(self) -> None:
        assert len(create_access_token(UID)) > 50

    def test_access_token_subject(self) -> None:
        assert decode_token(create_access_token(UID))["sub"] == UID

    def test_access_token_type(self) -> None:
        assert decode_token(create_access_token(UID))["type"] == "access"

    def test_refresh_token_type(self) -> None:
        assert decode_token(create_refresh_token(UID), "refresh")["type"] == "refresh"

    def test_access_rejected_as_refresh(self) -> None:
        with pytest.raises(AuthenticationError, match="Expected token type"):
            decode_token(create_access_token(UID), "refresh")

    def test_refresh_rejected_as_access(self) -> None:
        with pytest.raises(AuthenticationError, match="Expected token type"):
            decode_token(create_refresh_token(UID))

    def test_tampered_token_fails(self) -> None:
        token = create_access_token(UID)[:-5] + "XXXXX"
        with pytest.raises(AuthenticationError):
            decode_token(token)

    def test_get_user_id(self) -> None:
        assert get_user_id_from_token(create_access_token(UID)) == UID

    def test_unique_jti_per_token(self) -> None:
        p1 = decode_token(create_access_token(UID))
        p2 = decode_token(create_access_token(UID))
        assert p1["jti"] != p2["jti"]

    def test_extra_claims(self) -> None:
        token = create_access_token(UID, extra={"role": "admin"})
        assert decode_token(token)["role"] == "admin"
