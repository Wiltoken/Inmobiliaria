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
from datetime import UTC, datetime, timedelta, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import get_db, require_role
from app.config import DEFAULT_TENANT_ID, settings
from app.core.exceptions import PasswordPolicyError
from app.core.security import hash_password
from app.domain.models import (
    AgentProfile,
    AuditLog,
    BuyerProfile,
    Inquiry,
    LoginAttempt,
    PasswordReset,
    Property,
    PropertyStatus,
    RefreshToken,
    Role,
    SellerProfile,
    User,
    UserAction,
    UserRole,
)
from app.domain.schemas import (
    AdminUserCreate,
    AdminUserUpdate,
    AuditLogEntry,
    ComplianceReport,
    ErrorResponse,
    PaginatedAuditLogsResponse,
    PaginatedUsersResponse,
    PropertyResponse,
    RoleSummary,
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


def _user_profile(user: User) -> UserProfile:
    """Map a User ORM instance (with roles loaded) to UserProfile."""
    return UserProfile(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        document_type=user.document_type,
        document_number=user.document_number,
        is_verified=user.is_verified,
        tenant_id=user.tenant_id,
        roles=[RoleSummary(id=role.id, name=role.name) for role in user.roles],
        is_active=user.is_active,
        is_locked=user.is_locked,
        locked_until=user.locked_until,
        consent_given_at=user.consent_given_at,
        password_changed_at=user.password_changed_at,
        created_at=user.created_at,
        deleted_at=user.deleted_at,
    )


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
    include_deleted: bool = False,
    search: str | None = None,
    user: User = Depends(require_role("admin", "super_admin")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> PaginatedUsersResponse:
    """List users with pagination, optional tenant filter, and optional role filter.

    Requires admin or super_admin role.
    """
    # Build base query — join User → Role via secondary
    from sqlalchemy.orm import selectinload

    query = select(User).options(selectinload(User.roles))
    if not include_deleted:
        query = query.where(User.deleted_at.is_(None))
    if tenant_id is not None:
        query = query.where(User.tenant_id == tenant_id)

    # Filter by role name if provided
    if role is not None:
        query = query.join(User.roles).where(User.roles.any(Role.name == role))

    # Case-insensitive search across username/email/full_name
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                User.username.ilike(pattern),
                User.email.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )

    query = query.order_by(User.created_at.desc())

    users, total, total_pages = await _paginate(session, query, page, page_size)

    user_profiles = [_user_profile(u) for u in users]

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


# ── GET /api/v1/admin/users/{user_id} ───────────────────────────────────────────


class AdminUserDetailResponse(BaseModel):
    """GET /api/v1/admin/users/{user_id} response — user + role-specific profile."""

    user: UserProfile
    profile: dict | None = None


@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def get_user(
    user_id: uuid.UUID,
    user: User = Depends(require_role("admin", "super_admin")),
    session: AsyncSession = Depends(get_db),
) -> AdminUserDetailResponse:
    """Return a single user with roles and their role-specific profile.

    Requires admin or super_admin role.
    """
    result = await session.execute(
        select(User)
        .options(
            selectinload(User.roles),
            selectinload(User.buyer_profile),
            selectinload(User.seller_profile),
            selectinload(User.agent_profile),
        )
        .where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    profile = None
    if target.buyer_profile is not None:
        bp = target.buyer_profile
        profile = {
            "type": "buyer",
            "budget_min": bp.budget_min,
            "budget_max": bp.budget_max,
            "preferred_locations": bp.preferred_locations,
            "rooms_min": bp.rooms_min,
            "bathrooms_min": bp.bathrooms_min,
            "area_min": bp.area_min,
            "area_max": bp.area_max,
            "preferred_features": bp.preferred_features,
            "preferred_property_types": bp.preferred_property_types,
        }
    elif target.seller_profile is not None:
        sp = target.seller_profile
        profile = {
            "type": "seller",
            "phone": sp.phone,
            "company_name": sp.company_name,
        }
    elif target.agent_profile is not None:
        ap = target.agent_profile
        profile = {
            "type": "agent",
            "license_number": ap.license_number,
            "agency_name": ap.agency_name,
        }

    return AdminUserDetailResponse(user=_user_profile(target), profile=profile)


# ── POST /api/v1/admin/users ────────────────────────────────────────────────────


@router.post(
    "/users",
    response_model=UserProfile,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid role or password policy violation"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        409: {"model": ErrorResponse, "description": "Username or email already registered"},
    },
)
async def create_user(
    body: AdminUserCreate,
    request: Request,
    admin: User = Depends(require_role("admin", "super_admin")),
    session: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Create a new user with a single role.

    Requires admin or super_admin role.
    """
    role_result = await session.execute(select(Role).where(Role.name == body.role))
    role = role_result.scalar_one_or_none()
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
            headers={"error_code": "AUTH_INVALID_ROLE"},
        )

    email = body.email.lower().strip()

    existing = await session.execute(
        select(User).where(or_(User.username == body.username, User.email == email))
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email is already registered",
            headers={"error_code": "AUTH_USER_EXISTS"},
        )

    try:
        password_hash = hash_password(body.password)
    except PasswordPolicyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password policy violation",
            headers={"error_code": "AUTH_PASSWORD_POLICY_VIOLATION"},
        )

    new_user = User(
        username=body.username,
        email=email,
        full_name=body.full_name,
        document_type=body.document_type,
        document_number=body.document_number,
        is_verified=body.is_verified,
        password_hash=password_hash,
        tenant_id=DEFAULT_TENANT_ID,
        is_active=body.is_active,
        consent_given_at=datetime.now(timezone.utc),
    )
    new_user.roles.append(role)
    session.add(new_user)
    await session.commit()

    try:
        audit_entry = AuditLog(
            user_id=admin.id,
            tenant_id=admin.tenant_id,
            action="admin_create_user",
            ip_address=request.client.host if request.client else None,
            details={"target_username": body.username, "role": body.role},
        )
        session.add(audit_entry)
        await session.commit()
    except Exception as exc:
        log.warning("audit_log_write_failed", action="admin_create_user", error=str(exc))

    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == new_user.id)
    )
    return _user_profile(result.scalar_one())


# ── PATCH /api/v1/admin/users/{user_id} ─────────────────────────────────────────


@router.patch(
    "/users/{user_id}",
    response_model=UserProfile,
    responses={
        400: {"model": ErrorResponse, "description": "One or more roles do not exist"},
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def update_user(
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    request: Request,
    admin: User = Depends(require_role("admin", "super_admin")),
    session: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Update a user's email, name, active/locked status, or roles.

    Requires admin or super_admin role.
    """
    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if body.email is not None:
        target.email = body.email.lower().strip()
    if body.full_name is not None:
        target.full_name = body.full_name
    if body.document_type is not None:
        target.document_type = body.document_type
    if body.document_number is not None:
        target.document_number = body.document_number
    if body.is_verified is not None:
        target.is_verified = body.is_verified
    if body.is_active is not None:
        target.is_active = body.is_active
    if body.is_locked is not None:
        target.is_locked = body.is_locked
        if body.is_locked:
            target.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.lockout_duration_minutes
            )
        else:
            target.locked_until = None

    if body.roles is not None:
        roles_result = await session.execute(select(Role).where(Role.name.in_(body.roles)))
        new_roles = list(roles_result.scalars().all())
        if len(new_roles) != len(body.roles):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more roles do not exist",
            )
        target.roles = new_roles

    await session.commit()

    try:
        audit_entry = AuditLog(
            user_id=admin.id,
            tenant_id=admin.tenant_id,
            action="admin_update_user",
            ip_address=request.client.host if request.client else None,
            details={"target_user_id": str(user_id)},
        )
        session.add(audit_entry)
        await session.commit()
    except Exception as exc:
        log.warning("audit_log_write_failed", action="admin_update_user", error=str(exc))

    result = await session.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    return _user_profile(result.scalar_one())


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


# ── GET /api/v1/admin/properties ────────────────────────────────────────────────


class AdminPropertyListItem(BaseModel):
    """Property row in the admin moderation list."""

    id: uuid.UUID
    title: str
    type: str
    operation: str
    status: str
    price: float
    owner: dict | None = None
    rejection_reason: str | None = None
    published_at: datetime | None = None
    created_at: datetime
    photo: str | None = None


class AdminPropertiesResponse(BaseModel):
    """GET /api/v1/admin/properties response (paginated)."""

    properties: list[AdminPropertyListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get(
    "/properties",
    response_model=AdminPropertiesResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def list_properties(
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[str | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    user: User = Depends(require_role("admin", "super_admin")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> AdminPropertiesResponse:
    """List all properties for moderation, with optional status filter and search.

    Requires admin or super_admin role.
    """
    query = select(Property).options(
        selectinload(Property.owner), selectinload(Property.photos)
    )
    if status_filter:
        query = query.where(Property.status == status_filter)
    if search:
        query = query.where(Property.title.ilike(f"%{search.strip()}%"))
    query = query.order_by(Property.created_at.desc())

    props, total, total_pages = await _paginate(session, query, page, page_size)

    items = [
        AdminPropertyListItem(
            id=prop.id,
            title=prop.title,
            type=prop.type,
            operation=prop.operation,
            status=prop.status,
            price=prop.price,
            owner={"id": str(prop.owner.id), "username": prop.owner.username} if prop.owner else None,
            rejection_reason=prop.rejection_reason,
            published_at=prop.published_at,
            created_at=prop.created_at,
            photo=prop.photos[0].url if prop.photos else None,
        )
        for prop in props
    ]

    return AdminPropertiesResponse(
        properties=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
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

    # Events over time (last 7 days) — bucket in Python for cross-DB safety
    week_actions = (
        await session.execute(
            select(UserAction.created_at).where(UserAction.created_at >= week_ago)
        )
    ).scalars().all()
    events_by_day: dict[str, int] = {}
    for created in week_actions:
        if created is None:
            continue
        day_str = _WEEKDAYS_ES[created.weekday()]
        events_by_day[day_str] = events_by_day.get(day_str, 0) + 1
    events_over_time = [
        {"date": day, "events": events_by_day.get(day, 0)} for day in _WEEKDAYS_ES
    ]

    # User roles distribution (proper join, distinct users per role)
    roles_result = await session.execute(
        select(Role.name, func.count(func.distinct(UserRole.user_id)))
        .select_from(UserRole)
        .join(Role, UserRole.role_id == Role.id)
        .join(User, UserRole.user_id == User.id)
        .where(User.deleted_at.is_(None))
        .group_by(Role.name)
    )
    user_roles = [{"role": name, "count": cnt} for name, cnt in roles_result.all()]

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
        .options(selectinload(UserAction.user))
        .order_by(UserAction.created_at.desc())
        .limit(50)
    )
    recent_actions = [
        {
            "action": r.action,
            "user": r.user.username if r.user else "Anonymous",
            "time": _minutes_ago(now, r.created_at),
            "details": r.details,
        }
        for r in recent_result.scalars().all()
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


# ── GET /api/v1/admin/dashboard ─────────────────────────────────────────────────

_MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
_WEEKDAYS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


def _minutes_ago(now: datetime, then: datetime) -> str:
    """Human-readable 'Xm ago' (SQLite returns naive datetimes, normalize to UTC)."""
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    return f"{(now - then).total_seconds() // 60:.0f}m ago"


def _registrations_last_6_months(created_values: list[datetime], now: datetime) -> list[dict]:
    """Bucket user creation timestamps into the last 6 months (cross-DB safe)."""
    result: list[dict] = []
    for i in range(5, -1, -1):
        total_months = now.year * 12 + (now.month - 1) - i
        year = total_months // 12
        month = total_months % 12 + 1
        count = sum(1 for c in created_values if c is not None and c.year == year and c.month == month)
        result.append({"month": _MONTHS_ES[month - 1], "users": count})
    return result


class AdminDashboardResponse(BaseModel):
    """GET /api/v1/admin/dashboard response — aggregate platform stats."""

    total_users: int = Field(description="Total non-deleted users")
    total_properties: int = Field(description="Total properties")
    total_inquiries: int = Field(description="Total inquiries")
    role_distribution: list[dict] = Field(description="User count by role")
    registrations_per_month: list[dict] = Field(description="New users per month, last 6 months")
    pending_properties: list[dict] = Field(description="Properties pending approval")


@router.get(
    "/dashboard",
    response_model=AdminDashboardResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
    },
)
async def admin_dashboard(
    request: Request,
    user: User = Depends(require_role("admin", "super_admin")),
    session: AsyncSession = Depends(get_db),
) -> AdminDashboardResponse:
    """Aggregate platform stats for the admin dashboard.

    Requires admin or super_admin role.
    """
    # Totals
    total_users = (
        await session.execute(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        )
    ).scalar_one() or 0
    total_properties = (
        await session.execute(select(func.count()).select_from(Property))
    ).scalar_one() or 0
    total_inquiries = (
        await session.execute(select(func.count()).select_from(Inquiry))
    ).scalar_one() or 0

    # Role distribution (non-deleted users, distinct per role)
    roles_result = await session.execute(
        select(Role.name, func.count(func.distinct(UserRole.user_id)))
        .select_from(UserRole)
        .join(Role, UserRole.role_id == Role.id)
        .join(User, UserRole.user_id == User.id)
        .where(User.deleted_at.is_(None))
        .group_by(Role.name)
    )
    role_distribution = [{"role": name, "count": cnt} for name, cnt in roles_result.all()]

    # Registrations per month (last 6 months, bucketed in Python for cross-DB)
    created_values = (
        await session.execute(select(User.created_at).where(User.deleted_at.is_(None)))
    ).scalars().all()
    registrations_per_month = _registrations_last_6_months(
        list(created_values), datetime.now(timezone.utc)
    )

    # Pending properties
    pending_result = await session.execute(
        select(Property)
        .options(selectinload(Property.photos), selectinload(Property.owner))
        .where(Property.status == PropertyStatus.PENDING.value)
        .order_by(Property.created_at.desc())
    )
    pending_properties = [
        {
            "id": str(prop.id),
            "title": prop.title,
            "owner": {"username": prop.owner.username} if prop.owner else None,
            "photos": [{"url": photo.url} for photo in (prop.photos or [])],
        }
        for prop in pending_result.scalars().all()
    ]

    # Audit log admin access
    try:
        audit_entry = AuditLog(
            user_id=user.id,
            tenant_id=user.tenant_id,
            action="admin_dashboard_view",
            ip_address=request.client.host if request.client else None,
            details={},
        )
        session.add(audit_entry)
        await session.commit()
    except Exception as exc:
        log.warning("audit_log_write_failed", action="admin_dashboard_view", error=str(exc))

    return AdminDashboardResponse(
        total_users=total_users,
        total_properties=total_properties,
        total_inquiries=total_inquiries,
        role_distribution=role_distribution,
        registrations_per_month=registrations_per_month,
        pending_properties=pending_properties,
    )


# ── POST /api/v1/admin/users/{user_id}/delete-data ────────────────────────────


@router.post(
    "/users/{user_id}/delete-data",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def admin_delete_user_data(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_role("admin", "super_admin")),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a user's data for Ley 1581 compliance.

    Cascades to profiles, revokes tokens, anonymizes audit logs.
    Requires admin or super_admin role.
    """
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    now = datetime.now(UTC)
    target_user.deleted_at = now
    target_user.deletion_reason = "admin_requested"
    target_user.is_active = False

    profiles_result = await session.execute(
        select(BuyerProfile).where(BuyerProfile.user_id == user_id)
    )
    if buyer := profiles_result.scalar_one_or_none():
        buyer.is_deleted = True

    profiles_result = await session.execute(
        select(SellerProfile).where(SellerProfile.user_id == user_id)
    )
    if seller := profiles_result.scalar_one_or_none():
        seller.is_deleted = True

    profiles_result = await session.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    if agent := profiles_result.scalar_one_or_none():
        agent.is_deleted = True

    from sqlalchemy import update

    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )

    await session.execute(
        update(PasswordReset)
        .where(PasswordReset.user_id == user_id, PasswordReset.used_at.is_(None))
        .values(used_at=now)
    )

    await session.execute(
        update(AuditLog)
        .where(AuditLog.user_id == user_id)
        .values(ip_address=None)
    )

    try:
        admin_entry = AuditLog(
            user_id=admin.id,
            tenant_id=admin.tenant_id,
            action="admin_delete_user_data",
            ip_address=request.client.host if request.client else None,
            details={"target_user_id": str(user_id)},
        )
        session.add(admin_entry)
    except Exception as exc:
        log.warning("audit_log_write_failed", action="admin_delete_user_data", error=str(exc))

    log.info("user_soft_deleted_by_admin", target_user_id=str(user_id), admin_id=str(admin.id))
    await session.commit()


# ── POST /api/v1/admin/users/{user_id}/restore ────────────────────────────────


class UserRestoreResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    is_active: bool
    deleted_at: datetime | None
    deletion_reason: str | None


@router.post(
    "/users/{user_id}/restore",
    response_model=UserRestoreResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Not authenticated"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "User not found"},
    },
)
async def admin_restore_user(
    user_id: uuid.UUID,
    request: Request,
    admin: User = Depends(require_role("admin", "super_admin")),
    session: AsyncSession = Depends(get_db),
) -> UserRestoreResponse:
    """Restore a soft-deleted user and their profiles.

    Requires admin or super_admin role.
    """
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    target_user.deleted_at = None
    target_user.deletion_reason = None
    target_user.is_active = True

    profiles_result = await session.execute(
        select(BuyerProfile).where(BuyerProfile.user_id == user_id)
    )
    if buyer := profiles_result.scalar_one_or_none():
        buyer.is_deleted = False

    profiles_result = await session.execute(
        select(SellerProfile).where(SellerProfile.user_id == user_id)
    )
    if seller := profiles_result.scalar_one_or_none():
        seller.is_deleted = False

    profiles_result = await session.execute(
        select(AgentProfile).where(AgentProfile.user_id == user_id)
    )
    if agent := profiles_result.scalar_one_or_none():
        agent.is_deleted = False

    try:
        admin_entry = AuditLog(
            user_id=admin.id,
            tenant_id=admin.tenant_id,
            action="admin_restore_user",
            ip_address=request.client.host if request.client else None,
            details={"target_user_id": str(user_id)},
        )
        session.add(admin_entry)
    except Exception as exc:
        log.warning("audit_log_write_failed", action="admin_restore_user", error=str(exc))

    log.info("user_restored_by_admin", target_user_id=str(user_id), admin_id=str(admin.id))
    await session.commit()

    return UserRestoreResponse(
        id=target_user.id,
        username=target_user.username,
        email=target_user.email,
        is_active=target_user.is_active,
        deleted_at=target_user.deleted_at,
        deletion_reason=target_user.deletion_reason,
    )
