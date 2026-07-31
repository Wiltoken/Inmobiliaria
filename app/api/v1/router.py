"""API v1 router — aggregates all /api/v1/* route modules."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router

# ── v1 API router ─────────────────────────────────────────────────────────────


api_router = APIRouter(prefix="/api/v1")

# Auth: /api/v1/auth/login, /api/v1/auth/refresh, /api/v1/auth/logout, /api/v1/auth/forgot-password, /api/v1/auth/reset-password
api_router.include_router(auth_router)

# Users: /api/v1/users/me
api_router.include_router(users_router)

# Admin: /api/v1/admin/users, /api/v1/admin/audit-logs, /api/v1/admin/compliance-report
api_router.include_router(admin_router)
