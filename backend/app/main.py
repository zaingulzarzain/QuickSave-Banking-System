"""QuickSave Banking System — FastAPI application entrypoint.

Serves the JSON API under /api/v1, interactive docs at /docs,
and the single-page web app from /frontend at /.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.v1.router import api_router
from .core.config import settings
from .db.init_db import init_db

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables + seed demo data on first launch
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A full-stack demo banking system: JWT auth, accounts, atomic transfers, "
        "transaction history, admin controls, and an AI financial assistant "
        "(OpenAI-compatible LLM with offline fallback)."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    """Liveness probe + capability flags (used by the web UI + uptime checks)."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "ai_provider": (
            settings.OPENAI_MODEL if settings.llm_configured else "quicksave-local"
        ),
        "llm_configured": settings.llm_configured,
    }


@app.get("/api")
def api_index():
    return JSONResponse(
        {
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/api/v1/health",
            "ui": "/",
        }
    )


# --- Serve the single-page web app (must be mounted LAST) ---
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
