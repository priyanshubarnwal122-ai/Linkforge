# LinkForge — Project Handover & Complete Architecture Document 🚀

> **Note for AI Assistant / Claude**: This document provides a complete technical handover of the **LinkForge** project, detailing the stack, directory structure, database models, features built, API endpoints, and deployment status.

---

## 📌 1. Project Overview

**LinkForge** is a modern, high-performance, enterprise-grade URL Management & Analytics Platform built to compete with Bitly and Dub.co. 

* **Live Cloud Deployment**: [https://linkforge-xw5q.onrender.com](https://linkforge-xw5q.onrender.com)
* **GitHub Repository**: [https://github.com/priyanshubarnwal122-ai/Linkforge](https://github.com/priyanshubarnwal122-ai/Linkforge)
* **API Documentation (Swagger)**: [https://linkforge-xw5q.onrender.com/docs](https://linkforge-xw5q.onrender.com/docs)

---

## 🛠️ 2. Full Tech Stack

| Layer | Technology Used |
| :--- | :--- |
| **Backend Language** | Python 3.12 |
| **Web API Framework** | FastAPI 0.115 + Uvicorn (ASGI) |
| **Database & ORM** | PostgreSQL 16 + Async SQLAlchemy 2.0 (`asyncpg`) |
| **Database Migrations** | Alembic 1.13 |
| **Caching & Rate Limiting** | Redis 7 (`redis-py` / `aioredis`) |
| **Security & Auth** | JWT (python-jose), Bcrypt (`passlib`), Google OAuth 2.0 (`httpx`) |
| **Frontend** | HTML5, Vanilla CSS3 (Google/Stripe Enterprise System), Vanilla JS (ES6), Chart.js |
| **Containerization** | Docker (Multi-stage build) & Docker Compose |
| **Cloud Hosting** | Render.com |

---

## 📁 3. Directory Architecture

```text
url_shortener/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point, static asset mounting, router includes
│   │   ├── config.py             # Pydantic Settings (.env configuration & DB URLs)
│   │   ├── database.py           # Async SQLAlchemy engine & sessionmaker setup
│   │   ├── deps.py               # FastAPI dependencies (auth token extraction, DB sessions)
│   │   ├── exceptions.py         # Custom HTTP exception handlers (400, 401, 404, 409)
│   │   ├── models/               # SQLAlchemy ORM Database Models
│   │   │   ├── __init__.py
│   │   │   ├── user.py           # User model (id, email, password_hash, is_verified)
│   │   │   ├── url.py            # URL model (short_code, custom_alias, original_url, ios_url, android_url, password_hash, is_one_time)
│   │   │   └── click.py          # ClickEvent model (link_id, clicked_at, ip_address, referer, browser, device_type)
│   │   ├── routers/              # FastAPI APIRouter Endpoints
│   │   │   ├── auth.py           # /auth/register, /auth/login, /auth/google/login, /auth/google/callback
│   │   │   ├── links.py          # /links/ (CRUD), /links/recommend-alias, /s/{short_code} (Redirect Engine)
│   │   │   └── analytics.py      # /links/{id}/stats, /links/{id}/qr
│   │   ├── schemas.py            # Pydantic Request & Response Schemas
│   │   ├── security.py           # Bcrypt password hashing & JWT token encoding/decoding
│   │   └── services/             # Core Business Logic Services
│   │       ├── auth.py           # AuthService & Google OAuth integration
│   │       ├── links.py          # LinkService, Base62 _unique_code generator, pick_destination()
│   │       ├── analytics.py      # record_click(), get_link_stats(), _clean_referer()
│   │       └── recommender.py    # AliasRecommenderService (keyword extraction, candidate generation, DB availability check)
│   ├── alembic/                  # Alembic DB Migration Revisions
│   │   ├── env.py                # Alembic script environment setup
│   │   └── versions/             # Migration snapshots (20260727_..._create_tables.py)
│   ├── alembic.ini               # Alembic Configuration
│   ├── Dockerfile                # Multi-stage Docker build file
│   └── requirements.txt          # Python dependencies
├── frontend/                     # Web Dashboard UI Assets
│   ├── index.html                # Semantic HTML5 Dashboard Structure & Modals
│   ├── styles.css                # Google Enterprise CSS Token System
│   └── app.js                    # Async API Client, Chart.js Integration & Debounced AI Listeners
├── docker-compose.yml            # Multi-container orchestration (API, Postgres, Redis, Adminer)
├── .env                          # Local Environment Configuration
├── .env.example                  # Environment Template
├── README.md                     # GitHub Repository README
└── PROJECT_HANDOVER.md           # Handover & Architecture Reference (This file)
```

---

## ✨ 4. Complete Feature Specifications Built

### 1. Base62 URL Shortening Algorithm
* Generates cryptographically secure 7-character short codes using `secrets.choice(string.ascii_letters + string.digits)` (62 alphanumeric characters).

### 2. AI Smart Alias Recommender & Domain Category Analyzer
* Debounced 400ms input listener on frontend URL box.
* Parses domain and path keywords (stripping web noise like `www`, `html`, `watch`).
* Generates 3–4 brandable vanity alias candidates (e.g. `/facebook-react`, `/github-direct`).
* Executes real-time async PostgreSQL queries (`SELECT 1 FROM urls WHERE custom_alias = ?`) to verify 100% availability.
* Displays category badge (`🛡️ Developer Tools & Code`).

### 3. Password-Protected Links (`🔒 Password`)
* Protects links with secret passwords (`password_hash`).
* Visitors accessing a protected link without `?pw=` parameter see a clean HTML lock screen prompting for the password.

### 4. One-Time Self-Destruct Links (`💣 One-Time`)
* Links automatically burn and deactivate immediately after 1 click.

### 5. Smart Device Routing (iOS / Android / Desktop)
* Single short link routes iPhone/iPad visitors to Apple App Store (`ios_url`), Android visitors to Google Play Store (`android_url`), and Desktop visitors to the main website.

### 6. High-Value Link Analytics Suite
* **Interactive Chart.js Engagement Graph**: Visual line chart showing daily click trend over time (`last_7_days`).
* **Unique Visitors Count**: Counts `func.count(func.distinct(ClickEvent.ip_address))` in PostgreSQL.
* **Traffic Referrer Channel Attribution**: Captures `HTTP Referer` header and categorizes traffic (`LinkedIn`, `Twitter / X`, `WhatsApp`, `Telegram`, `Google Search`, `Direct / External`).

### 7. PNG QR Code Generator
* Dynamically streams PNG QR codes using `qrcode` + `Pillow`.

### 8. Authentication & Google OAuth 2.0
* JWT access token authentication with token rotation.
* Bcrypt password hashing.
* Live Google OAuth 2.0 redirect flow (`/auth/google/login` and `/auth/google/callback`).

---

## 🗄️ 5. Database Schema (SQLAlchemy Models)

### `users` Table
* `id` (UUID, Primary Key)
* `email` (String, Unique, Index)
* `username` (String, Unique, Index)
* `password_hash` (String)
* `is_active` (Boolean)
* `is_verified` (Boolean)
* `created_at` (DateTime UTC)

### `urls` Table
* `id` (UUID, Primary Key)
* `user_id` (UUID, Foreign Key -> `users.id`)
* `short_code` (String, Unique, Index)
* `custom_alias` (String, Unique, Index, Nullable)
* `original_url` (String)
* `title` (String, Nullable)
* `password_hash` (String, Nullable)
* `is_one_time` (Boolean, Default False)
* `ios_url` (String, Nullable)
* `android_url` (String, Nullable)
* `max_clicks` (Integer, Nullable)
* `click_count` (Integer, Default 0)
* `is_active` (Boolean, Default True)
* `created_at` (DateTime UTC)

### `click_events` Table
* `id` (UUID, Primary Key)
* `link_id` (UUID, Foreign Key -> `urls.id`)
* `clicked_at` (DateTime UTC)
* `ip_address` (String, Nullable)
* `referer` (String, Nullable)
* `browser` (String, Nullable)
* `device_type` (String, Nullable)

---

## 🔑 6. API Route Summary

| Method | Route | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register new user account |
| `POST` | `/api/v1/auth/login` | Login user & return JWT token |
| `GET` | `/api/v1/auth/google/login` | Initiate Google OAuth redirect |
| `GET` | `/api/v1/auth/google/callback` | Google OAuth callback handler |
| `POST` | `/api/v1/links/` | Create a short link with custom options |
| `POST` | `/api/v1/links/recommend-alias` | Get AI smart custom alias suggestions |
| `GET` | `/api/v1/links/` | List current user's shortened links |
| `GET` | `/api/v1/links/{id}/stats` | Get full click analytics & Chart.js graph data |
| `GET` | `/api/v1/links/{id}/qr` | Stream PNG QR code for link |
| `GET` | `/s/{short_code}` | Public link redirection & password gate |

---

## 🚀 7. How To Run Locally

```bash
# 1. Clone repository
git clone https://github.com/priyanshubarnwal122-ai/Linkforge.git
cd Linkforge

# 2. Start containers via Docker Compose
docker compose up -d --build

# 3. Access web dashboard
# Open http://localhost:8000 in your browser
```
