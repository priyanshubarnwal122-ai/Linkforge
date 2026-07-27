# LinkForge — Enterprise URL Management & Analytics Platform 🚀

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis&logoColor=white)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**LinkForge** is a modern, high-performance, enterprise-grade URL Shortener and Link Management Platform competing directly with Bitly and Dub.co. Built with an asynchronous Python/FastAPI microservices architecture, PostgreSQL, Redis caching, and a clean Google Cloud/Stripe-styled enterprise dashboard.

---

## ✨ Features & Innovations

* 🤖 **AI Smart Alias Recommender**: Analyzes long URLs in real-time, generates 3–4 brandable vanity alias suggestions (`/facebook-react`, `/amazon-direct`), and assigns a live Domain Trust Score.
* 🔒 **Password-Protected Links**: Restrict link access behind an interactive HTML password gate (`?pw=secret`).
* 💣 **One-Time Self-Destruct Links**: Links automatically burn and deactivate immediately after 1 click.
* 📱 **Smart Device Routing**: 1 short URL routes iPhone users to Apple App Store, Android users to Google Play Store, and Desktop users to your website.
* 📷 **PNG QR Code Generator**: Export and download high-resolution QR codes directly from the dashboard.
* 📊 **Real-Time Click Analytics**: Visual click breakdown, top device types, and browser distribution.
* 🔑 **JWT & Google OAuth 2.0 Auth**: Secure authentication with short-lived access tokens, refresh token rotation, and Google login integration.
* 🐳 **Fully Dockerized Architecture**: Automated orchestration with Docker Compose, PostgreSQL 16, and Redis 7.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Language** | Python 3.12 |
| **Web Framework** | FastAPI + Uvicorn (ASGI) |
| **Database & ORM** | PostgreSQL 16 + Async SQLAlchemy 2.0 |
| **Database Migrations** | Alembic |
| **Caching & Rate Limit** | Redis 7 (`redis-py` / `aioredis`) |
| **Authentication** | JWT (python-jose), Bcrypt, Google OAuth 2.0 |
| **Frontend** | HTML5, Vanilla CSS3 (Google Enterprise System), Vanilla JS (ES6) |
| **Containerization** | Docker & Docker Compose (Multi-stage build) |

---

## 📁 Repository Structure

```text
url_shortener/
├── backend/                  # Asynchronous FastAPI Microservice
│   ├── app/                  # Application Logic (Routers, Services, Models, Schemas)
│   ├── alembic/              # Database Schema Revisions & Migrations
│   ├── alembic.ini           # Alembic Migration Configuration
│   ├── Dockerfile            # Production Multi-Stage Dockerfile
│   └── requirements.txt      # Python Dependencies
├── frontend/                 # Enterprise Single-Page Web Dashboard
│   ├── index.html            # HTML5 Web App Structure & Modals
│   ├── styles.css            # Google Cloud / Stripe CSS Design System
│   └── app.js                # Frontend API Client & AI Recommender Engine
├── docker-compose.yml        # Orchestrates API, PostgreSQL, Redis & Adminer
├── .env.example              # Environment Variables Template
└── README.md                 # Project Documentation
```

---

## 🚀 Quick Start (Local Setup)

### Prerequisites
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
* [Git](https://git-scm.com/)

### 1. Clone Repository
```bash
git clone https://github.com/your-username/linkforge.git
cd linkforge
```

### 2. Configure Environment Variables
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```

### 3. Launch with Docker Compose
Run the following command to build and launch all containers (`api`, `postgres`, `redis`, `adminer`):
```bash
docker compose up -d --build
```

### 4. Open the Web Application
Open your browser and navigate to:
👉 **[http://localhost:8000/](http://localhost:8000/)**

---

## 🔑 Demo Account Credentials

You can test LinkForge immediately using pre-configured demo credentials:

* **Email**: `testuser@example.com`
* **Password**: `Password123!`

---

## 📖 API Documentation & Endpoints

FastAPI automatically generates interactive Swagger & OpenAPI documentation:

* **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc UI**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **OpenAPI Schema**: [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json)

### Core Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/links/` | Shorten a long URL with custom options |
| `POST` | `/api/v1/links/recommend-alias` | Get AI smart custom alias suggestions |
| `GET` | `/api/v1/links/{id}/qr` | Download PNG QR code for a link |
| `GET` | `/api/v1/links/{id}/stats` | Get real-time click analytics & device stats |
| `GET` | `/s/{short_code}` | Public link redirection & password unlock gate |

---

## ⚙️ Environment Variables Reference

```env
ENVIRONMENT=development
SECRET_KEY=super_secret_key_at_least_32_characters_long

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=linkforge
POSTGRES_USER=linkforge_user
POSTGRES_PASSWORD=linkforge_dev_password

REDIS_HOST=redis
REDIS_PORT=6379

BASE_URL=http://localhost:8000
SHORT_CODE_LENGTH=7
```

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
