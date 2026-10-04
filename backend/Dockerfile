FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////app/data/quicksave.db \
    PORT=8000

WORKDIR /app

# Install curl for healthchecks (tiny layer)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy app code
COPY backend ./backend
COPY frontend ./frontend

# Ensure data dir exists for SQLite persistence
RUN mkdir -p /app/data && chmod 777 /app/data

EXPOSE 8000

# Healthcheck for orchestrators (Render, Railway, Fly, Docker)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:${PORT:-8000}/api/v1/health || exit 1

# Shell form so $PORT (injected by Render/Railway/Fly) is honored; defaults to 8000 locally.
# Use --proxy-headers for correct IP when behind a proxy, and single worker for free-tier RAM.
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers
