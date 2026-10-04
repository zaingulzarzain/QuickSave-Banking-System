#!/usr/bin/env bash
set -e

# QuickSave production start script
# Works on Render, Railway, Fly.io, Heroku, or any VPS with $PORT

PORT="${PORT:-8000}"
echo "🚀 Starting QuickSave on 0.0.0.0:$PORT"
echo "   Health: /api/v1/health"
echo "   Docs:   /docs"
echo "   UI:     /"

# Ensure data dir exists for SQLite fallback
mkdir -p /app/data 2>/dev/null || mkdir -p ./data || true

exec uvicorn backend.app.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --proxy-headers \
  --log-level info
