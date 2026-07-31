"""Buyer profile management endpoints.

GET    /api/v1/profiles/me          — get current user's buyer profile
PUT    /api/v1/profiles/me          — update buyer preferences
POST   /api/v1/profiles/me          — create buyer profile

NOTE: This module is Slice 4 (Buyer Profiles). The T-4.4 recompute trigger
hook is included here so it can be wired once profiles.py is fully implemented.
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
from app.domain.models import BuyerProfile, User

log = structlog.get_logger()
router = APIRouter(prefix="/profiles", tags=["profiles"])


# ── Schemas ────────────────────────────────────────────────────────────────────


class PreferredLocationItem(BaseModel):
    """Single preferred location with radius."""

    lat: float
    lon: float
    radius_km: float = 5.0


class BuyerProfileUpdate(BaseModel):
    """PUT /api/v1/profiles/me request body."""

    budget_min: float | None = None
    budget_max: float | None = None
    preferred_locations: list[PreferredLocationItem] | None = None
    rooms_min: int | None = None
    bathrooms_min: int | None = None
    area_min: float | None = None
    area_max: float | None = None
    preferred_features: list[str] | None = None
    preferred_property_types: list[str] | None = None


class BuyerProfileResponse(BaseModel):
    """Buyer profile in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    budget_min: float | None
    budget_max: float | None
    preferred_locations: list[PreferredLocationItem] | None
    rooms_min: int | None
    bathrooms_min: int | None
    area_min: float | None
    area_max: float | None
    preferred_features: dict | None
    preferred_property_types: list[str] | None
    created_at: datetime
    updated_at: datetime


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
    response_model=BuyerProfileResponse,
    responses={401: {"description": "Not authenticated"}},
)
async def get_my_buyer_profile(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BuyerProfileResponse:
    """Get the current user's buyer profile."""
    profile = await _get_buyer_profile_or_404(session, user.id)
    return BuyerProfileResponse.model_validate(profile)


# ── PUT /api/v1/profiles/me ───────────────────────────────────────────────────


@router.put(
    "/me",
    response_model=BuyerProfileResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Buyer profile not found"},
    },
)
async def update_my_buyer_profile(
    data: BuyerProfileUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BuyerProfileResponse:
    """Update the current user's buyer profile preferences.

    Changes to preferences trigger async match cache invalidation
    and recompute (see _trigger_match_recompute_on_preference_change).
    """
    profile = await _get_buyer_profile_or_404(session, user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Handle preferred_locations JSONB conversion
    if "preferred_locations" in update_data and update_data["preferred_locations"] is not None:
        update_data["preferred_locations"] = [
            loc.model_dump() for loc in update_data["preferred_locations"]
        ]

    # Handle preferred_features JSONB conversion
    if "preferred_features" in update_data and update_data["preferred_features"] is not None:
        update_data["preferred_features"] = {"features": update_data["preferred_features"]}

    for field, value in update_data.items():
        setattr(profile, field, value)

    profile.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(profile)

    # ── Trigger match recompute ─────────────────────────────────────────────
    _trigger_match_recompute_on_preference_change(session, user.id)

    log.info("buyer_profile_updated", user_id=str(user.id))
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
