"""Profile management endpoints for all roles.

GET    /api/v1/profiles/me          — get profile based on role
PUT    /api/v1/profiles/me          — update own profile
PATCH  /api/v1/profiles/buyer       — update buyer preferences (triggers match recompute)

Buyer profiles, seller profiles, and agent profiles are all managed here.
The role is detected from the user's roles at runtime.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_active_user, get_db
from app.domain.models import AgentProfile, BuyerProfile, SellerProfile, User
from app.domain.schemas import (
    AgentProfileResponse,
    AgentProfileUpdate,
    BuyerProfileResponse,
    BuyerProfileUpdate,
    PreferredLocationItem,
    SellerProfileResponse,
    SellerProfileUpdate,
)

log = structlog.get_logger()
router = APIRouter(prefix="/profiles", tags=["profiles"])


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _get_buyer_profile_or_404(
    session: AsyncSession, user_id: uuid.UUID
) -> BuyerProfile:
    """Load buyer profile for a user or raise 404."""
    result = await session.execute(
        select(BuyerProfile).where(BuyerProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Buyer profile not found. Create one first.",
        )
    return profile


async def _get_seller_profile_or_404(
    session: AsyncSession, user_id: uuid.UUID
) -> SellerProfile:
    """Load seller profile for a user or raise 404."""
    result = await session.execute(
        select(SellerProfile).where(SellerProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seller profile not found.",
        )
    return profile


async def _get_agent_profile_or_404(
    session: AsyncSession, user_id: uuid.UUID
) -> AgentProfile:
    """Load agent profile for a user or raise 404."""
    result = await session.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent profile not found.",
        )
    return profile


def _get_user_role(user: User) -> str | None:
    """Return the first role name for the user, or None."""
    if not user.roles:
        return None
    return user.roles[0].name


def _trigger_match_recompute_on_preference_change(
    session: AsyncSession, user_id: uuid.UUID
) -> None:
    """Trigger match recompute when buyer preferences change.

    NOTE: This is a fire-and-forget background trigger. In production,
    this should be a proper background job (Celery, Redis queue, etc.)
    to avoid blocking the profile update response.

    The full recompute invalidates the Redis cache and schedules a
    compute_all_matches() for the buyer.
    """
    import asyncio

    log.info(
        "match_recompute_triggered",
        reason="preference_change",
        user_id=str(user_id),
    )

    async def _recompute():
        try:
            from app.core.matching import compute_all_matches

            await compute_all_matches(user_id, session)
            log.info("match_recompute_completed", user_id=str(user_id))
        except Exception as exc:
            log.warning("match_recompute_failed", user_id=str(user_id), error=str(exc))

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_recompute())
    except RuntimeError:
        # No running loop (tests, startup)
        pass


# ── GET /api/v1/profiles/me ───────────────────────────────────────────────────


@router.get(
    "/me",
    responses={401: {"description": "Not authenticated"}},
)
async def get_my_profile(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
):
    """Get the current user's profile based on their role.

    Returns BuyerProfileResponse, SellerProfileResponse, or AgentProfileResponse
    depending on the user's primary role.
    """
    role = _get_user_role(user)

    if role == "buyer":
        profile = await _get_buyer_profile_or_404(session, user.id)
        return BuyerProfileResponse.model_validate(profile)
    elif role == "seller":
        profile = await _get_seller_profile_or_404(session, user.id)
        return SellerProfileResponse.model_validate(profile)
    elif role == "agent":
        profile = await _get_agent_profile_or_404(session, user.id)
        return AgentProfileResponse.model_validate(profile)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No profile available for your role",
        )


# ── PUT /api/v1/profiles/me ───────────────────────────────────────────────────


@router.put(
    "/me",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "No profile for your role"},
    },
)
async def update_my_profile(
    data: BuyerProfileUpdate | SellerProfileUpdate | AgentProfileUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
):
    """Update the current user's profile based on their role.

    Accepts BuyerProfileUpdate, SellerProfileUpdate, or AgentProfileUpdate
    depending on the user's primary role.
    """
    role = _get_user_role(user)

    if role == "buyer":
        profile = await _get_buyer_profile_or_404(session, user.id)
        update_data = data.model_dump(exclude_unset=True)
        if "preferred_locations" in update_data and update_data["preferred_locations"] is not None:
            update_data["preferred_locations"] = [loc.model_dump() for loc in update_data["preferred_locations"]]
        if "preferred_features" in update_data and update_data["preferred_features"] is not None:
            update_data["preferred_features"] = {"features": update_data["preferred_features"]}
        for field, value in update_data.items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now(timezone.utc)
        await session.flush()
        await session.refresh(profile)
        _trigger_match_recompute_on_preference_change(session, user.id)
        log.info("buyer_profile_updated", user_id=str(user.id))
        return BuyerProfileResponse.model_validate(profile)

    elif role == "seller":
        profile = await _get_seller_profile_or_404(session, user.id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now(timezone.utc)
        await session.flush()
        await session.refresh(profile)
        log.info("seller_profile_updated", user_id=str(user.id))
        return SellerProfileResponse.model_validate(profile)

    elif role == "agent":
        profile = await _get_agent_profile_or_404(session, user.id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(profile, field, value)
        profile.updated_at = datetime.now(timezone.utc)
        await session.flush()
        await session.refresh(profile)
        log.info("agent_profile_updated", user_id=str(user.id))
        return AgentProfileResponse.model_validate(profile)

    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No profile available for your role",
        )


# ── PATCH /api/v1/profiles/buyer ───────────────────────────────────────────────


@router.patch(
    "/buyer",
    response_model=BuyerProfileResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Buyer profile not found"},
    },
)
async def patch_my_buyer_preferences(
    data: BuyerProfileUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BuyerProfileResponse:
    """Update buyer preferences only (PATCH semantics — partial update).

    This endpoint specifically targets buyer preferences and triggers
    match cache invalidation when preferences change.
    """
    profile = await _get_buyer_profile_or_404(session, user.id)

    update_data = data.model_dump(exclude_unset=True)

    if "preferred_locations" in update_data and update_data["preferred_locations"] is not None:
        update_data["preferred_locations"] = [
            loc.model_dump() for loc in update_data["preferred_locations"]
        ]

    if "preferred_features" in update_data and update_data["preferred_features"] is not None:
        update_data["preferred_features"] = {"features": update_data["preferred_features"]}

    for field, value in update_data.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(profile)

    _trigger_match_recompute_on_preference_change(session, user.id)

    log.info("buyer_preferences_patched", user_id=str(user.id))
    return BuyerProfileResponse.model_validate(profile)


# ── POST /api/v1/profiles/me — create buyer profile ───────────────────────────


@router.post(
    "/me",
    status_code=status.HTTP_201_CREATED,
    response_model=BuyerProfileResponse,
    responses={401: {"description": "Not authenticated"}},
)
async def create_my_buyer_profile(
    data: BuyerProfileUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BuyerProfileResponse:
    """Create a buyer profile for the current user.

    Fails if a profile already exists. Use PUT to update existing profiles.
    """
    # Check if profile already exists
    result = await session.execute(
        select(BuyerProfile).where(BuyerProfile.user_id == user.id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Buyer profile already exists. Use PUT to update.",
        )

    profile_data: dict = {"user_id": user.id}

    if data.budget_min is not None:
        profile_data["budget_min"] = data.budget_min
    if data.budget_max is not None:
        profile_data["budget_max"] = data.budget_max
    if data.preferred_locations is not None:
        profile_data["preferred_locations"] = [loc.model_dump() for loc in data.preferred_locations]
    if data.rooms_min is not None:
        profile_data["rooms_min"] = data.rooms_min
    if data.bathrooms_min is not None:
        profile_data["bathrooms_min"] = data.bathrooms_min
    if data.area_min is not None:
        profile_data["area_min"] = data.area_min
    if data.area_max is not None:
        profile_data["area_max"] = data.area_max
    if data.preferred_features is not None:
        profile_data["preferred_features"] = {"features": data.preferred_features}
    if data.preferred_property_types is not None:
        profile_data["preferred_property_types"] = data.preferred_property_types

    profile = BuyerProfile(**profile_data)
    session.add(profile)
    await session.flush()
    await session.refresh(profile)

    log.info("buyer_profile_created", user_id=str(user.id))
    return BuyerProfileResponse.model_validate(profile)
