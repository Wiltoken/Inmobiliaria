"""Favorite property endpoints.

GET    /api/v1/favorites              — user's favorited properties
POST   /api/v1/favorites              — add property to favorites
DELETE /api/v1/favorites/{property_id} — remove property from favorites
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_active_user, get_db
from app.domain.models import Favorite, Property, User
from app.domain.schemas import FavoriteCreate, FavoriteResponse

log = structlog.get_logger()
router = APIRouter(prefix="/favorites", tags=["favorites"])


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _get_favorite_or_404(
    session: AsyncSession, user_id: uuid.UUID, property_id: uuid.UUID
) -> Favorite:
    """Load favorite or raise 404."""
    result = await session.execute(
        select(Favorite).where(
            and_(
                Favorite.user_id == user_id,
                Favorite.property_id == property_id,
            )
        )
    )
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found",
        )
    return fav


# ── GET /api/v1/favorites ──────────────────────────────────────────────────────


@router.get(
    "",
    response_model=list[FavoriteResponse],
    responses={401: {"description": "Not authenticated"}},
)
async def list_favorites(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[FavoriteResponse]:
    """List all properties favorited by the current user."""
    result = await session.execute(
        select(Favorite)
        .where(Favorite.user_id == user.id)
        .order_by(Favorite.created_at.desc())
    )
    favorites = result.scalars().all()
    return [FavoriteResponse.model_validate(f) for f in favorites]


# ── POST /api/v1/favorites ─────────────────────────────────────────────────────


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=FavoriteResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Property not found"},
        409: {"description": "Already favorited"},
    },
)
async def add_favorite(
    data: FavoriteCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> FavoriteResponse:
    """Add a property to the user's favorites."""
    # Verify property exists
    prop_result = await session.execute(
        select(Property).where(Property.id == data.property_id)
    )
    prop = prop_result.scalar_one_or_none()
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    # Check if already favorited
    existing_result = await session.execute(
        select(Favorite).where(
            and_(
                Favorite.user_id == user.id,
                Favorite.property_id == data.property_id,
            )
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Property already in favorites",
        )

    favorite = Favorite(
        user_id=user.id,
        property_id=data.property_id,
    )
    session.add(favorite)
    await session.flush()
    await session.refresh(favorite)

    log.info("favorite_added", user_id=str(user.id), property_id=str(data.property_id))
    return FavoriteResponse.model_validate(favorite)


# ── DELETE /api/v1/favorites/{property_id} ─────────────────────────────────────


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Favorite not found"},
    },
)
async def remove_favorite(
    property_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Remove a property from the user's favorites."""
    favorite = await _get_favorite_or_404(session, user.id, property_id)
    await session.delete(favorite)
    await session.flush()

    log.info("favorite_removed", user_id=str(user.id), property_id=str(property_id))
