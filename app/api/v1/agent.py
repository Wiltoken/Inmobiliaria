"""Agent dashboard endpoints.

GET  /api/v1/agent/dashboard/stats        — overview statistics
GET  /api/v1/agent/dashboard/listings    — agent's properties with stats
GET  /api/v1/agent/dashboard/clients     — assigned buyers list
GET  /api/v1/agent/dashboard/clients/{buyer_id}/matches — client's match results
POST /api/v1/agent/inquiries             — create inquiry on behalf of assigned buyer

All endpoints require agent role via require_role("agent").
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_db, require_role
from app.domain.models import (
    BuyerProfile,
    Inquiry,
    InquiryStatus,
    Match,
    Property,
    PropertyStatus,
    User,
)
from app.domain.schemas import InquiryCreate, InquiryResponse

log = structlog.get_logger()
router = APIRouter(prefix="/agent", tags=["agent"])


# ── Dashboard stats ─────────────────────────────────────────────────────────────


class AgentDashboardStats(BaseModel):
    """GET /api/v1/agent/dashboard/stats response."""

    model_config = ConfigDict(from_attributes=True)

    active_listings: int
    pending_inquiries: int
    recent_matches_7d: int
    total_clients: int


@router.get(
    "/dashboard/stats",
    response_model=AgentDashboardStats,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not an agent"},
    },
)
async def agent_dashboard_stats(
    user: User = Depends(require_role("agent")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> AgentDashboardStats:
    """Agent dashboard overview: active listings, pending inquiries, recent matches, total clients.

    Requires agent role.
    """
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    # Active listings: properties where agent_id = current user and is_active=True
    active_result = await session.execute(
        select(func.count(Property.id)).where(
            Property.agent_id == user.id,
            Property.is_active == True,
            Property.status == PropertyStatus.ACTIVE.value,
        )
    )
    active_listings = active_result.scalar_one() or 0

    # Pending inquiries: inquiries sent to this agent (to_user_id = user.id) with status pending
    pending_result = await session.execute(
        select(func.count(Inquiry.id)).where(
            Inquiry.to_user_id == user.id,
            Inquiry.status == InquiryStatus.PENDING.value,
        )
    )
    pending_inquiries = pending_result.scalar_one() or 0

    # Recent matches (last 7 days): agent's clients' matches computed in last 7 days
    # Matches are linked to BuyerProfile which has a user_id. We count matches whose
    # buyer is assigned to this agent (via buyer.user_id == user.id)
    recent_matches_result = await session.execute(
        select(func.count(Match.id)).where(
            Match.computed_at >= seven_days_ago
        ).join(
            BuyerProfile, Match.buyer_id == BuyerProfile.id
        ).where(
            BuyerProfile.user_id == user.id
        )
    )
    recent_matches_7d = recent_matches_result.scalar_one() or 0

    # Total clients: distinct buyers assigned to this agent
    clients_result = await session.execute(
        select(func.count(BuyerProfile.id)).where(
            BuyerProfile.user_id == user.id
        )
    )
    total_clients = clients_result.scalar_one() or 0

    return AgentDashboardStats(
        active_listings=active_listings,
        pending_inquiries=pending_inquiries,
        recent_matches_7d=recent_matches_7d,
        total_clients=total_clients,
    )


# ── Dashboard listings ───────────────────────────────────────────────────────────


class AgentListingItem(BaseModel):
    """Single property item in agent listings response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    type: str
    operation: str
    status: str
    price: float
    area_m2: float | None
    rooms: int | None
    bathrooms: int | None
    created_at: datetime
    published_at: datetime | None
    inquiry_count: int
    favorite_count: int


class AgentListingsResponse(BaseModel):
    """GET /api/v1/agent/dashboard/listings response."""

    listings: list[AgentListingItem]
    total: int


@router.get(
    "/dashboard/listings",
    response_model=AgentListingsResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not an agent"},
    },
)
async def agent_dashboard_listings(
    request: Request,
    status_filter: str | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user: User = Depends(require_role("agent")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> AgentListingsResponse:
    """Agent's properties with inquiry and favorite counts, filterable by status.

    Requires agent role.
    """
    # Base query: agent's properties
    base_query = select(Property).where(Property.agent_id == user.id)
    count_query = select(func.count(Property.id)).where(Property.agent_id == user.id)

    if status_filter is not None:
        base_query = base_query.where(Property.status == status_filter)
        count_query = count_query.where(Property.status == status_filter)

    # Order by newest first
    base_query = base_query.order_by(Property.created_at.desc())

    # Get total
    total_result = await session.execute(count_query)
    total = total_result.scalar_one() or 0

    # Paginate
    offset = (page - 1) * page_size
    paginated_query = base_query.offset(offset).limit(page_size)
    result = await session.execute(paginated_query)
    properties = result.scalars().all()

    # Build response with counts
    listings = []
    for prop in properties:
        # Count inquiries for this property
        inquiry_result = await session.execute(
            select(func.count(Inquiry.id)).where(Inquiry.property_id == prop.id)
        )
        inquiry_count = inquiry_result.scalar_one() or 0

        # Count favorites
        from app.domain.models import Favorite
        fav_result = await session.execute(
            select(func.count(Favorite.id)).where(Favorite.property_id == prop.id)
        )
        favorite_count = fav_result.scalar_one() or 0

        listings.append(
            AgentListingItem(
                id=prop.id,
                title=prop.title,
                type=prop.type,
                operation=prop.operation,
                status=prop.status,
                price=prop.price,
                area_m2=prop.area_m2,
                rooms=prop.rooms,
                bathrooms=prop.bathrooms,
                created_at=prop.created_at,
                published_at=prop.published_at,
                inquiry_count=inquiry_count,
                favorite_count=favorite_count,
            )
        )

    return AgentListingsResponse(listings=listings, total=total)


# ── Dashboard clients ─────────────────────────────────────────────────────────────


class AgentClientItem(BaseModel):
    """Single buyer client in agent's client list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID  # BuyerProfile.id
    user_id: uuid.UUID
    username: str
    email: str
    budget_min: float | None
    budget_max: float | None
    preferred_property_types: list[str] | None
    match_count: int
    created_at: datetime


class AgentClientsResponse(BaseModel):
    """GET /api/v1/agent/dashboard/clients response."""

    clients: list[AgentClientItem]
    total: int


@router.get(
    "/dashboard/clients",
    response_model=AgentClientsResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not an agent"},
    },
)
async def agent_dashboard_clients(
    user: User = Depends(require_role("agent")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> AgentClientsResponse:
    """List of buyers assigned to this agent.

    Requires agent role.
    """
    # Find buyer's profiles where the buyer's user_id matches the agent (assigned buyer relationship)
    # For MVP: any BuyerProfile whose user has interacted with agent-owned properties.
    # We use a simpler approach: buyers who have matches computed for the agent's properties.
    result = await session.execute(
        select(BuyerProfile)
        .options(selectinload(BuyerProfile.user))
        .join(Match, Match.buyer_id == BuyerProfile.id)
        .join(Property, Match.property_id == Property.id)
        .where(Property.agent_id == user.id)
        .distinct()
        .order_by(BuyerProfile.created_at.desc())
    )
    buyer_profiles = result.scalars().unique().all()

    clients = []
    for buyer in buyer_profiles:
        # Count matches for this buyer
        match_result = await session.execute(
            select(func.count(Match.id)).where(Match.buyer_id == buyer.id)
        )
        match_count = match_result.scalar_one() or 0

        username = buyer.user.username if buyer.user else "unknown"
        email = buyer.user.email if buyer.user else "unknown"

        clients.append(
            AgentClientItem(
                id=buyer.id,
                user_id=buyer.user_id,
                username=username,
                email=email,
                budget_min=buyer.budget_min,
                budget_max=buyer.budget_max,
                preferred_property_types=buyer.preferred_property_types,
                match_count=match_count,
                created_at=buyer.created_at,
            )
        )

    return AgentClientsResponse(clients=clients, total=len(clients))


# ── Dashboard client matches ─────────────────────────────────────────────────────


class AgentClientMatchItem(BaseModel):
    """Single match result for a client's match list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    score: float
    score_breakdown: dict | None
    computed_at: datetime
    property_title: str
    property_price: float
    property_type: str


class AgentClientMatchesResponse(BaseModel):
    """GET /api/v1/agent/dashboard/clients/{buyer_id}/matches response."""

    matches: list[AgentClientMatchItem]
    total: int


@router.get(
    "/dashboard/clients/{buyer_id}/matches",
    response_model=AgentClientMatchesResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not an agent or buyer not assigned"},
        404: {"description": "Buyer profile not found"},
    },
)
async def agent_client_matches(
    buyer_id: uuid.UUID,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user: User = Depends(require_role("agent")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> AgentClientMatchesResponse:
    """List match results for an assigned buyer.

    Requires agent role and buyer must be assigned to this agent.
    """
    # Verify buyer profile exists
    buyer_result = await session.execute(
        select(BuyerProfile).where(BuyerProfile.id == buyer_id)
    )
    buyer = buyer_result.scalar_one_or_none()
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Buyer profile not found",
        )

    # Verify this agent has properties that this buyer has matches for (assignment check)
    assignment_check = await session.execute(
        select(Match.id)
        .join(Property, Match.property_id == Property.id)
        .where(Match.buyer_id == buyer_id, Property.agent_id == user.id)
        .limit(1)
    )
    if assignment_check.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This buyer is not assigned to you",
        )

    # Count total matches
    total_result = await session.execute(
        select(func.count(Match.id)).where(Match.buyer_id == buyer_id)
    )
    total = total_result.scalar_one() or 0

    # Paginate matches
    offset = (page - 1) * page_size
    matches_result = await session.execute(
        select(Match)
        .options(selectinload(Match.property))
        .where(Match.buyer_id == buyer_id)
        .order_by(Match.score.desc())
        .offset(offset)
        .limit(page_size)
    )
    matches = matches_result.scalars().unique().all()

    items = []
    for match in matches:
        prop = match.property
        items.append(
            AgentClientMatchItem(
                id=match.id,
                property_id=match.property_id,
                score=match.score,
                score_breakdown=match.score_breakdown,
                computed_at=match.computed_at,
                property_title=prop.title if prop else "unknown",
                property_price=prop.price if prop else 0.0,
                property_type=prop.type if prop else "unknown",
            )
        )

    return AgentClientMatchesResponse(matches=items, total=total)


# ── Agent inquiries ──────────────────────────────────────────────────────────────


@router.post(
    "/inquiries",
    status_code=status.HTTP_201_CREATED,
    response_model=InquiryResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not an agent or buyer not assigned"},
        404: {"description": "Property or buyer not found"},
    },
)
async def agent_create_inquiry(
    data: InquiryCreate,
    buyer_id: Annotated[uuid.UUID, Query(description="Buyer profile ID to act on behalf of")],
    user: User = Depends(require_role("agent")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> InquiryResponse:
    """Agent creates an inquiry on behalf of an assigned buyer.

    Requires agent role. The buyer must be assigned to this agent (has matches
    for the agent's properties).
    """
    # Load buyer profile
    buyer_result = await session.execute(
        select(BuyerProfile).where(BuyerProfile.id == buyer_id)
    )
    buyer = buyer_result.scalar_one_or_none()
    if not buyer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Buyer profile not found",
        )

    # Verify assignment: buyer must have matches for this agent's properties
    assignment_check = await session.execute(
        select(Match.id)
        .join(Property, Match.property_id == Property.id)
        .where(Match.buyer_id == buyer_id, Property.agent_id == user.id)
        .limit(1)
    )
    if assignment_check.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This buyer is not assigned to you",
        )

    # Load property
    prop_result = await session.execute(
        select(Property).where(Property.id == data.property_id)
    )
    prop = prop_result.scalar_one_or_none()
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    if prop.status != PropertyStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only inquire about published properties",
        )

    # Determine recipient
    to_user_id = prop.owner_id or prop.agent_id
    if not to_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property has no owner or agent",
        )

    inquiry = Inquiry(
        from_user_id=buyer.user_id,
        to_user_id=to_user_id,
        property_id=data.property_id,
        message=data.message,
        contact_preference=data.contact_preference,
        status=InquiryStatus.PENDING,
    )
    session.add(inquiry)
    await session.flush()
    await session.refresh(inquiry)

    log.info(
        "agent_inquiry_created",
        inquiry_id=str(inquiry.id),
        agent_id=str(user.id),
        buyer_id=str(buyer_id),
        property_id=str(data.property_id),
    )
    return InquiryResponse.model_validate(inquiry)
