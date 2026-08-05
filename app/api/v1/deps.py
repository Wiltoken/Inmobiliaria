"""Dependency injection chain: get_db → get_current_user → require_role.

All protected endpoints use these dependencies. The DI chain is the single
entry point for DB session and auth context.
"""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.database import get_session_maker
from app.adapters.redis_client import (
    is_last_active_expired,
    touch_last_active,
)
from app.config import settings
from app.core.exceptions import (
    InsufficientRoleError,
    SessionExpiredError,
)
from app.domain.models import User

# ── Database session ──────────────────────────────────────────────────────────


async def get_db() -> AsyncSession:
    """Yield an AsyncSession from the session maker.

    Handles commit/rollback and closes on yield teardown.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Auth context from request.state ──────────────────────────────────────────


async def get_current_user(request: Request) -> User:
    """Return the current authenticated user from request.state.

    Raises 401 if no user is attached (token missing, invalid, or blacklisted).
    This dependency should be used after AuthMiddleware has run.
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Fetch the user from DB to ensure they still exist and are active
    session_maker = get_session_maker()
    async with session_maker() as session:
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_active_user(
    request: Request,
) -> User:
    """Return the current user and check they are active and not locked.

    Raises 401 if account is inactive or locked.
    """
    user = await get_current_user(request)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    if user.is_locked:
        locked_until_str = None
        if user.locked_until:
            locked_until_str = user.locked_until.isoformat()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked",
            headers={"X-Locked-Until": locked_until_str or ""},
        )

    return user


def require_role(*roles: str) -> Callable:
    """FastAPI Depends that checks current_user.roles against allowed roles.

    Usage:
        @app.get("/admin", dependencies=[Depends(require_role("admin"))])
        def admin_endpoint(user: User = Depends(get_current_active_user)):
            ...

    Raises 403 if the user has insufficient roles.
    """

    async def role_checker(
        request: Request,
        user: User = Depends(get_current_active_user),
    ) -> User:
        user_role_names = [role.name for role in user.roles]
        if not any(r in user_role_names for r in roles):
            raise InsufficientRoleError(required_roles=list(roles))
        return user

    return role_checker


def get_tenant_id(request: Request) -> uuid.UUID:
    """Extract tenant_id from the current authenticated user.

    Raises 401 if no authenticated user.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return tenant_id


# ── Session activity check ────────────────────────────────────────────────────


async def check_session_active(user_id: uuid.UUID) -> None:
    """Dependency that verifies the user's session is still active.

    Checks Redis last_active:{user_id} key. If missing/expired, raises 401.
    If valid, refreshes the TTL (sliding window).

    Applied to authenticated endpoints via Depends(check_session_active).
    """
    if await is_last_active_expired(str(user_id)):
        raise SessionExpiredError()

    # Refresh the TTL (sliding window)
    await touch_last_active(
        str(user_id),
        ttl_seconds=settings.inactivity_timeout_minutes * 60,
    )


def require_session_active(
    user_id: uuid.UUID,
) -> None:
    """Dependency wrapper for check_session_active.

    Usage:
        user: User = Depends(get_current_active_user),
        ...
    ) -> None:
        await check_session_active(user.id)
    """
    return check_session_active(user_id)
