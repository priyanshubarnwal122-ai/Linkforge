# LinkForge — Comprehensive File-by-File Technical & Plain Guide

This document explains **every single file** in the `LinkForge` repository. Each file includes:
1. **Simple Explanation**: High-level plain English description.
2. **Technical Explanation**: Deep architectural breakdown, design choices, data types, and algorithms.
3. **Role in System**: How the file interacts with the rest of LinkForge.

---

## Table of Contents
1. [Root & Configuration Files](#1-root--configuration-files)
2. [Database & Migration Files (Alembic)](#2-database--migration-files-alembic)
3. [Core Application Package (`app/`)](#3-core-application-package-app)
4. [Data Models (`app/models/`)](#4-data-models-appmodels)
5. [Business Logic Services (`app/services/`)](#5-business-logic-services-appservices)
6. [API Routers (`app/routers/`)](#6-api-routers-approuters)

---

## 1. Root & Configuration Files

### `pyproject.toml`
- **Simple Explanation**: The main project configuration file for Python. It lists project details (name, version, author), what libraries Python needs to run the project, and settings for testing and linting tools.
- **Technical Explanation**: Uses standard PEP 518/621 packaging specifications. Defines runtime dependencies (`fastapi`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic-settings`, `redis`, `bcrypt`, `python-jose`, `httpx`, `qrcode`, `Pillow`) and development dependencies (`pytest`, `pytest-asyncio`, `ruff`). Configures tooling settings like `[tool.ruff]` (linter line length and rule selections) and `[tool.pytest.ini_options]` (asyncio mode auto-discovery).
- **Role in System**: Single source of truth for dependencies and code quality configurations across local environments and Docker builds.

### `requirements.txt`
- **Simple Explanation**: A simple list of required Python libraries created from `pyproject.toml`.
- **Technical Explanation**: Flat dependency manifest optimized for `pip install -r requirements.txt`. Includes strict version constraints to ensure deterministic builds.
- **Role in System**: Used inside the `Dockerfile` to cache dependency installation steps before copying project source code, speeding up container builds.

### `.env` & `.env.example`
- **Simple Explanation**: `.env` stores secret credentials (passwords, secret keys, hostnames) on your computer. `.env.example` is a safe template copy showing what environment variables are needed without revealing real secrets.
- **Technical Explanation**: Environment configuration file loaded by `pydantic-settings`. Configures database connection strings, JWT secret key length, token TTLs, Redis host/port, and environment type (`development`, `staging`, `production`).
- **Role in System**: Provides dynamic configuration parameters at runtime without hardcoding sensitive data into source code.

### `docker-compose.yml`
- **Simple Explanation**: A setup file that launches the entire backend infrastructure (PostgreSQL database, Redis cache, FastAPI application server, and Adminer database viewer) with a single command.
- **Technical Explanation**: Docker Compose v3.9 manifest defining 4 networked services:
  1. `postgres`: PostgreSQL 16 Alpine container with persistent volume and `pg_isready` healthcheck.
  2. `redis`: Redis 7 Alpine container configured with LRU memory eviction policy (`allkeys-lru`, 256MB maxmemory) and healthcheck.
  3. `api`: The FastAPI web server built from `Dockerfile`, mounted with auto-reload for local development.
  4. `adminer`: Lightweight Web GUI for PostgreSQL management listening on port 8080.
- **Role in System**: Orchestrates distributed local container services over a shared Docker bridge network (`linkforge_net`).

### `Dockerfile`
- **Simple Explanation**: A recipe that package-wraps the Python app so it runs identically on any computer or server.
- **Technical Explanation**: Multi-stage container build definition:
  - `builder` stage: Compiles binary C-extensions and installs virtual environment dependencies (`libpq-dev`, `build-essential`).
  - `production` stage: Copies only the pre-compiled virtual environment onto a minimal `python:3.12-slim` base image, sets up a non-root system user (`linkforge`), and defines a container healthcheck against `/api/v1/health/live`.
- **Role in System**: Produces lightweight, secure, production-ready container images.

### `.gitignore`
- **Simple Explanation**: A file telling Git which local files (like secret `.env` files, virtual environments, database dumps, compiled cache files) to ignore so they aren't uploaded to public repositories.
- **Technical Explanation**: Pattern-matching list filtering out `__pycache__/`, `.venv/`, `.env`, `.pytest_cache/`, `.coverage`, and OS temporary files (`.DS_Store`, `Thumbs.db`).
- **Role in System**: Prevents repository bloat and accidental credential leakage.

### `CURRENT_STAGE.md`
- **Simple Explanation**: A status tracker recording all implemented features, database architecture decisions, and current progress.
- **Technical Explanation**: Project roadmap and architecture summary mapping completed milestones (Auth, Link Shortening, Analytics) and planned phases (Redis caching, CI/CD).
- **Role in System**: Documentation baseline for developer onboarding and project status verification.

---

## 2. Database & Migration Files (Alembic)

### `alembic.ini`
- **Simple Explanation**: Configures Alembic, the database migration tool that updates your database structure as your Python models change.
- **Technical Explanation**: Core configuration file for Alembic specifying script location (`alembic/`), template formats, loggers, and default connection settings (overridden dynamically by `alembic/env.py`).
- **Role in System**: Enables database schema migrations across database environments.

### `alembic/env.py`
- **Simple Explanation**: A Python script that connects Alembic to the SQLAlchemy database models so it can automatically detect table additions or column changes.
- **Technical Explanation**: Alembic environment runner script. Imports `Base` from `app.database` and all model schemas (`app.models.user`, `app.models.url`, `app.models.click`). Dynamically reads PostgreSQL database settings from `app.config.get_settings()` and supports both offline script generation and online async migration execution.
- **Role in System**: Bridges application SQLAlchemy models with actual PostgreSQL database tables.

### `alembic/script.py.mako`
- **Simple Explanation**: A template file used by Alembic to format newly generated database migration script files.
- **Technical Explanation**: Mako template producing standardized migration files containing `upgrade()` and `downgrade()` functions.
- **Role in System**: Formats generated migration revision scripts.

---

## 3. Core Application Package (`app/`)

### `app/__init__.py`
- **Simple Explanation**: Marks the `app` folder as a Python module package.
- **Technical Explanation**: Empty package initialization file allowing absolute imports like `from app.config import get_settings`.
- **Role in System**: Enables Python package namespace resolution.

### `app/config.py`
- **Simple Explanation**: Loads and validates all project settings from `.env` or system environment variables.
- **Technical Explanation**: Uses Pydantic `BaseSettings` with automatic validation (`secret_key` minimum length check, log level patterns, CORS JSON parsing). Provides cached settings access via `@lru_cache` and sets up `structlog` logging format (JSON in production, colored console in development).
- **Role in System**: Centralized configuration management and structured logging initialization across the entire application.

### `app/database.py`
- **Simple Explanation**: Sets up the connection to the PostgreSQL database and handles request database sessions.
- **Technical Explanation**:
  - Initializes `create_async_engine` with `asyncpg` driver, connection pooling (`pool_size=5`, `pool_pre_ping=True`), and recycled stale connections.
  - Defines `Base` (SQLAlchemy `DeclarativeBase`) and reusable database mixins:
    - `UUIDMixin`: Generates UUID v4 primary keys (`uuid.uuid4()`).
    - `TimestampMixin`: Automatically sets `created_at` and `updated_at` timestamps using database-level `func.now()`.
  - Provides `get_db_session()` FastAPI generator dependency that yields an `AsyncSession`, auto-commits on success, and rolls back on unhandled exceptions.
- **Role in System**: Data access layer foundation managing database connection pooling and lifecycle.

### `app/cache.py`
- **Simple Explanation**: Connects the FastAPI application to Redis for fast in-memory operations.
- **Technical Explanation**: Implements an asynchronous Redis client instance using `redis.asyncio.from_url`. Provides singleton connection acquisition (`get_redis()`) and clean disconnection (`close_redis()`).
- **Role in System**: Provides in-memory storage used for brute-force rate limiting and refresh token session storage.

### `app/security.py`
- **Simple Explanation**: Handles password hashing, password checking, and creating/verifying JWT security tokens.
- **Technical Explanation**:
  - `hash_password()` & `verify_password()`: Direct `bcrypt` password hashing with auto-generated salts.
  - `create_access_token()`, `create_refresh_token()`, `create_verification_token()`: Utility functions generating signed `python-jose` JWT tokens with claims (`sub`, `type`, `exp`, `iat`, unique `jti` UUID).
  - `decode_token()`: Verifies signature, expiration time, and expected token type claim (`access`, `refresh`, or `verification`).
- **Role in System**: Core security layer enforcing identity verification and cryptographic token generation.

### `app/deps.py`
- **Simple Explanation**: Common helper functions (dependencies) that endpoints use to get database sessions or check if a user is logged in.
- **Technical Explanation**: FastAPI dependency injection utilities:
  - `DbSession`: Type alias for `Annotated[AsyncSession, Depends(get_db_session)]`.
  - `CurrentUserId`: Extracts HTTP Bearer token from headers (`HTTPBearer`), decodes access JWT, and returns user ID string.
  - `get_current_user`: Fetches full database `User` object from database session.
  - `require_verified`: Blocks unverified users by raising `AuthorizationError` if `is_verified` is `False`.
- **Role in System**: Reusable controller dependencies for route protection and data access.

### `app/exceptions.py`
- **Simple Explanation**: Custom error definitions that ensure every error returned by the server has a clean, consistent JSON structure.
- **Technical Explanation**: Defines base class `LinkForgeError` and domain exception subclasses (`NotFoundError`, `ConflictError`, `AuthenticationError`, `AuthorizationError`, `LinkExpiredError`, `RateLimitError`). Registers global exception handlers with FastAPI to intercept domain errors, HTTP exceptions, and Pydantic validation errors, standardizing response bodies to `{"error": {"code": ..., "message": ...}}`.
- **Role in System**: Unified API error handling and HTTP status code mapping.

### `app/schemas.py`
- **Simple Explanation**: Contains Pydantic models that define and validate incoming HTTP request payloads and outgoing JSON responses.
- **Technical Explanation**: Defines strict Pydantic v2 schemas:
  - **Auth Schemas**: `UserCreate` (email formatting, username pattern `^[a-zA-Z0-9_]+$`, password length validation), `UserLogin`, `UserResponse`, `TokenPair`, `RefreshRequest`.
  - **Link Schemas**: `LinkCreate` (URL protocol validation `http://` / `https://`, vanity alias pattern, password protection, one-time flag, device URLs `ios_url`, `android_url`), `LinkResponse`.
  - **Analytics Schemas**: `LinkStats`, `DailyStats`, `TopItem`.
- **Role in System**: Input validation layer and API response serializer.

### `app/main.py`
- **Simple Explanation**: The main entry point that constructs the FastAPI app, attaches CORS policy, registers all API routers, and defines startup/shutdown hooks.
- **Technical Explanation**: Application factory (`create_app()`). Configures FastAPI metadata, registers `CORSMiddleware`, attaches exception handlers from `app.exceptions`, includes routers (`health`, `auth`, `links`, `analytics`), and sets up `@app.on_event("startup")` and `"shutdown"` lifecycle hooks to close database and Redis pools cleanly.
- **Role in System**: Web service orchestrator binding HTTP routes, middleware, and lifecycle events together.

### `app/repository.py`
- **Simple Explanation**: A retired placeholder file kept for historical context.
- **Technical Explanation**: Formerly contained a generic `BaseRepository[ModelType, CreateSchema, UpdateSchema]` abstraction. Replaced by direct, readable async SQLAlchemy queries inside service classes to reduce unnecessary technical complexity.
- **Role in System**: Deprecated file; direct queries are now handled in service layers.

---

## 4. Data Models (`app/models/`)

### `app/models/__init__.py`
- **Simple Explanation**: Imports all database models in one place so Alembic and SQLAlchemy recognize them.
- **Technical Explanation**: Package export file importing `User`, `URL`, and `ClickEvent`.
- **Role in System**: Makes models discoverable for Alembic migration generation.

### `app/models/user.py`
- **Simple Explanation**: The database structure for registered user accounts.
- **Technical Explanation**: SQLAlchemy ORM model `User` mapped to table `users`. Inherits `UUIDMixin` and `TimestampMixin`. Fields:
  - `email` (indexed, unique, non-null str)
  - `username` (indexed, unique, non-null str)
  - `hashed_password` (nullable for OAuth accounts)
  - `is_active` & `is_verified` (booleans with server defaults)
  - `login_count` & `last_login_at` (login activity tracking)
  - `deleted_at` (soft deletion timestamp)
- **Role in System**: Represents user account state and credentials in PostgreSQL.

### `app/models/url.py`
- **Simple Explanation**: The database structure for shortened links.
- **Technical Explanation**: SQLAlchemy ORM model `URL` mapped to table `links`. Linked to `users.id` via foreign key with CASCADE deletion. Fields:
  - `original_url` (Text, non-null)
  - `short_code` (String(20), indexed, unique)
  - `custom_alias` (String(50), indexed, unique, optional)
  - `title` (auto-fetched webpage `og:title`)
  - Expiry controls: `expires_at` (timestamp), `max_clicks` (integer cap), `click_count` (current redirect count)
  - Innovations: `password_hash` (bcrypt hash for link protection), `is_one_time` (self-destruct flag), `ios_url` & `android_url` (device-specific target URLs)
  - `is_active` & `deleted_at`
- **Role in System**: Stores URL shortening rules, security constraints, and device routing targets.

### `app/models/click.py`
- **Simple Explanation**: The database structure for recording link redirects and visitor analytics.
- **Technical Explanation**: SQLAlchemy ORM model `ClickEvent` mapped to table `click_events`. Linked to `links.id` via foreign key with CASCADE deletion. Fields:
  - `clicked_at` (timestamp, indexed)
  - `ip_address` (String(45), supports IPv6)
  - `referer` (String(500), referring domain)
  - `browser` & `device_type` (parsed from visitor's User-Agent string)
- **Role in System**: Provides immutable event log for link usage statistics.

---

## 5. Business Logic Services (`app/services/`)

### `app/services/__init__.py`
- **Simple Explanation**: Package marker for services.
- **Technical Explanation**: Empty package initialization file.
- **Role in System**: Enables namespace imports under `app.services`.

### `app/services/auth.py`
- **Simple Explanation**: Contains business logic for user registration, password login, Google OAuth 2.0 login, account lockout protection, refresh token rotation, and email verification.
- **Technical Explanation**: Service class `AuthService`:
  - `register()`: Checks duplicate email/username, hashes password, inserts `User`, schedules background email verification.
  - `login()`: Enforces Redis brute-force lockout (`bf:{ip}:{email}` key, max 5 attempts within 15 mins), validates bcrypt hash, updates `login_count` and `last_login_at`, generates access/refresh tokens, and stores refresh `jti` in Redis.
  - `get_google_auth_url()`: Builds Google OAuth 2.0 authorization URL with `openid email profile` scopes.
  - `google_login_callback()`: Exchanges Google authorization code for ID/access tokens via `httpx`, fetches user profile, finds or auto-creates user, sets `is_verified=True`, and issues standard app JWT tokens.
  - `refresh()`: Validates refresh token `jti` in Redis, revokes the old token, issues a fresh token pair (Token Rotation).
  - `logout()`: Removes refresh token `jti` from Redis.
  - `verify_email()`: Decodes short-lived verification JWT and sets `user.is_verified = True`.
- **Role in System**: Handles identity, authentication security, Google OAuth integration, and session storage.

### `app/services/links.py`
- **Simple Explanation**: Contains core URL shortener logic: creating links, pick device targets, handle passwords, self-destruct links, and fetch page titles.
- **Technical Explanation**: Service class `LinkService`:
  - `_unique_code()`: Generates random Base62 codes (`A-Za-z0-9`) with collision retry logic.
  - `create()`: Checks custom alias availability, hashes optional link passwords, saves device targets (`ios_url`, `android_url`), and schedules background title fetching.
  - `_fetch_title()`: Asynchronous HTTP request using `httpx` parsing `og:title` or `<title>` HTML meta tags in background.
  - `redirect()`: Performs single-query lookup by `short_code OR custom_alias`. Checks password against `password_hash`, validates date expiry (`expires_at`) and click-budget expiry (`max_clicks`), handles one-time links (`is_one_time` sets `deleted_at`), and increments `click_count`.
  - `pick_destination()`: Parses User-Agent header to choose `ios_url`, `android_url`, or fallback `original_url`.
- **Role in System**: Executes core URL redirection features and security rules.

### `app/services/analytics.py`
- **Simple Explanation**: Collects visitor data on every redirect without slowing down the user, and calculates analytics reports.
- **Technical Explanation**:
  - `_parse_ua()`: Lightweight string parser identifying browser (Chrome, Firefox, Safari, Edge, Opera) and device category (Mobile, Tablet, Desktop) from User-Agent strings.
  - `record_click()`: Non-blocking background task inserting a `ClickEvent` record.
  - `get_link_stats()`: Executes 5 aggregated SQL queries computing total clicks, today's clicks, last 7 days daily click breakdown, top 5 browsers, and top device types.
- **Role in System**: Manages link analytics generation and background click processing.

---

## 6. API Routers (`app/routers/`)

### `app/routers/__init__.py`
- **Simple Explanation**: Package marker for routers.
- **Technical Explanation**: Empty package initialization file.
- **Role in System**: Enables namespace imports under `app.routers`.

### `app/routers/auth.py`
- **Simple Explanation**: API endpoints for user authentication (`/api/v1/auth/*`) including email/password login and Google OAuth 2.0.
- **Technical Explanation**: Controller layer routing HTTP requests to `AuthService`:
  - `POST /register`: Registers user account (201 Created).
  - `POST /login`: Authenticates credentials, passes client IP for brute-force tracking, returns `TokenPair`.
  - `GET /google/login`: Redirects browser to Google OAuth consent screen.
  - `GET /google/callback`: Receives Google authorization code, exchanges it for profile data, logs in or auto-registers user, returns `TokenPair`.
  - `POST /refresh`: Rotates refresh token pair.
  - `POST /logout`: Revokes refresh token (204 No Content).
  - `GET /verify-email`: Verifies account via token query parameter.
  - `GET /me`: Returns logged-in user profile (`CurrentUserId` protected).
- **Role in System**: Exposes authentication endpoints to frontend/API clients.

### `app/routers/health.py`
- **Simple Explanation**: Health endpoints used by monitoring systems to check if the server and database are running.
- **Technical Explanation**:
  - `GET /health/live`: Returns `{"status": "ok"}` for container liveness probes.
  - `GET /health/ready`: Executes `SELECT 1` against database to confirm connectivity.
- **Role in System**: Provides deployment readiness checks for Docker and load balancers.

### `app/routers/links.py`
- **Simple Explanation**: API endpoints for managing links (`/api/v1/links/*`) and the public short link redirect (`/{short_code}`).
- **Technical Explanation**:
  - `router` (`/api/v1/links`): Authenticated CRUD routes (`POST /` to create link, `GET /` to list links, `GET /{id}` for single link, `PATCH /{id}/toggle` to enable/disable, `DELETE /{id}` for soft delete).
  - `redirect_router` (`/{short_code}`): Unauthenticated public redirect. Accepts optional `?pw=` query parameter for password links. Calls `LinkService.redirect()`, picks device destination via `pick_destination()`, schedules background `record_click()`, and returns HTTP 302 Found redirect response.
- **Role in System**: Primary interface for link creation and public link redirection execution.

### `app/routers/analytics.py`
- **Simple Explanation**: Endpoints for viewing link statistics and downloading link QR codes.
- **Technical Explanation**:
  - `GET /api/v1/links/{id}/stats`: Validates link ownership and returns structured `LinkStats` JSON payload.
  - `GET /api/v1/links/{id}/qr`: Generates a PNG QR code image using `qrcode` library pointing to the short URL, returning an HTTP `StreamingResponse` image attachment.
- **Role in System**: Exposes analytical insights and downloadable assets for user links.


