"""User endpoints.

GET /api/v1/users/me — current user profile
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.redis_client import blacklist_token, touch_last_active
from app.api.v1.deps import check_session_active, get_current_active_user, get_db
from app.config import settings
from app.core.security import get_token_remaining_ttl
from app.domain.models import (
    AgentProfile,
    AuditLog,
    BuyerProfile,
    PasswordReset,
    RefreshToken,
    SellerProfile,
    User,
)
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


# ── POST /api/v1/users/me/delete-data ─────────────────────────────────────────


@router.post(
    "/me/delete-data",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Not authenticated or session expired"},
    },
)
async def delete_my_data(
    request: Request,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Request deletion of own data for Ley 1581 compliance.

    Soft-deletes the user, cascades to profiles, revokes tokens,
    anonymizes audit logs, and invalidates the current token.
    """
    now = datetime.now(UTC)

    # Re-fetch the user in this session: the `user` dependency is detached
    # (fetched and closed in get_current_user), so mutating it directly would
    # not persist. Work on a session-bound instance instead.
    result = await session.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one()

    db_user.deleted_at = now
    db_user.deletion_reason = "user_requested"
    db_user.is_active = False

    profiles_result = await session.execute(
        select(BuyerProfile).where(BuyerProfile.user_id == user.id)
    )
    if buyer := profiles_result.scalar_one_or_none():
        buyer.is_deleted = True

    profiles_result = await session.execute(
        select(SellerProfile).where(SellerProfile.user_id == user.id)
    )
    if seller := profiles_result.scalar_one_or_none():
        seller.is_deleted = True

    profiles_result = await session.execute(
        select(AgentProfile).where(AgentProfile.user_id == user.id)
    )
    if agent := profiles_result.scalar_one_or_none():
        agent.is_deleted = True

    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )

    await session.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user.id, PasswordReset.used_at.is_(None))
        .values(used_at=now)
    )

    await session.execute(
        update(AuditLog)
        .where(AuditLog.user_id == user.id)
        .values(ip_address=None)
    )

    try:
        audit_entry = AuditLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="user_requested_data_deletion",
            ip_address=request.client.host if request.client else None,
            details={},
        )
        session.add(audit_entry)
    except Exception as exc:
        log.warning("audit_log_write_failed", action="user_requested_data_deletion", error=str(exc))

    await session.commit()

    jti = getattr(request.state, "jti", None)
    token = getattr(request.state, "token", None)
    if jti and token:
        remaining_ttl = get_token_remaining_ttl(token)
        if remaining_ttl > 0:
            await blacklist_token(jti, remaining_ttl)

    log.info("user_self_deleted_data", user_id=str(user.id))
