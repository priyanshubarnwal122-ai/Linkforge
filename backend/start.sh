#!/bin/sh
set -e

echo "=== LinkForge Startup ==="
echo "Running database migrations..."
cd /app

# Render's managed database can take a moment to accept connections after the
# web container is created. Retrying here keeps migration responsibility in
# the startup path without changing application request behavior.
attempt=1
until alembic upgrade head; do
    if [ "$attempt" -ge 30 ]; then
        echo "Database migrations failed after ${attempt} attempts" >&2
        exit 1
    fi
    echo "Migration attempt ${attempt} failed; retrying in 2 seconds..." >&2
    attempt=$((attempt + 1))
    sleep 2
done
echo "Migrations complete. Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
