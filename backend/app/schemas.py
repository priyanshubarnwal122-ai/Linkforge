"""
app/schemas.py — Shared Pydantic schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from ipaddress import ip_address
from typing import Generic, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: list[T]
    pagination: PaginationMeta


class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=20, ge=1, le=100)

    @property
    def skip(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def limit(self) -> int:
        return self.per_page


class TimestampSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    email: str = Field(..., max_length=255)
    username: str = Field(..., min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.lower().strip()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Enter a valid email address.")
        return v


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    username: str
    full_name: str | None
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    login_count: int
    last_login_at: datetime | None
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Link schemas
# ---------------------------------------------------------------------------

class LinkCreate(BaseModel):
    original_url: str = Field(..., max_length=2048)
    custom_alias: str | None = Field(
        default=None, min_length=2, max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Optional vanity alias, e.g. 'my-resume'"
    )

    @field_validator("custom_alias", mode="before")
    @classmethod
    def clean_alias(cls, v: str | None) -> str | None:
        if v:
            v = v.lstrip("/").strip().lower()
            if not v:
                return None
        return v
    expires_at: datetime | None = Field(default=None, description="Optional expiry date")
    max_clicks: int | None = Field(default=None, ge=1, description="Link dies after this many clicks")

    # Innovation 1: Password protection
    password: str | None = Field(default=None, min_length=4, max_length=100, description="Protect link with a password")

    # Innovation 2: One-time / self-destructing link
    is_one_time: bool = Field(default=False, description="Link self-destructs after the first click")

    # Innovation 3: Device-specific redirect
    ios_url: str | None = Field(default=None, max_length=2048, description="Destination for iPhone/iPad users")
    android_url: str | None = Field(default=None, max_length=2048, description="Destination for Android users")

    @field_validator("original_url", "ios_url", "android_url", mode="before")
    @classmethod
    def must_be_http(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        parsed = urlparse(v)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("URL must be a valid http:// or https:// URL")
        if parsed.username or parsed.password:
            raise ValueError("URLs containing embedded credentials are not allowed")
        host = parsed.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith(".localhost"):
            raise ValueError("Private or local destinations are not allowed")
        try:
            address = ip_address(host)
        except ValueError:
            address = None
        if address and (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved):
            raise ValueError("Private or local destinations are not allowed")
        return v


class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    short_code: str
    custom_alias: str | None
    original_url: str
    title: str | None
    short_url: str
    expires_at: datetime | None
    max_clicks: int | None
    click_count: int
    is_active: bool
    created_at: datetime
    # Innovation fields (password hash is NEVER returned — only whether it's set)
    is_password_protected: bool
    is_one_time: bool
    ios_url: str | None
    android_url: str | None


# ---------------------------------------------------------------------------
# Analytics schemas
# ---------------------------------------------------------------------------

class DailyStats(BaseModel):
    date: str   # "2026-07-20"
    clicks: int


class HourlySlot(BaseModel):
    """One slot in the 24-hour engagement heatmap."""
    hour: int   # 0–23 (UTC)
    count: int


class TopItem(BaseModel):
    name: str
    count: int


class LinkStats(BaseModel):
    """Full analytics breakdown for a single link."""
    total_clicks: int
    unique_clicks: int
    today_clicks: int
    last_7_days: list[DailyStats]
    top_browsers: list[TopItem]
    top_devices: list[TopItem]
    top_referrers: list[TopItem]
    hourly_heatmap: list[HourlySlot]  # always 24 items (hour 0–23)


# ---------------------------------------------------------------------------
# Alias Recommender schemas
# ---------------------------------------------------------------------------

class AliasRecommendRequest(BaseModel):
    url: str = Field(..., max_length=2048, description="URL to generate alias recommendations for")


class AliasOption(BaseModel):
    alias: str
    available: bool


class AliasRecommendResponse(BaseModel):
    domain: str
    category: str
    trust_score: int = 95
    recommendations: list[AliasOption]


class IncidentActionRequest(BaseModel):
    action: str = Field(..., min_length=1, max_length=50)

