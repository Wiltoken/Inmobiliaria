"""Admin endpoints: user management, audit log queries, compliance reports, and property moderation.

All endpoints require admin or super_admin role.

GET  /api/v1/admin/users
GET  /api/v1/admin/audit-logs
GET  /api/v1/admin/compliance-report
GET  /api/v1/admin/users  (extended with role filter)
PATCH /api/v1/admin/properties/{id}/approve
PATCH /api/v1/admin/properties/{id}/reject
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_db, require_role
from app.config import settings
from app.domain.models import (
    AuditLog,
    LoginAttempt,
    Property,
    PropertyStatus,
    Role,
    User,
    UserAction,
)
from app.domain.schemas import (
    AuditLogEntry,
    ComplianceReport,
    ErrorResponse,
    PaginatedAuditLogsResponse,
    PaginatedUsersResponse,
    PropertyResponse,
    UserProfile,
)

log = structlog.get_logger()
router = APIRouter(prefix="/admin", tags=["admin"])


async def _paginate(
    session: AsyncSession,
    query,
    page: int,
    page_size: int,
):
    """Apply pagination to a query and return (items, total, total_pages)."""
    total_result = await session.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    paginated_query = query.offset(offset).limit(page_size)
    result = await session.execute(paginated_query)
    items = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return list(items), total, total_pages


# ── GET /api/v1/admin/users ─────────────────────────────────────────────────────


@router.get(
    "/users",
    response_model=PaginatedUsersResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def list_users(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    tenant_id: uuid.UUID | None = None,
    role: str | None = None,
    user: User = Depends(require_role("admin", "super_admin")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> PaginatedUsersResponse:
    """List users with pagination, optional tenant filter, and optional role filter.

    Requires admin or super_admin role.
    """
    # Build base query — join User → Role via secondary
    from sqlalchemy.orm import selectinload

    query = select(User).options(selectinload(User.roles))
    if tenant_id is not None:
        query = query.where(User.tenant_id == tenant_id)

    # Filter by role name if provided
    if role is not None:
        query = query.join(User.roles).where(User.roles.any(Role.name == role))

    query = query.order_by(User.created_at.desc())

    users, total, total_pages = await _paginate(session, query, page, page_size)

    user_profiles = [
        UserProfile(
            id=u.id,
            username=u.username,
            email=u.email,
            tenant_id=u.tenant_id,
            roles=[role.name for role in u.roles],
            is_active=u.is_active,
            is_locked=u.is_locked,
            consent_given_at=u.consent_given_at,
            password_changed_at=u.password_changed_at,
        )
        for u in users
    ]

    # Audit log admin access
    try:
        admin_entry = AuditLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="admin_list_users",
            ip_address=request.client.host if request.client else None,
            details={"page": page, "page_size": page_size, "tenant_id": str(tenant_id) if tenant_id else None, "role": role},
        )
        session.add(admin_entry)
        await session.commit()
    except Exception as exc:
        log.warning("audit_log_write_failed", action="admin_list_users", error=str(exc))

    return PaginatedUsersResponse(
        users=user_profiles,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ── GET /api/v1/admin/audit-logs ───────────────────────────────────────────────


@router.get(
    "/audit-logs",
    response_model=PaginatedAuditLogsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def query_audit_logs(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    tenant_id: uuid.UUID | None = None,
    user: User = Depends(require_role("admin", "super_admin")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> PaginatedAuditLogsResponse:
    """Query audit logs with filters: user_id, action, date_from, date_to, tenant_id.

    Requires admin or super_admin role.
    """
    conditions = []

    if user_id is not None:
        conditions.append(AuditLog.user_id == user_id)
    if action is not None:
        conditions.append(AuditLog.action == action)
    if date_from is not None:
        conditions.append(AuditLog.created_at >= date_from)
    if date_to is not None:
        conditions.append(AuditLog.created_at <= date_to)
    if tenant_id is not None:
        conditions.append(AuditLog.tenant_id == tenant_id)

    query = select(AuditLog)
    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(AuditLog.created_at.desc())

    logs, total, total_pages = await _paginate(session, query, page, page_size)

    log_entries = [
        AuditLogEntry(
            id=log_entry.id,
            user_id=log_entry.user_id,
            tenant_id=log_entry.tenant_id,
            action=log_entry.action,
            ip_address=log_entry.ip_address,
            details=log_entry.details,
            created_at=log_entry.created_at,
        )
        for log_entry in logs
    ]

    return PaginatedAuditLogsResponse(
        audit_logs=log_entries,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ── GET /api/v1/admin/compliance-report ─────────────────────────────────────────


@router.get(
    "/compliance-report",
    response_model=ComplianceReport,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def compliance_report(
    request: Request,
    user: User = Depends(require_role("admin", "super_admin")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> ComplianceReport:
    """Compliance summary report for Colombian Ley 1581/2012.

    Returns:
    - active_users: count of users where is_active=True
    - locked_accounts: count of users where is_locked=True
    - failed_logins_today: count of failed login attempts in the last 24h
    - users_without_consent: users where consent_given_at IS NULL
    - password_expired_count: users whose password has expired

    Requires admin or super_admin role.
    """
    today_start = datetime.now(timezone.utc) - timedelta(hours=24)

    # Active users count
    active_result = await session.execute(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    )
    active_users = active_result.scalar_one()

    # Locked accounts count
    locked_result = await session.execute(
        select(func.count()).select_from(User).where(User.is_locked.is_(True))
    )
    locked_accounts = locked_result.scalar_one()

    # Failed logins today
    failed_result = await session.execute(
        select(func.count()).select_from(LoginAttempt).where(
            and_(
                LoginAttempt.success.is_(False),
                LoginAttempt.attempted_at >= today_start,
            )
        )
    )
    failed_logins_today = failed_result.scalar_one()

    # Users without consent
    no_consent_result = await session.execute(
        select(func.count()).select_from(User).where(User.consent_given_at.is_(None))
    )
    users_without_consent = no_consent_result.scalar_one()

    # Password expired count
    if settings.password_expiry_days > 0:
        expiry_threshold = datetime.now(timezone.utc) - timedelta(days=settings.password_expiry_days)
        expired_result = await session.execute(
            select(func.count()).select_from(User).where(
                and_(
                    User.password_changed_at < expiry_threshold,
                    User.is_active.is_(True),
                )
            )
        )
        password_expired_count = expired_result.scalar_one()
    else:
        password_expired_count = 0

    # Audit log admin access
    try:
        admin_entry = AuditLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="admin_compliance_report",
            ip_address=request.client.host if request.client else None,
            details={
                "active_users": active_users,
                "locked_accounts": locked_accounts,
                "failed_logins_today": failed_logins_today,
                "users_without_consent": users_without_consent,
                "password_expired_count": password_expired_count,
            },
        )
        session.add(admin_entry)
        await session.commit()
    except Exception as exc:
        log.warning("audit_log_write_failed", action="admin_compliance_report", error=str(exc))

    return ComplianceReport(
        active_users=active_users,
        locked_accounts=locked_accounts,
        failed_logins_today=failed_logins_today,
        users_without_consent=users_without_consent,
        password_expired_count=password_expired_count,
    )


# ── PATCH /api/v1/admin/properties/{id}/approve ─────────────────────────────────


@router.patch(
    "/properties/{property_id}/approve",
    response_model=PropertyResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Property not found"},
    },
)
async def approve_property(
    request: Request,
    property_id: uuid.UUID,
    user: User = Depends(require_role("admin", "super_admin")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """Admin approves a property listing and sets published_at.

    Requires admin or super_admin role. Clears any prior rejection reason.
    """
    result = await session.execute(
        select(Property).where(Property.id == property_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    prop.status = PropertyStatus.ACTIVE.value
    prop.published_at = datetime.now(timezone.utc)
    prop.rejection_reason = None
    await session.flush()
    await session.refresh(prop)

    # Audit log
    try:
        admin_entry = AuditLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="admin_property_approve",
            ip_address=request.client.host if request.client else None,
            details={"property_id": str(property_id), "title": prop.title},
        )
        session.add(admin_entry)
        await session.commit()
    except Exception as exc:
        log.warning("audit_log_write_failed", action="admin_property_approve", error=str(exc))

    log.info("property_approved_by_admin", property_id=str(property_id), admin_id=str(user.id))
    return _build_admin_property_response(prop)


# ── PATCH /api/v1/admin/properties/{id}/reject ──────────────────────────────────


class PropertyRejectRequest(BaseModel):
    """PATCH /api/v1/admin/properties/{id}/reject request body."""

    reason: Annotated[str, Field(min_length=1, max_length=1000)]


class PropertyRejectResponse(BaseModel):
    """PATCH /api/v1/admin/properties/{id}/reject response."""

    id: uuid.UUID
    status: str
    rejection_reason: str


@router.patch(
    "/properties/{property_id}/reject",
    response_model=PropertyRejectResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Property not found"},
    },
)
async def reject_property(
    request: Request,
    property_id: uuid.UUID,
    data: PropertyRejectRequest,
    user: User = Depends(require_role("admin", "super_admin")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> PropertyRejectResponse:
    """Admin rejects a property listing with a reason and reverts it to draft.

    Sets rejection_reason on the property and reverts status to pending (draft-like).
    Requires admin or super_admin role.
    """
    result = await session.execute(
        select(Property).where(Property.id == property_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found",
        )

    prop.status = PropertyStatus.PENDING.value
    prop.rejection_reason = data.reason
    await session.flush()
    await session.refresh(prop)

    # Audit log
    try:
        admin_entry = AuditLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="admin_property_reject",
            ip_address=request.client.host if request.client else None,
            details={"property_id": str(property_id), "title": prop.title, "reason": data.reason},
        )
        session.add(admin_entry)
        await session.commit()
    except Exception as exc:
        log.warning("audit_log_write_failed", action="admin_property_reject", error=str(exc))

    log.info("property_rejected_by_admin", property_id=str(property_id), admin_id=str(user.id), reason=data.reason)
    return PropertyRejectResponse(id=prop.id, status=prop.status, rejection_reason=prop.rejection_reason)


# ── Internal helpers ───────────────────────────────────────────────────────────


def _build_admin_property_response(prop: Property) -> PropertyResponse:
    """Map ORM Property to PropertyResponse for admin endpoints."""
    loc = prop.location
    if loc and loc.get("type") == "Point":
        coords = loc.get("coordinates", [])
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None
    else:
        lat, lon = None, None

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
        photos=[],
    )


# ── GET /api/v1/admin/analytics ─────────────────────────────────────────────────


class AnalyticsResponse(BaseModel):
    dau: int = Field(description="Daily active users (unique users today)")
    searches_today: int
    properties_viewed: int
    inquiries_sent: int
    events_over_time: list[dict] = Field(description="Events over last 7 days by action type")
    user_roles: list[dict] = Field(description="User count by role")
    top_properties: list[dict] = Field(description="Top 10 viewed properties")
    recent_actions: list[dict] = Field(description="Last 50 user actions")


@router.get(
    "/analytics",
    response_model=AnalyticsResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def get_analytics(
    request: Request,
    user: User = Depends(require_role("admin", "super_admin")),
    session: AsyncSession = Depends(get_db),
) -> AnalyticsResponse:
    """Get BI dashboard analytics data.

    Requires admin or super_admin role.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today_start - timedelta(days=7)

    # DAU - unique users with actions today
    dau_result = await session.execute(
        select(func.count(func.distinct(UserAction.user_id)))
        .where(UserAction.created_at >= today_start)
        .where(UserAction.user_id.isnot(None))
    )
    dau = dau_result.scalar_one() or 0

    # Searches today
    searches_result = await session.execute(
        select(func.count())
        .select_from(UserAction)
        .where(UserAction.created_at >= today_start)
        .where(UserAction.action == "search_performed")
    )
    searches_today = searches_result.scalar_one() or 0

    # Properties viewed today
    viewed_result = await session.execute(
        select(func.count())
        .select_from(UserAction)
        .where(UserAction.created_at >= today_start)
        .where(UserAction.action == "property_viewed")
    )
    properties_viewed = viewed_result.scalar_one() or 0

    # Inquiries sent today
    inquiries_result = await session.execute(
        select(func.count())
        .select_from(UserAction)
        .where(UserAction.created_at >= today_start)
        .where(UserAction.action == "inquiry_sent")
    )
    inquiries_sent = inquiries_result.scalar_one() or 0

    # Events over time (last 7 days, grouped by date and action)
    events_result = await session.execute(
        select(
            func.date_trunc('day', UserAction.created_at).label('day'),
            UserAction.action,
            func.count(),
        )
        .where(UserAction.created_at >= week_ago)
        .group_by('day', UserAction.action)
        .order_by('day')
    )
    events_raw = events_result.all()

    # Build events_over_time as a list of {date, events} per day
    events_by_day: dict[str, int] = {}
    for row in events_raw:
        day_str = row.day.strftime('%a') if hasattr(row.day, 'strftime') else str(row.day)
        events_by_day[day_str] = events_by_day.get(day_str, 0) + row.count
    events_over_time = [{"date": k, "events": v} for k, v in sorted(events_by_day.items())]

    # User roles distribution
    roles_result = await session.execute(
        select(User.roles, func.count())
        .join(User.roles)
        .group_by(User.roles)
    )
    roles_raw = roles_result.all()
    user_roles = [
        {"role": r.role.name if hasattr(r.role, 'name') else str(r.roles), "count": cnt}
        for r, cnt in roles_raw
    ]

    # Top 10 viewed properties (from user_actions.details.property_id)
    top_props_result = await session.execute(
        select(UserAction.details, func.count().label('views'))
        .where(UserAction.action == "property_viewed")
        .where(UserAction.created_at >= week_ago)
        .group_by(UserAction.details)
        .order_by(func.count().desc())
        .limit(10)
    )
    top_properties = [
        {"id": str(row.details.get('property_id', '')) if row.details else '', "views": row.views}
        for row in top_props_result.all()
    ]

    # Recent 50 actions
    recent_result = await session.execute(
        select(UserAction)
        .order_by(UserAction.created_at.desc())
        .limit(50)
    )
    recent_actions = [
        {
            "action": r.action,
            "user": r.user.username if r.user else "Anonymous",
            "time": f"{(now - r.created_at).total_seconds() // 60:.0f}m ago",
            "details": r.details,
        }
        for r in recent_result.all()
    ]

    return AnalyticsResponse(
        dau=dau,
        searches_today=searches_today,
        properties_viewed=properties_viewed,
        inquiries_sent=inquiries_sent,
        events_over_time=events_over_time,
        user_roles=user_roles,
        top_properties=top_properties,
        recent_actions=recent_actions,
    )
