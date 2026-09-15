"""API v1 router — single place where all endpoint modules plug in."""

from fastapi import APIRouter

from .accounts import router as accounts_router
from .admin import router as admin_router
from .ai import router as ai_router
from .auth import router as auth_router
from .transactions import router as transactions_router
from .users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(accounts_router)
api_router.include_router(transactions_router)
api_router.include_router(ai_router)
api_router.include_router(admin_router)
