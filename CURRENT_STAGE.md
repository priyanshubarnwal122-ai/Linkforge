# LinkForge — CURRENT_STAGE.md
# This file is updated after EVERY implementation milestone.
# It is the ground truth of where the project stands right now.

---

## 📍 Current Phase
**Phase 1 — Production Foundation** ✅ COMPLETE

---

## ✅ Completed Features

### Core Infrastructure
- [x] Application factory pattern (`create_application()`)
- [x] Pydantic v2 Settings with environment variable parsing
- [x] Auto-disable Swagger UI in production environment
- [x] Single-source-of-truth DB URL construction
- [x] JSON array CORS_ORIGINS env var parsing

### Database
- [x] Async SQLAlchemy 2.0 engine (asyncpg driver)
- [x] Connection pooling with pool_pre_ping (survives DB restarts)
- [x] Session per request via dependency injection
- [x] Automatic commit/rollback in session dependency
- [x] Graceful engine disposal on shutdown
- [x] Base declarative class with shared metadata
- [x] UUIDPrimaryKeyMixin (prevents enumeration attacks)
- [x] TimestampMixin (created_at / updated_at, DB-level defaults)
- [x] SoftDeleteMixin (audit trail, recovery support)

### Repository Pattern
- [x] Generic async BaseRepository[Model, Create, Update]
- [x] get(), get_or_raise(), get_by_field()
- [x] list() with pagination, ordering, soft-delete transparency
- [x] create() using Pydantic schema
- [x] update() with partial updates (exclude_unset=True)
- [x] delete() (hard) and soft_delete()
- [x] count(), exists() utilities

### Security
- [x] bcrypt password hashing (via passlib)
- [x] Constant-time password verification (timing attack safe)
- [x] JWT access tokens (HS256, 30 min, configurable)
- [x] JWT refresh tokens (7 days, configurable)
- [x] Standard JWT claims: sub, exp, iat, jti (for revocation)
- [x] Cross-type token rejection (access vs refresh)
- [x] Token decode with explicit type validation

### HTTP Layer
- [x] Custom exception hierarchy (NotFound, Conflict, Auth, Forbidden, etc.)
- [x] Consistent error response envelope: {error: {code, message, request_id}}
- [x] Global exception handlers (domain, HTTP, validation, unhandled)
- [x] RequestIDMiddleware (generates/propagates X-Request-ID)
- [x] LoggingMiddleware (structured request/response logging)
- [x] CORS middleware (configured from env)
- [x] TrustedHost middleware

### API Endpoints
- [x] `GET /api/v1/health/live` — liveness probe
- [x] `GET /api/v1/health/ready` — readiness probe (checks PostgreSQL)
- [x] `GET /api/v1/health/` — load balancer stub (hidden from docs)

### Observability
- [x] structlog structured JSON logging
- [x] Console logging for development
- [x] Request context binding (request_id, method, path in every log)
- [x] Startup/shutdown lifecycle logging
- [x] Third-party logger quieting (uvicorn.access, sqlalchemy, httpx)

### Infrastructure
- [x] Multi-stage Dockerfile (builder + production stages)
- [x] Non-root user in production container
- [x] Docker HEALTHCHECK
- [x] Docker Compose (postgres 16, redis 7, API, adminer)
- [x] Service health-gate dependencies (API waits for healthy postgres)
- [x] PostgreSQL init script (pgcrypto, pg_trgm, citext extensions)
- [x] Nginx reverse proxy config (load balancing, security headers)

### Alembic
- [x] alembic.ini with UTC timestamps and descriptive filenames
- [x] env.py pulling DB URL from Settings (single source of truth)
- [x] Offline (SQL script) and online migration modes
- [x] compare_type=True, compare_server_default=True

### Testing
- [x] pytest-asyncio configuration (asyncio_mode=auto)
- [x] Session-scoped DB setup/teardown
- [x] Function-scoped transaction rollback isolation
- [x] AsyncClient with dependency override
- [x] Unit tests: Settings (8 tests)
- [x] Unit tests: Security — passwords + JWT (11 tests)
- [x] Integration tests: Health endpoints (8 tests)

### Project Hygiene
- [x] pyproject.toml (dependencies, ruff, mypy, pytest config)
- [x] requirements.txt (runtime) + requirements-dev.txt (dev)
- [x] .env.example with full documentation
- [x] .gitignore (Python, venv, secrets, editors)
- [x] IMPLEMENTATION_PLAN.md (permanent roadmap)

---

## 📁 Files Created

```
linkforge/
├── app/
│   ├── __init__.py
│   ├── main.py                        ← Application factory
│   ├── middleware.py                   ← RequestID + Logging middleware
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                     ← DI: DbSession, CurrentUserId
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── health.py               ← /live, /ready, / endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                   ← Pydantic Settings
│   │   ├── exceptions.py               ← Exception hierarchy + handlers
│   │   ├── logging.py                  ← structlog setup
│   │   └── security.py                 ← bcrypt + JWT utilities
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                     ← Base + Mixins
│   │   ├── session.py                  ← Async engine + session factory
│   │   └── init_db.py                  ← Dev/test table creation
│   ├── models/
│   │   └── __init__.py                 ← Model import point for Alembic
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── base.py                     ← Generic async CRUD repository
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── common.py                   ← APIResponse, PaginatedResponse, etc.
│   ├── services/
│   │   └── __init__.py
│   ├── workers/
│   │   └── __init__.py
│   └── cache/
│       └── __init__.py
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/.gitkeep
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_core_config.py         ← 8 tests
│   │   └── test_security.py            ← 11 tests
│   └── integration/
│       ├── __init__.py
│       └── test_health.py              ← 8 tests
├── scripts/
│   └── db_init.sql
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── .env                                ← gitignored
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── IMPLEMENTATION_PLAN.md
└── CURRENT_STAGE.md
```

---

## 🗄️ Database Status

| Item | Status |
|---|---|
| Engine | Async (asyncpg) ✅ |
| Migrations | Alembic configured, no migrations yet |
| Tables | None (Phase 2 adds User table) |
| Extensions | pgcrypto, pg_trgm, citext (via init script) |
| Connection Pool | 10 connections, 20 overflow |

---

## 🌐 Routes Completed

| Method | Path | Description | Auth |
|---|---|---|---|
| GET | `/api/v1/health/live` | Liveness probe | None |
| GET | `/api/v1/health/ready` | Readiness probe | None |
| GET | `/api/v1/health/` | LB health check | None |

---

## 🐛 Known Issues / Technical Debt

- [ ] `alembic/env.py` uses `asyncio.run()` which may conflict with event loops in some environments — consider using `nest_asyncio` if needed
- [ ] `middleware.py` type annotation fix (Any import at bottom) — minor lint issue, clean up in Phase 2
- [ ] Test database URL is hardcoded in `conftest.py` — should read from env in Phase 2

---

## 📊 Progress

| Phase | Status | Progress |
|---|---|---|
| Phase 1: Foundation | ✅ Complete | 100% |
| Phase 2: Authentication | 🔜 Next | 0% |
| Phase 3: URL Service | ⏳ Pending | 0% |
| Phase 4: Redis Cache | ⏳ Pending | 0% |
| Phase 5: Kafka | ⏳ Pending | 0% |
| Phase 6: Analytics | ⏳ Pending | 0% |
| Phase 7: Workers | ⏳ Pending | 0% |
| Phase 8: Deployment | ⏳ Pending | 0% |
| Phase 9: Monitoring | ⏳ Pending | 0% |
| Phase 10: Microservices | ⏳ Pending | 0% |

**Overall: 10% complete**

---

## 🔄 Current Git Branch
`main` (initial commit)

---

## 📝 Implementation Notes

### Why asyncpg over psycopg2?
asyncpg is 3-10x faster than psycopg2 for async workloads because it implements the PostgreSQL wire protocol natively in Python with no C-extension dependency overhead. The tradeoff is Alembic must use a sync driver (psycopg2) because its migration context is synchronous.

### Why UUID primary keys?
Sequential integer IDs are enumerable — an attacker can iterate /users/1, /users/2, etc. UUIDs are unguessable. They also work correctly across distributed systems and database shards.

### Why lru_cache on get_settings()?
pydantic-settings reads and validates environment variables on every Settings() instantiation. @lru_cache(maxsize=1) ensures this expensive operation happens exactly once per process. In tests, call `get_settings.cache_clear()` to force re-read.

### Why session per request (not global session)?
SQLAlchemy sessions are NOT thread-safe or async-safe for sharing across requests. A global session would cause race conditions, dirty reads, and connection leaks. One session per request, returned to pool after commit/rollback, is the correct pattern.

---

## ➡️ Next Milestone: Phase 2 — Authentication

**What we'll build:**
1. `User` model with Alembic migration
2. Password hashing on registration
3. `POST /api/v1/auth/register` — email + password
4. `POST /api/v1/auth/login` — returns access + refresh tokens
5. `POST /api/v1/auth/refresh` — exchanges refresh for new access token
6. `POST /api/v1/auth/logout` — revokes refresh token
7. `GET /api/v1/auth/google` — initiates OAuth2 flow
8. `GET /api/v1/auth/google/callback` — handles OAuth callback
9. `GET /api/v1/users/me` — returns current user (protected)
10. Email verification background task

**New patterns introduced:**
- UserRepository extending BaseRepository
- AuthService (business logic)
- Protected route dependency (`get_current_user`)
- httpx OAuth2 client calls
