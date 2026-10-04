# Root Dockerfile — for platforms that expect Dockerfile at repo root
# Mirrors backend/Dockerfile so Render, Railway, Fly, etc. all work.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////app/data/quicksave.db \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend

RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:${PORT:-8000}/api/v1/health || exit 1

CMD uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers
