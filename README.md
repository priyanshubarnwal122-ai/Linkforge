# LinkforgeAI — Reliable URL Management & Analytics Platform 🚀

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://linkforge-xw5q.onrender.com)

**LinkforgeAI** is a reliable URL-shortening and link-management platform engineered with **Python 3.12**, **FastAPI**, **PostgreSQL**, **Redis**, and **Docker**. The URL shortener remains the central product: users create, manage, secure, analyze, and redirect short links. Monitoring, deterministic incident detection, evidence-backed investigation, and approval-gated remediation are built around that working core.

> **Product principle:** LinkforgeAI remains useful when an optional AI provider is unavailable. Ordinary link creation, management, redirection, analytics, and deterministic reliability workflows do not depend on an LLM.

📄 **Complete product and capability report:** [PROJECT_REPORT.md](PROJECT_REPORT.md)

🌐 **Live Cloud Production**: [https://linkforge-xw5q.onrender.com](https://linkforge-xw5q.onrender.com)  
📖 **Interactive API Documentation (Swagger)**: [https://linkforge-xw5q.onrender.com/docs](https://linkforge-xw5q.onrender.com/docs)  

---

## 🌟 Key Innovations & Architectural Highlights

### ⚡ 1. Dynamic QR Codes (Zero-Reprint System)
Unlike traditional static QR codes that break when a target destination changes, LinkForge encodes dynamic short endpoints (`/s/{short_code}`). **Updating a link's destination URL in the dashboard automatically updates every printed QR code instantly without reprinting physical posters or billboards!**

### 🛡️ 2. Privacy-First Cookieless Analytics (GDPR Engineering)
Built for 100% GDPR compliance using pure server-side request header attribution. **No tracking cookies. No browser fingerprinting scripts.** Visitor IP addresses are anonymized at ingestion using salted SHA-256 truncation (`anon_...`), preserving privacy while accurately deduplicating unique visitors.

### 🧠 3. Optional smart alias recommendations
The alias recommender can suggest readable aliases based on the destination URL. It is optional and does not block the core shortener when an external AI provider is unavailable.

### 🛠️ 4. Reliability monitoring and incidents

Redirect events include correlation IDs, status codes, latency measurements, and privacy-aware analytics signals. Deterministic rules group recent error events into persisted incidents with severity, component, timestamps, summaries, and evidence.

### 🔎 5. Evidence-backed investigation

The baseline investigator works without an AI key. It reports observed facts, supporting event IDs, measurements, hypotheses, confidence, unknowns, and recommended diagnostic steps instead of inventing root causes.

### ✅ 6. Approval-gated remediation

Safe remediation is restricted to an explicit allowlist such as acknowledging or resolving an incident. Every request, approval, execution, and result is persisted. Arbitrary shell commands and unrestricted production changes are not allowed.

### 🔒 7. Password-Protected Links
Restrict link access behind a sleek, interactive HTML password gate (`?pw=secret`). Unauthorized visitors see a secure lock screen before redirection.

### 💣 8. One-Time Self-Destruct Links
Links automatically burn and permanently deactivate immediately after the first click for secure, sensitive single-use sharing.

### 📱 9. Smart Device Targeting & Routing
A single short link routes **iPhone/iPad** users to the Apple App Store, **Android** users to the Google Play Store, and **Desktop** users to the main website based on dynamic User-Agent detection.

### 📈 10. High-Value Analytics & Chart.js Integration
* **Visual Area Line Graphs**: Daily engagement trend analysis over time (`last_7_days`).
* **Hourly Peak Traffic Heatmap**: 24-hour UTC click intensity bar chart for optimal posting windows.
* **Unique Visitors Metric**: Database-level `COUNT(DISTINCT ip_address)` deduplication.
* **Traffic Referrer Attribution**: Captures and categorizes incoming traffic sources (`LinkedIn`, `Twitter / X`, `WhatsApp`, `Telegram`, `Google Search`, `Direct`).

---

## 🛠️ Complete Tech Stack Architecture

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend Core** | Python 3.12 + FastAPI 0.115 | High-concurrency async web API & Swagger docs |
| **Database & ORM** | PostgreSQL 16 + Async SQLAlchemy 2.0 | Persistent relational storage & async ORM queries |
| **Schema Migrations** | Alembic 1.13 | Zero-downtime database schema version control |
| **Caching & Speed** | Redis 7 (`redis-py` / `aioredis`) | In-memory link caching (2ms response time) & rate limiting |
| **Security & Auth** | JWT, Bcrypt, SHA-256 | Access token rotation, password hashing, IP anonymization |
| **Frontend** | HTML5, Vanilla CSS3, JS (ES6), Chart.js | Stripe/Google styled enterprise dashboard & analytics |
| **DevOps & Deploy** | Docker Compose + Render.com | Multi-container isolation & live cloud hosting |

---

## 📁 Repository Directory Structure

```text
url_shortener/
├── backend/                  # FastAPI Microservice Backend
│   ├── app/
│   │   ├── main.py           # Application entry point & router mounting
│   │   ├── config.py         # Pydantic Settings (.env configuration)
│   │   ├── database.py       # Async SQLAlchemy engine setup
│   │   ├── models/           # SQLAlchemy ORM Models (User, URL, ClickEvent)
│   │   ├── routers/          # API Routers (auth, links, analytics, health)
│   │   ├── schemas.py        # Pydantic validation schemas
│   │   └── services/         # Business logic (Auth, Links, Analytics, Recommender)
│   ├── alembic/              # Database migration revisions
│   ├── Dockerfile            # Multi-stage production Dockerfile
│   └── requirements.txt      # Production Python dependencies
├── frontend/                 # Enterprise Single-Page Dashboard UI (canonical copy)
│   ├── index.html            # Dashboard HTML structure
│   ├── styles.css            # Custom CSS token design system
│   └── app.js                # Async API client & Chart.js graphs
├── docker-compose.yml        # Container orchestration (API, Postgres, Redis)
├── README.md                 # Project README (This file)
├── PROJECT_HANDOVER.md       # Architecture Handover Specification
└── priyanshu.md              # Master Project Report
```

---

## 🔑 OpenAPI / Swagger API Endpoint Reference

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/api/v1/auth/register` | Register new user account | ❌ |
| `POST` | `/api/v1/auth/login` | Authenticate user & return JWT token | ❌ |
| `GET` | `/api/v1/auth/google/login` | Initiate Google OAuth 2.0 redirect | ❌ |
| `GET` | `/api/v1/auth/google/callback` | Google OAuth 2.0 callback handler | ❌ |
| `POST` | `/api/v1/links/` | Create short link with custom options | 🔒 Yes |
| `POST` | `/api/v1/links/recommend-alias` | Get GenAI / NLP alias suggestions | ❌ |
| `GET` | `/api/v1/links/` | Fetch current user's shortened links | 🔒 Yes |
| `GET` | `/api/v1/links/{id}/stats` | Get full click analytics & Chart.js graph data | 🔒 Yes |
| `GET` | `/api/v1/links/{id}/qr` | Stream dynamic PNG QR code image | 🔒 Yes |
| `GET` | `/s/{short_code}` | Public link redirection & password unlock gate | ❌ |
| `GET` | `/api/v1/health/live` | Liveness check | ❌ |
| `GET` | `/api/v1/health/ready` | Database readiness check | ❌ |
| `GET` | `/api/v1/incidents/` | List reliability incidents | 🔒 Yes |
| `POST` | `/api/v1/incidents/detect` | Run deterministic incident detection | 🔒 Yes |
| `POST` | `/api/v1/incidents/{id}/investigate` | Generate evidence-backed investigation | 🔒 Yes |
| `POST` | `/api/v1/incidents/{id}/actions` | Request safe remediation | 🔒 Verified user |
| `POST` | `/api/v1/incidents/{id}/actions/{action_id}/approve` | Approve remediation | 🔒 Verified user |
| `POST` | `/api/v1/incidents/{id}/actions/{action_id}/execute` | Execute approved remediation | 🔒 Verified user |

---

## ⚡ Quick Start Guide (1-Command Setup)

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on your system.

### Launch Application locally
```bash
# 1. Clone the repository
git clone https://github.com/priyanshubarnwal122-ai/Linkforge.git
cd Linkforge

# 2. Create local configuration (the example contains no real credentials)
cp .env.example .env

# 3. Build and launch containers
docker compose up -d --build

# 4. Access LinkForge Dashboard
# Open http://localhost:8000 in your web browser!
```

On Windows, Docker Desktop must be running before Compose can contact the
Linux engine. If Docker reports that `dockerDesktopLinuxEngine` is missing,
start it with `docker desktop start` (or open Docker Desktop), then retry the
Compose command. If old containers from an earlier checkout claim the fixed
LinkForge names, stop the old Compose project first with
`docker compose down`; do not use `down -v` unless deleting local database data
is intended.

The API container waits for healthy PostgreSQL and Redis containers before
starting. Check deployment status with:

```bash
docker compose ps
curl http://localhost:8000/api/v1/health/live
curl http://localhost:8000/api/v1/health/ready
```

`/live` confirms that the process is running; `/ready` returns HTTP 503 until
the database is reachable. For startup or migration problems, inspect
`docker compose logs api` and retry after the database healthcheck passes.
To reset local database and cache data, use `docker compose down -v` (this
deletes the local Docker volumes).

The Compose API service uses the same production startup path as Render: it
waits for PostgreSQL and Redis, runs `alembic upgrade head` (with retries for a
slow database), and then starts one Uvicorn worker. The Docker build context is
the repository root so `frontend/` is copied directly into the image; no
generated frontend copy is required. To exercise the image without Compose:

```bash
docker build --file backend/Dockerfile --tag linkforge:local .
docker run --rm --env-file .env -p 8000:8000 linkforge:local
```

For code-only checks, the repository pins Python 3.12.8 in `.python-version`
and provides one test entry point:

```bash
make test                 # offline unit tests (stdlib unittest)
make lint                 # ruff, when installed in the active environment
make compile              # Python bytecode compilation
make docker-config        # validates Compose using .env.example
```

On systems without GNU Make, the test equivalent is:

```bash
python -m unittest discover -s tests -q
```

`backend/requirements.lock.txt` is the resolved deployment dependency lock;
the Docker image installs that lockfile. Update it deliberately when changing
dependencies.

### Render deployment

Render uses `render.yaml` to provision the API, PostgreSQL, and Redis. Set the
`SECRET_KEY` and any optional integration keys in the Render dashboard; do not
commit a production `.env`. The service healthcheck uses
`/api/v1/health/live`, while database readiness is available at
`/api/v1/health/ready` for troubleshooting.

---

### Windows Docker troubleshooting

If Compose reports:

```text
failed to connect to the dockerDesktopLinuxEngine
```

start Docker Desktop and retry:

```powershell
docker desktop start
docker compose up -d --build
```

If containers from an older checkout claim the fixed Linkforge names, stop the
old Compose project with `docker compose down`. Do not use `docker compose down
-v` unless you intentionally want to delete local PostgreSQL and Redis data.

### Project verification

The repository includes offline tests for URL validation, redirect destination
selection, incident metric calculation, remediation policy, and unsafe-action
rejection:

```bash
python -m unittest discover -s tests -v
python -m compileall -q backend/app backend/alembic tests scripts
python -m ruff check backend/app --select E,F,W,I --ignore E501
docker compose config --quiet
```

The synthetic evaluation command produces calculated detector metrics from
known observations:

```bash
python scripts/evaluate_redirect_reliability.py
```

These synthetic metrics are evaluation results, not a claim about production
traffic performance.

### Capability and limitation report

See [PROJECT_REPORT.md](PROJECT_REPORT.md) for the complete product report,
architecture, API surface, database tables, deployment capabilities, security
controls, test coverage, and current limitations.

---

## 📜 License & Author

Developed by **Priyanshu Barnwal** — Released under the MIT License.
