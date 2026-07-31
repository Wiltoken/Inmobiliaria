"""User endpoints.

GET /api/v1/users/me — current user profile
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.redis_client import touch_last_active
from app.api.v1.deps import check_session_active, get_current_active_user, get_db
from app.config import settings
from app.domain.models import User
from app.domain.schemas import UserProfile

log = structlog.get_logger()
router = APIRouter(prefix="/users", tags=["users"])


# ── GET /api/v1/users/me ──────────────────────────────────────────────────────


@router.get(
    "/me",
    response_model=UserProfile,
    responses={
        401: {"description": "Not authenticated or session expired"},
        403: {"description": "Account inactive or locked"},
    },
)
async def get_me(
    request: Request,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Return the current authenticated user's profile.

    Updates last_active:{user_id} TTL (session heartbeat).
    Raises 401 AUTH_SESSION_EXPIRED if the session has been inactive for too long.
    """
    # Check session activity (inactivity timeout)
    # This also refreshes the TTL if the session is active
    try:
        await check_session_active(user.id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired due to inactivity",
            headers={"error_code": "AUTH_SESSION_EXPIRED"},
        )

    # Refresh session heartbeat
    await touch_last_active(
        str(user.id),
        ttl_seconds=settings.inactivity_timeout_minutes * 60,
    )

    log.debug("user_profile_accessed", user_id=str(user.id))

    return UserProfile(
        id=user.id,
        username=user.username,
        email=user.email,
        tenant_id=user.tenant_id,
        roles=[role.name for role in user.roles],
        is_active=user.is_active,
        is_locked=user.is_locked,
        consent_given_at=user.consent_given_at,
        password_changed_at=user.password_changed_at,
    )
