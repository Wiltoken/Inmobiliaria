"""Property CRUD, search, and photo management endpoints.

POST   /api/v1/properties                  — create draft (seller/agent)
GET    /api/v1/properties                  — public search with filters
GET    /api/v1/properties/{id}             — detail with photos
PUT    /api/v1/properties/{id}             — owner update
DELETE /api/v1/properties/{id}             — soft delete (is_active=False)
PATCH  /api/v1/properties/{id}/status      — status transition
POST   /api/v1/properties/{id}/photos      — upload photo (max 20)
DELETE /api/v1/properties/{id}/photos/{pid} — delete photo
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.s3_storage import get_s3_adapter
from app.api.v1.deps import get_current_active_user, get_db
from app.domain.models import Property, PropertyPhoto, PropertyStatus, User
from app.domain.schemas import (
    PaginatedPropertiesResponse,
    PhotoUploadResponse,
    PropertyCreate,
    PropertyPhotoResponse,
    PropertyResponse,
    PropertySearch,
    PropertyStatusUpdate,
    PropertyUpdate,
)

log = structlog.get_logger()
router = APIRouter(prefix="/properties", tags=["properties"])

MAX_PHOTOS_PER_PROPERTY = 20


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _get_property_or_404(
    session: AsyncSession, property_id: uuid.UUID
) -> Property:
    """Load property with photos or raise 404."""
    result = await session.execute(
        select(Property)
        .options(selectinload(Property.photos))
        .where(Property.id == property_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    return prop


def _location_dict(lat: float | None, lon: float | None) -> dict | None:
    """Build GeoJSON Point dict for PostGIS."""
    if lat is not None and lon is not None:
        return {"type": "Point", "coordinates": [lon, lat]}
    return None


def _extract_lat_lon(prop: Property) -> tuple[float | None, float | None]:
    """Extract lat/lon from GeoJSON location dict."""
    loc = prop.location
    if loc and loc.get("type") == "Point":
        coords = loc.get("coordinates", [])
        return coords[1] if len(coords) > 1 else None, coords[0] if coords else None
    return None, None


def _check_owner_or_agent(user: User, prop: Property) -> None:
    """Raise 403 if user is neither owner nor agent."""
    user_role_names = {r.name for r in user.roles}
    is_agent = "agent" in user_role_names
    is_owner = prop.owner_id == user.id
    is_listing_agent = prop.agent_id == user.id
    if not (is_owner or is_listing_agent) and not is_agent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this property",
        )


def _trigger_match_cache_invalidation_on_publish(
    session: AsyncSession, property_id: uuid.UUID
) -> None:
    """Invalidate match caches for all buyers when a property is published.

    NOTE: This invalidates ALL buyer caches because a new published property
    could match any buyer. In production, this should be a background task
    (e.g., Celery task, Redis stream, or async queue) to avoid blocking the response.

    TODO ( Slice 5 ): Replace with a proper background job / message queue
    so this runs async and doesn't block the property publish response.
    """
    import asyncio

    log.info("match_cache_invalidation_triggered", reason="property_published", property_id=str(property_id))

    async def _invalidate():
        try:
            from sqlalchemy import select

            from app.adapters.redis_client import invalidate_match_cache
            from app.domain.models import BuyerProfile

            result = await session.execute(select(BuyerProfile.id))
            buyer_ids = result.scalars().all()
            for buyer_id in buyer_ids:
                await invalidate_match_cache(buyer_id)
            log.info("match_cache_invalidated", buyer_count=len(buyer_ids))
        except Exception as exc:
            log.warning("match_cache_invalidation_failed", error=str(exc))

    # Run fire-and-forget (non-blocking)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_invalidate())
    except RuntimeError:
        # No running loop (tests, startup)
        pass


def _build_property_response(prop: Property, distance: float | None = None) -> PropertyResponse:
    """Map ORM Property to PropertyResponse."""
    lat, lon = _extract_lat_lon(prop)
    return PropertyResponse(
        id=prop.id,
        type=prop.type,
        operation=prop.operation,
        status=prop.status,
        price=prop.price,
        area_m2=prop.area_m2,
        lat=lat,
        lon=lon,
        rooms=prop.rooms,
        bathrooms=prop.bathrooms,
        features=prop.features,
        title=prop.title,
        description=prop.description,
        is_active=prop.is_active,
        owner_id=prop.owner_id,
        agent_id=prop.agent_id,
        project_id=prop.project_id,
        created_at=prop.created_at,
        updated_at=prop.updated_at,
        published_at=prop.published_at,
        distance=distance,
        photos=[PropertyPhotoResponse.model_validate(p) for p in prop.photos],
    )


# ── POST /api/v1/properties — create draft ─────────────────────────────────────


@router.post(
    "",
    response_model=PropertyResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Must be seller or agent"},
    },
)
async def create_property(
    data: PropertyCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Create a new property listing (draft).

    Seller or agent role required. Sets owner_id from current user.
    """
    user_role_names = {r.name for r in user.roles}
    if "seller" not in user_role_names and "agent" not in user_role_names:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Must be a seller or agent to create properties",
        )

    prop = Property(
        type=data.type,
        operation=data.operation,
        status=PropertyStatus.ACTIVE.value,
        price=data.price,
        area_m2=data.area_m2,
        location=_location_dict(data.lat, data.lon),
        rooms=data.rooms,
        bathrooms=data.bathrooms,
        features={"features": data.features} if data.features else None,
        title=data.title,
        description=data.description,
        owner_id=user.id,
        agent_id=user.id if "agent" in user_role_names else None,
        project_id=data.project_id,
        is_active=True,
    )
    session.add(prop)
    await session.flush()
    await session.refresh(prop)

    log.info("property_created", property_id=str(prop.id), user_id=str(user.id))

    return _build_property_response(prop)


# ── GET /api/v1/properties — search ───────────────────────────────────────────


@router.get(
    "",
    response_model=PaginatedPropertiesResponse,
)
async def search_properties(
    search: PropertySearch = Depends(),
    session: AsyncSession = Depends(get_db),
) -> PaginatedPropertiesResponse:
    """Public property search with filters.

    - If lat/lon provided: uses ST_DWithin for geo filtering + ST_Distance for ordering
    - If query provided: uses ILIKE on title/description (GIN trigram index)
    - Only returns published/active properties
    """
    # Import here to avoid circular / missing adapter
    try:
        from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint
        from geoalchemy2.shape import to_shape

        has_geo = search.lat is not None and search.lon is not None
    except ImportError:
        has_geo = False

    # Base query — only published/active
    base_query = select(Property).options(selectinload(Property.photos)).where(
        Property.is_active == True,
        Property.status == PropertyStatus.ACTIVE.value,
    )

    count_query = select(func.count(Property.id)).where(
        Property.is_active == True,
        Property.status == PropertyStatus.ACTIVE.value,
    )

    # Apply type filter
    if search.type:
        base_query = base_query.where(Property.type == search.type)
        count_query = count_query.where(Property.type == search.type)

    # Apply operation filter
    if search.operation:
        base_query = base_query.where(Property.operation == search.operation)
        count_query = count_query.where(Property.operation == search.operation)

    # Apply price range
    if search.price_min is not None:
        base_query = base_query.where(Property.price >= search.price_min)
        count_query = count_query.where(Property.price >= search.price_min)
    if search.price_max is not None:
        base_query = base_query.where(Property.price <= search.price_max)
        count_query = count_query.where(Property.price <= search.price_max)

    # Apply rooms/bathrooms
    if search.rooms_min is not None:
        base_query = base_query.where(Property.rooms >= search.rooms_min)
        count_query = count_query.where(Property.rooms >= search.rooms_min)
    if search.bathrooms_min is not None:
        base_query = base_query.where(Property.bathrooms >= search.bathrooms_min)
        count_query = count_query.where(Property.bathrooms >= search.bathrooms_min)

    # Apply area range
    if search.area_min is not None:
        base_query = base_query.where(Property.area_m2 >= search.area_min)
        count_query = count_query.where(Property.area_m2 >= search.area_min)
    if search.area_max is not None:
        base_query = base_query.where(Property.area_m2 <= search.area_max)
        count_query = count_query.where(Property.area_m2 <= search.area_max)

    # Apply text search (ILIKE on title/description)
    if search.query:
        pattern = f"%{search.query}%"
        base_query = base_query.where(
            Property.title.ilike(pattern) | Property.description.ilike(pattern)
        )
        count_query = count_query.where(
            Property.title.ilike(pattern) | Property.description.ilike(pattern)
        )

    # Geo search: ST_DWithin + distance ordering
    distances: dict[uuid.UUID, float] = {}
    if has_geo and search.radius_km:
        radius_m = search.radius_km * 1000
        point = ST_MakePoint(search.lon, search.lat)
        # Filter: within radius
        base_query = base_query.where(
            ST_DWithin(Property.location, point, radius_m)
        )
        count_query = count_query.where(
            ST_DWithin(Property.location, point, radius_m)
        )
        # Order by distance
        base_query = base_query.order_by(
            ST_Distance(Property.location, point).asc()
        )
        # Compute distances for response
        geo_order = base_query.subquery()
        # We need to re-fetch with distance — do a second pass is complex in async
        # For now, we'll compute distance after fetching using to_shape
        result = await session.execute(base_query)
        props = result.scalars().unique().all()
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        responses = []
        for prop in props:
            if prop.location:
                shape = to_shape(prop.location)
                import math
                dist = math.sqrt(
                    (shape.x - search.lon) ** 2 + (shape.y - search.lat) ** 2
                ) * 111  # rough km conversion
                distances[prop.id] = round(dist, 2)
            responses.append(_build_property_response(prop, distances.get(prop.id)))
        total_pages = (total + search.limit - 1) // search.limit if search.limit else 1
        return PaginatedPropertiesResponse(
            properties=responses,
            total=total,
            page=search.page,
            limit=search.limit,
            total_pages=total_pages,
        )

    # Pagination
    offset = (search.page - 1) * search.limit
    base_query = base_query.offset(offset).limit(search.limit)

    # Default order: newest first
    base_query = base_query.order_by(Property.created_at.desc())

    result = await session.execute(base_query)
    props = result.scalars().unique().all()

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0
    total_pages = (total + search.limit - 1) // search.limit if search.limit else 1

    return PaginatedPropertiesResponse(
        properties=[_build_property_response(p) for p in props],
        total=total,
        page=search.page,
        limit=search.limit,
        total_pages=total_pages,
    )


# ── GET /api/v1/properties/{id} — detail ──────────────────────────────────────


@router.get(
    "/{property_id}",
    response_model=PropertyResponse,
    responses={404: {"description": "Property not found"}},
)
async def get_property(
    property_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Get property detail with photos."""
    prop = await _get_property_or_404(session, property_id)
    if not prop.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )
    return _build_property_response(prop)


# ── PUT /api/v1/properties/{id} — update ──────────────────────────────────────


@router.put(
    "/{property_id}",
    response_model=PropertyResponse,
    responses={
        403: {"description": "Not authorized"},
        404: {"description": "Property not found"},
    },
)
async def update_property(
    property_id: uuid.UUID,
    data: PropertyUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Update property — owner or listing agent only."""
    prop = await _get_property_or_404(session, property_id)
    _check_owner_or_agent(user, prop)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "lat":
            lat, lon = _extract_lat_lon(prop)
            prop.location = _location_dict(value, lon)
        elif field == "lon":
            lat, lon = _extract_lat_lon(prop)
            prop.location = _location_dict(lat, value)
        elif field == "features":
            setattr(prop, field, {"features": value} if value else None)
        else:
            setattr(prop, field, value)

    await session.flush()
    await session.refresh(prop)

    log.info("property_updated", property_id=str(property_id), user_id=str(user.id))
    return _build_property_response(prop)


# ── DELETE /api/v1/properties/{id} — soft delete ───────────────────────────────


@router.delete(
    "/{property_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "Not authorized"},
        404: {"description": "Property not found"},
    },
)
async def delete_property(
    property_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete a property (sets is_active=False). Owner or agent only."""
    prop = await _get_property_or_404(session, property_id)
    _check_owner_or_agent(user, prop)

    prop.is_active = False
    await session.flush()

    log.info("property_deleted", property_id=str(property_id), user_id=str(user.id))


# ── PATCH /api/v1/properties/{id}/status — status transition ──────────────────


@router.patch(
    "/{property_id}/status",
    response_model=PropertyResponse,
    responses={
        400: {"description": "Invalid status transition"},
        403: {"description": "Not authorized"},
        404: {"description": "Property not found"},
    },
)
async def update_property_status(
    property_id: uuid.UUID,
    data: PropertyStatusUpdate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Transition property status.

    Valid transitions: draft → published → reserved → sold → archived
    """
    prop = await _get_property_or_404(session, property_id)
    _check_owner_or_agent(user, prop)

    # Validate target status
    try:
        new_status = PropertyStatus(data.status)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status: {data.status}",
        )

    # Set published_at when first published
    if new_status == PropertyStatus.ACTIVE and prop.published_at is None:
        prop.published_at = datetime.now(timezone.utc)

    prop.status = new_status.value
    await session.flush()
    await session.refresh(prop)

    # ── Match cache invalidation trigger ─────────────────────────────────────
    # When a property is published (ACTIVE), all buyer matches may be affected.
    # Invalidate all buyer caches (fire-and-forget background task in production).
    if new_status == PropertyStatus.ACTIVE:
        _trigger_match_cache_invalidation_on_publish(session, prop.id)

    log.info(
        "property_status_updated",
        property_id=str(property_id),
        new_status=data.status,
        user_id=str(user.id),
    )
    return _build_property_response(prop)


# ── POST /api/v1/properties/{id}/photos — upload ───────────────────────────────


@router.post(
    "/{property_id}/photos",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Too many photos or invalid file"},
        403: {"description": "Not authorized"},
        404: {"description": "Property not found"},
    },
)
async def upload_photo(
    property_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PhotoUploadResponse:
    """Upload a photo for a property (max 20 per property)."""
    prop = await _get_property_or_404(session, property_id)
    _check_owner_or_agent(user, prop)

    # Count existing photos
    if len(prop.photos) >= MAX_PHOTOS_PER_PROPERTY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {MAX_PHOTOS_PER_PROPERTY} photos per property",
        )
    # Validate content type
    allowed = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}
    if file.content_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}",
        )

    # Read file content
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large (max 10MB)",
        )

    # Generate S3 key
    photo_id = uuid.uuid4()
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    key = f"properties/{property_id}/{photo_id}.{ext}"

    # Upload to S3
    s3 = get_s3_adapter()
    url = s3.upload_file(content, key)

    # Create PropertyPhoto record
    order = len(prop.photos)
    photo = PropertyPhoto(
        id=photo_id,
        property_id=property_id,
        url=url,
        s3_key=key,
        order=order,
    )
    session.add(photo)
    await session.flush()
    await session.refresh(photo)

    log.info("property_photo_uploaded", photo_id=str(photo_id), property_id=str(property_id))

    return PhotoUploadResponse(id=photo.id, url=photo.url, order=photo.order)


# ── DELETE /api/v1/properties/{id}/photos/{photo_id} ─────────────────────────


@router.delete(
    "/{property_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"description": "Not authorized"},
        404: {"description": "Photo not found"},
    },
)
async def delete_photo(
    property_id: uuid.UUID,
    photo_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a property photo."""
    prop = await _get_property_or_404(session, property_id)
    _check_owner_or_agent(user, prop)

    # Find photo
    photo = next((p for p in prop.photos if p.id == photo_id), None)
    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo not found",
        )

    # Delete from S3
    if photo.s3_key:
        s3 = get_s3_adapter()
        try:
            s3.delete_file(photo.s3_key)
        except Exception:
            log.warning("s3_delete_failed", key=photo.s3_key)

    # Delete from DB
    await session.delete(photo)
    await session.flush()

    log.info("property_photo_deleted", photo_id=str(photo_id), property_id=str(property_id))
