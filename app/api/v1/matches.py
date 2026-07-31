"""Property-to-buyer matching endpoints.

GET    /api/v1/matches              — paginated matches for current buyer (sorted by score desc)
POST   /api/v1/matches/compute      — trigger recompute for current user
GET    /api/v1/matches/{match_id}  — match detail with score breakdown
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_current_active_user, get_db
from app.core.matching import (
    compute_all_matches,
    get_matches_from_cache,
    get_paginated_matches,
)
from app.domain.models import Match, User

log = structlog.get_logger()
router = APIRouter(prefix="/matches", tags=["matches"])


# ── Response schemas ──────────────────────────────────────────────────────────


class ScoreBreakdown(BaseModel):
    price: float
    location: float
    features: float
    area: float


class MatchPropertySummary(BaseModel):
    """Minimal property info embedded in match response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    operation: str
    price: float
    area_m2: float | None
    lat: float | None
    lon: float | None
    rooms: int | None
    bathrooms: int | None
    features: dict | None
    title: str
    status: str
    is_active: bool
    published_at: datetime | None


class MatchDetailResponse(BaseModel):
    """Single match with full score breakdown."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    score: float
    score_breakdown: dict
    computed_at: datetime
    property: MatchPropertySummary


class PaginatedMatchesResponse(BaseModel):
    """GET /api/v1/matches paginated response."""

    matches: list[MatchDetailResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# ── Helpers ────────────────────────────────────────────────────────────────────


def _property_summary(prop) -> MatchPropertySummary:
    """Extract lat/lon from GeoJSON location."""
    lat, lon = None, None
    if prop.location and prop.location.get("type") == "Point":
        coords = prop.location.get("coordinates", [])
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None

    return MatchPropertySummary(
        id=prop.id,
        type=prop.type,
        operation=prop.operation,
        price=prop.price,
        area_m2=prop.area_m2,
        lat=lat,
        lon=lon,
        rooms=prop.rooms,
        bathrooms=prop.bathrooms,
        features=prop.features,
        title=prop.title,
        status=prop.status,
        is_active=prop.is_active,
        published_at=prop.published_at,
    )


# ── GET /api/v1/matches ───────────────────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedMatchesResponse,
    responses={
        401: {"description": "Not authenticated"},
    },
)
async def list_matches(
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PaginatedMatchesResponse:
    """Get paginated matches for the current buyer, sorted by score descending.

    Tries Redis cache first; falls back to DB on cache miss.
    """
    # Try cache first
    cached = await get_matches_from_cache(user.id)
    if cached is not None:
        total = len(cached)
        offset = (page - 1) * limit
        page_items = cached[offset : offset + limit]
        total_pages = (total + limit - 1) // limit if limit else 1
        # Hydrate property from DB for the page items
        property_ids = [uuid.UUID(m["property_id"]) for m in page_items if m.get("property_id")]
        if property_ids:
            from app.domain.models import Property
            result = await session.execute(
                select(Property).where(Property.id.in_(property_ids))
            )
            props_by_id = {str(p.id): p for p in result.scalars().all()}
            matches = []
            for m in page_items:
                prop = props_by_id.get(m.get("property_id"))
                if prop:
                    from datetime import datetime
                    computed_at = datetime.fromisoformat(m["computed_at"]) if isinstance(m.get("computed_at"), str) else m.get("computed_at")
                    matches.append(
                        MatchDetailResponse(
                            id=uuid.UUID(m["id"]) if isinstance(m["id"], str) else m["id"],
                            property_id=uuid.UUID(m["property_id"]) if isinstance(m["property_id"], str) else m["property_id"],
                            score=m["score"],
                            score_breakdown=m["score_breakdown"],
                            computed_at=computed_at,
                            property=_property_summary(prop),
                        )
                    )
        else:
            matches = []

        return PaginatedMatchesResponse(
            matches=matches,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )

    # Cache miss — query DB
    matches, total = await get_paginated_matches(user.id, session, page, limit)
    total_pages = (total + limit - 1) // limit if limit else 1

    return PaginatedMatchesResponse(
        matches=[
            MatchDetailResponse(
                id=m.id,
                property_id=m.property_id,
                score=m.score,
                score_breakdown=m.score_breakdown or {},
                computed_at=m.computed_at,
                property=_property_summary(m.property),
            )
            for m in matches
        ],
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )


# ── POST /api/v1/matches/compute ───────────────────────────────────────────────


@router.post(
    "/compute",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Buyer profile not found"},
    },
)
async def recompute_matches(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger match recomputation for the current user.

    Recomputes scores for all published/active properties and updates
    the Match table and Redis cache.
    """
    computed = await compute_all_matches(user.id, session)
    return {
        "message": "Matches recomputed",
        "count": len(computed),
    }


# ── GET /api/v1/matches/{match_id} ────────────────────────────────────────────


@router.get(
    "/{match_id}",
    response_model=MatchDetailResponse,
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Match not found"},
    },
)
async def get_match(
    match_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> MatchDetailResponse:
    """Get a single match detail with full score breakdown.

    Only returns matches belonging to the current user.
    """
    result = await session.execute(
        select(Match)
        .options(selectinload(Match.property))
        .options(selectinload(Match.buyer))
        .where(Match.id == match_id)
    )
    match = result.scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    # Ensure the match belongs to the current user's buyer profile
    if match.buyer.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found",
        )

    return MatchDetailResponse(
        id=match.id,
        property_id=match.property_id,
        score=match.score,
        score_breakdown=match.score_breakdown or {},
        computed_at=match.computed_at,
        property=_property_summary(match.property),
    )
