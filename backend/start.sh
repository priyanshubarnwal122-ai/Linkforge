#!/bin/sh
set -e

echo "=== LinkForge Startup ==="
echo "Running database migrations..."
cd /app && alembic upgrade head
echo "Migrations complete. Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
