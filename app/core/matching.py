"""Weighted scoring algorithm for buyer-property matching.

Public API:
    score_price()
    score_location()
    score_features()
    score_area()
    compute_match()
    compute_all_matches()
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.redis_client import (
    cache_matches,
    get_cached_matches,
    invalidate_match_cache,
)
from app.domain.models import BuyerProfile, Match, Property, PropertyStatus

log = structlog.get_logger()


# ── Individual score functions ─────────────────────────────────────────────────


def score_price(budget_min: float | None, budget_max: float | None, property_price: float) -> float:
    """100 if within budget, linear decay outside.

    Args:
        budget_min: Lower bound of buyer budget (inclusive).
        budget_max: Upper bound of buyer budget (inclusive).
        property_price: Price of the property.

    Returns:
        Score 0-100. Returns 50 (neutral) if budget bounds are not set.
    """
    if budget_min is None or budget_max is None:
        return 50.0
    if budget_min <= property_price <= budget_max:
        return 100.0
    midpoint = (budget_min + budget_max) / 2
    diff = abs(property_price - midpoint) / midpoint
    return max(0.0, 100.0 - diff * 100.0)


def score_location(
    preferred_locations: list[dict] | None,
    property_lat: float | None,
    property_lon: float | None,
) -> float:
    """Score based on location proximity.

    Preferred locations is a list of {lat, lon, radius_km} dicts from JSONB.
    For MVP: if any preferred location has property within its radius, score 100.
    Otherwise, closest distance scores with decay.

    Args:
        preferred_locations: List of {lat, lon, radius_km} from buyer profile JSONB.
        property_lat: Property latitude.
        property_lon: Property longitude.

    Returns:
        Score 0-100. Returns 50 (neutral) if no preferences or coords are missing.
    """
    if not preferred_locations or property_lat is None or property_lon is None:
        return 50.0

    closest_distance_km: float | None = None

    for loc in preferred_locations:
        lat = loc.get("lat")
        lon = loc.get("lon")
        radius_km = loc.get("radius_km", 5.0)  # default 5 km radius

        if lat is None or lon is None:
            continue

        distance_km = _haversine_km(property_lat, property_lon, lat, lon)

        if distance_km <= radius_km:
            return 100.0  # Within at least one preferred radius

        if closest_distance_km is None or distance_km < closest_distance_km:
            closest_distance_km = distance_km

    # No radius match — decay from 100 based on closest distance
    if closest_distance_km is not None:
        # Decay: 50 at 0km, 0 at 50km (tunable)
        decay_range_km = 50.0
        score = max(0.0, 100.0 - (closest_distance_km / decay_range_km) * 100.0)
        return round(score, 2)

    return 50.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance between two points in km."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def score_features(preferred_features: list[str] | None, property_features: list[str] | None) -> float:
    """Jaccard similarity between preferred and property features.

    Args:
        preferred_features: List of feature strings from buyer profile.
        property_features: List of feature strings from property.

    Returns:
        Score 0-100. Returns 50 (neutral) if either list is empty.
    """
    if not preferred_features or not property_features:
        return 50.0
    intersection = len(set(preferred_features) & set(property_features))
    union = len(set(preferred_features) | set(property_features))
    if union == 0:
        return 50.0
    return (intersection / union) * 100.0


def score_area(area_min: float | None, area_max: float | None, property_area: float | None) -> float:
    """100 if within range, linear decay outside.

    Args:
        area_min: Minimum preferred area in m².
        area_max: Maximum preferred area in m².
        property_area: Property area in m².

    Returns:
        Score 0-100. Returns 50 (neutral) if bounds are not set.
    """
    if area_min is None or area_max is None or property_area is None:
        return 50.0
    if area_min <= property_area <= area_max:
        return 100.0
    midpoint = (area_min + area_max) / 2
    diff = abs(property_area - midpoint) / midpoint
    return max(0.0, 100.0 - diff * 100.0)


# ── Match computation ──────────────────────────────────────────────────────────


def compute_match(buyer: BuyerProfile, prop: Property) -> dict:
    """Compute total match score with breakdown for a single buyer-property pair.

    Weights:
        price: 30%
        location: 25%
        features: 25%
        area: 20%

    Args:
        buyer: BuyerProfile ORM model instance.
        prop: Property ORM model instance.

    Returns:
        {"total": float, "breakdown": {"price": float, "location": float,
         "features": float, "area": float}}
    """
    # Extract lat/lon from GeoJSON location dict
    lat, lon = None, None
    if prop.location and prop.location.get("type") == "Point":
        coords = prop.location.get("coordinates", [])
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None

    # Extract features list (stored as {"features": [...]})
    prop_features: list[str] = []
    if prop.features and isinstance(prop.features, dict):
        prop_features = prop.features.get("features", [])

    # Extract preferred features list
    buyer_features: list[str] = []
    if buyer.preferred_features and isinstance(buyer.preferred_features, dict):
        buyer_features = buyer.preferred_features.get("features", [])

    raw_price = score_price(buyer.budget_min, buyer.budget_max, prop.price)
    raw_location = score_location(buyer.preferred_locations, lat, lon)
    raw_features = score_features(buyer_features, prop_features)
    raw_area = score_area(buyer.area_min, buyer.area_max, prop.area_m2)

    total = raw_price * 0.30 + raw_location * 0.25 + raw_features * 0.25 + raw_area * 0.20

    return {
        "total": round(total, 2),
        "breakdown": {
            "price": round(raw_price, 2),
            "location": round(raw_location, 2),
            "features": round(raw_features, 2),
            "area": round(raw_area, 2),
        },
    }


async def compute_all_matches(buyer_id: uuid.UUID, session: AsyncSession) -> list[dict]:
    """Recompute matches for a buyer against all published properties.

    1. Get buyer profile.
    2. Get all published/active properties.
    3. Score each property.
    4. Upsert Match records (ON CONFLICT UPDATE).
    5. Cache results in Redis.
    6. Return sorted list of match dicts.

    Args:
        buyer_id: UUID of the user (not the buyer_profile.id).
        session: Async SQLAlchemy session.

    Returns:
        List of match dicts sorted by score descending.
    """
    # Get buyer profile
    result = await session.execute(
        select(BuyerProfile).where(BuyerProfile.user_id == buyer_id)
    )
    buyer = result.scalar_one_or_none()
    if not buyer:
        log.warning("compute_all_matches_no_buyer_profile", user_id=str(buyer_id))
        return []

    # Get all published/active properties
    result = await session.execute(
        select(Property).where(
            Property.is_active == True,
            Property.status == PropertyStatus.ACTIVE.value,
        )
    )
    properties = result.scalars().all()

    match_records: list[Match] = []
    match_dicts: list[dict] = []

    for prop in properties:
        score_data = compute_match(buyer, prop)
        match = Match(
            buyer_id=buyer.id,
            property_id=prop.id,
            score=score_data["total"],
            score_breakdown=score_data["breakdown"],
            computed_at=datetime.now(timezone.utc),
        )
        session.add(match)
        match_records.append(match)
        match_dicts.append(
            {
                "id": match.id,
                "property_id": prop.id,
                "score": score_data["total"],
                "score_breakdown": score_data["breakdown"],
                "computed_at": match.computed_at.isoformat(),
                "property": prop,
            }
        )

    # Flush all upserts (ON CONFLICT UPDATE is handled by the DB constraint)
    await session.flush()

    # Invalidate stale cache first, then cache new results
    await invalidate_match_cache(buyer.id)
    sorted_matches = sorted(match_dicts, key=lambda m: m["score"], reverse=True)
    await cache_matches(buyer.id, sorted_matches)

    log.info(
        "matches_computed",
        buyer_id=str(buyer_id),
        property_count=len(properties),
        match_count=len(match_records),
    )
    return sorted_matches


async def get_paginated_matches(
    buyer_id: uuid.UUID,
    session: AsyncSession,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Match], int]:
    """Get paginated match records for a buyer, sorted by score desc.

    Returns (matches, total_count).
    """
    # Get buyer profile
    result = await session.execute(
        select(BuyerProfile).where(BuyerProfile.user_id == buyer_id)
    )
    buyer = result.scalar_one_or_none()
    if not buyer:
        return [], 0

    offset = (page - 1) * limit

    # Get total
    total_result = await session.execute(
        select(func.count(Match.id)).where(Match.buyer_id == buyer.id)
    )
    total = total_result.scalar() or 0

    # Get paginated matches with property
    result = await session.execute(
        select(Match)
        .options(selectinload(Match.property))
        .where(Match.buyer_id == buyer.id)
        .order_by(Match.score.desc())
        .offset(offset)
        .limit(limit)
    )
    matches = result.scalars().unique().all()

    return list(matches), int(total)


# ── Cache helpers (imported from redis_client) ──────────────────────────────────


async def get_matches_from_cache(buyer_id: uuid.UUID) -> list[dict] | None:
    """Get cached matches from Redis if available."""
    return await get_cached_matches(buyer_id)
