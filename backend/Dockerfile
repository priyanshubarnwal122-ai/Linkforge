# LinkForge — Multi-stage Dockerfile
# Stage 1 (builder): install deps into venv
# Stage 2 (production): copy only the venv — no build tools in the final image

FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1001 linkforge && \
    useradd --uid 1001 --gid 1001 --shell /bin/bash --create-home linkforge

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=linkforge:linkforge . .

# frontend/ is bundled inside backend/ for build context access
RUN if [ -d "/app/frontend" ]; then cp -r /app/frontend /frontend; fi

USER linkforge

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8000/api/v1/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
