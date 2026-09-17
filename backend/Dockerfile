FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////app/data/quicksave.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend

RUN mkdir -p /app/data

EXPOSE 8000

# Shell form so $PORT (injected by Render/Railway) is honored; defaults to 8000 locally.
CMD uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}
