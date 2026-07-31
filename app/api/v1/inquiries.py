"""Inquiry management endpoints.

POST   /api/v1/inquiries              — buyer creates inquiry
GET    /api/v1/inquiries              — user sees sent + received, filterable by status
PATCH  /api/v1/inquiries/{id}         — owner responds (accept/decline/request_more_info)
GET    /api/v1/inquiries/sent         — buyer sees sent inquiries
GET    /api/v1/inquiries/received     — seller/agent sees received inquiries
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_active_user, get_db
from app.domain.models import Inquiry, InquiryStatus, Property, PropertyStatus, ResponseAction, User
from app.domain.schemas import InquiryAction, InquiryCreate, InquiryListResponse, InquiryResponse

log = structlog.get_logger()
router = APIRouter(prefix="/inquiries", tags=["inquiries"])


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _get_inquiry_or_404(
    session: AsyncSession, inquiry_id: uuid.UUID
) -> Inquiry:
    """Load inquiry or raise 404."""
    result = await session.execute(
        select(Inquiry).where(Inquiry.id == inquiry_id)
    )
    inquiry = result.scalar_one_or_none()
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inquiry not found",
        )
    return inquiry


def _get_user_role(user: User) -> str | None:
    """Return the first role name for the user, or None."""
    if not user.roles:
        return None
    return user.roles[0].name


# ── POST /api/v1/inquiries ────────────────────────────────────────────────────


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=InquiryResponse,
    responses={
        401: {"description": "Not authenticated"},
        400: {"description": "Cannot inquire about own property or unpublished property"},
    },
)
async def create_inquiry(
    data: InquiryCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> InquiryResponse:
    """Buyer creates an inquiry about a published property.

    Validation:
    - Property must exist and be published (status=active)
    - User cannot inquire about their own property
    """
    # Load property
    result = await session.execute(
        select(Property).where(Property.id == data.property_id)
    )
    prop = result.scalar_one_or_none()
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
    if prop.owner_id == user.id or prop.agent_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot inquire about your own property",
        )

    # Determine recipient
    to_user_id = prop.owner_id or prop.agent_id
    if not to_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Property has no owner or agent",
        )

    inquiry = Inquiry(
        from_user_id=user.id,
        to_user_id=to_user_id,
        property_id=data.property_id,
        message=data.message,
        contact_preference=data.contact_preference,
        status=InquiryStatus.PENDING,
    )
    session.add(inquiry)
    await session.flush()
    await session.refresh(inquiry)

    log.info("inquiry_created", inquiry_id=str(inquiry.id), from_user=str(user.id))
    return InquiryResponse.model_validate(inquiry)


# ── GET /api/v1/inquiries ─────────────────────────────────────────────────────


@router.get(
    "",
    response_model=InquiryListResponse,
    responses={401: {"description": "Not authenticated"}},
)
async def list_inquiries(
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> InquiryListResponse:
    """List inquiries sent and received by the current user, optionally filtered by status."""
    conditions = or_(
        Inquiry.from_user_id == user.id,
        Inquiry.to_user_id == user.id,
    )

    if status_filter:
        conditions = and_(conditions, Inquiry.status == status_filter)

    result = await session.execute(
        select(Inquiry)
        .where(conditions)
        .order_by(Inquiry.created_at.desc())
    )
    inquiries = result.scalars().all()

    return InquiryListResponse(
        inquiries=[InquiryResponse.model_validate(i) for i in inquiries],
        total=len(inquiries),
    )


# ── GET /api/v1/inquiries/sent ───────────────────────────────────────────────


@router.get(
    "/sent",
    response_model=InquiryListResponse,
    responses={401: {"description": "Not authenticated"}},
)
async def list_sent_inquiries(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> InquiryListResponse:
    """Buyer sees all inquiries they have sent."""
    result = await session.execute(
        select(Inquiry)
        .where(Inquiry.from_user_id == user.id)
        .order_by(Inquiry.created_at.desc())
    )
    inquiries = result.scalars().all()

    return InquiryListResponse(
        inquiries=[InquiryResponse.model_validate(i) for i in inquiries],
        total=len(inquiries),
    )


# ── GET /api/v1/inquiries/received ───────────────────────────────────────────


@router.get(
    "/received",
    response_model=InquiryListResponse,
    responses={401: {"description": "Not authenticated"}},
)
async def list_received_inquiries(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> InquiryListResponse:
    """Seller or agent sees all inquiries they have received."""
    role = _get_user_role(user)
    if role not in ("seller", "agent"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only sellers and agents can view received inquiries",
        )

    result = await session.execute(
        select(Inquiry)
        .where(Inquiry.to_user_id == user.id)
        .order_by(Inquiry.created_at.desc())
    )
    inquiries = result.scalars().all()

    return InquiryListResponse(
        inquiries=[InquiryResponse.model_validate(i) for i in inquiries],
        total=len(inquiries),
    )


# ── PATCH /api/v1/inquiries/{id} ─────────────────────────────────────────────


@router.patch(
    "/{inquiry_id}",
    response_model=InquiryResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not the inquiry recipient"},
        404: {"description": "Inquiry not found"},
    },
)
async def respond_to_inquiry(
    inquiry_id: uuid.UUID,
    data: InquiryAction,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> InquiryResponse:
    """Owner (seller/agent) responds to an inquiry.

    Actions:
    - accept: marks as interested
    - decline: marks as not_interested
    - request_more_info: marks as replied
    """
    inquiry = await _get_inquiry_or_404(session, inquiry_id)

    if inquiry.to_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only respond to inquiries you received",
        )

    # Map action to status
    action_to_status = {
        "accept": InquiryStatus.INTERESTED,
        "decline": InquiryStatus.NOT_INTERESTED,
        "request_more_info": InquiryStatus.REPLIED,
    }

    if data.action not in action_to_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Use: accept, decline, request_more_info",
        )

    inquiry.status = action_to_status[data.action]
    inquiry.response_message = data.response_message
    inquiry.response_action = ResponseAction.NO_ACTION

    await session.flush()
    await session.refresh(inquiry)

    log.info(
        "inquiry_responded",
        inquiry_id=str(inquiry_id),
        action=data.action,
        user_id=str(user.id),
    )
    return InquiryResponse.model_validate(inquiry)
