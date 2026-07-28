# LinkForge — Enterprise URL Management & Analytics SaaS 🚀

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://linkforge-xw5q.onrender.com)

**LinkForge** is a high-performance, enterprise-grade URL Management and Link Analytics platform engineered with **Python 3.12**, **FastAPI**, **PostgreSQL**, **Redis**, and **Docker**. Designed to compete with global market leaders like Bitly and Dub.co, LinkForge transforms static long links into intelligent, trackable, secure, and editable digital marketing assets.

🌐 **Live Cloud Production**: [https://linkforge-xw5q.onrender.com](https://linkforge-xw5q.onrender.com)  
📖 **Interactive API Documentation (Swagger)**: [https://linkforge-xw5q.onrender.com/docs](https://linkforge-xw5q.onrender.com/docs)  

---

## 🌟 Key Innovations & Architectural Highlights

### ⚡ 1. Dynamic QR Codes (Zero-Reprint System)
Unlike traditional static QR codes that break when a target destination changes, LinkForge encodes dynamic short endpoints (`/s/{short_code}`). **Updating a link's destination URL in the dashboard automatically updates every printed QR code instantly without reprinting physical posters or billboards!**

### 🛡️ 2. Privacy-First Cookieless Analytics (GDPR Engineering)
Built for 100% GDPR compliance using pure server-side request header attribution. **No tracking cookies. No browser fingerprinting scripts.** Visitor IP addresses are anonymized at ingestion using salted SHA-256 truncation (`anon_...`), preserving privacy while accurately deduplicating unique visitors.

### 🧠 3. GenAI & Semantic NLP Custom Alias Engine
Integrated directly with **Google Gemini 1.5 Flash**, **Groq Llama 3**, and **OpenAI APIs**. Replaces gimmicky template suffixes with genuine LLM prompt engineering and semantic NLP keyword extraction (`/facebook-react`, `/apple-iphone-15-pro-max`).

### 🔒 4. Password-Protected Links
Restrict link access behind a sleek, interactive HTML password gate (`?pw=secret`). Unauthorized visitors see a secure lock screen before redirection.

### 💣 5. One-Time Self-Destruct Links
Links automatically burn and permanently deactivate immediately after the first click for secure, sensitive single-use sharing.

### 📱 6. Smart Device Targeting & Routing
A single short link routes **iPhone/iPad** users to the Apple App Store, **Android** users to the Google Play Store, and **Desktop** users to the main website based on dynamic User-Agent detection.

### 📈 7. High-Value Analytics & Chart.js Integration
* **Visual Area Line Graphs**: Daily engagement trend analysis over time (`last_7_days`).
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
├── frontend/                 # Enterprise Single-Page Dashboard UI
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

---

## ⚡ Quick Start Guide (1-Command Setup)

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed on your system.

### Launch Application locally
```bash
# 1. Clone the repository
git clone https://github.com/priyanshubarnwal122-ai/Linkforge.git
cd Linkforge

# 2. Build and launch containers
docker compose up -d --build

# 3. Access LinkForge Dashboard
# Open http://localhost:8000 in your web browser!
```

---

## 📜 License & Author

Developed by **Priyanshu Barnwal** — Released under the MIT License.
