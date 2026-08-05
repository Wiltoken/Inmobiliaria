"""API v1 router — aggregates all /api/v1/* route modules."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.agent import router as agent_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.favorites import router as favorites_router
from app.api.v1.inquiries import router as inquiries_router
from app.api.v1.matches import router as matches_router
from app.api.v1.profiles import router as profiles_router
from app.api.v1.properties import router as properties_router
from app.api.v1.users import router as users_router

# ── v1 API router ─────────────────────────────────────────────────────────────


api_router = APIRouter(prefix="/api/v1")

# Auth: /api/v1/auth/login, /api/v1/auth/refresh, /api/v1/auth/logout, /api/v1/auth/forgot-password, /api/v1/auth/reset-password
api_router.include_router(auth_router)

# Users: /api/v1/users/me
api_router.include_router(users_router)

# Admin: /api/v1/admin/users, /api/v1/admin/audit-logs, /api/v1/admin/compliance-report
api_router.include_router(admin_router)

# Properties: /api/v1/properties, /api/v1/properties/{id}, /api/v1/properties/{id}/photos, etc.
api_router.include_router(properties_router)

# Matches: /api/v1/matches, /api/v1/matches/compute, /api/v1/matches/{match_id}
api_router.include_router(matches_router)

# Profiles: /api/v1/profiles/me (buyer/seller/agent profile CRUD)
api_router.include_router(profiles_router)

# Inquiries: /api/v1/inquiries (create, list, respond)
api_router.include_router(inquiries_router)

# Favorites: /api/v1/favorites (add, remove, list)
api_router.include_router(favorites_router)

# Agent: /api/v1/agent/dashboard/* and /api/v1/agent/inquiries
api_router.include_router(agent_router)

# Audit: /api/v1/audit/user-action
api_router.include_router(audit_router)
