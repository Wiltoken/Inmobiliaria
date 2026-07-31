"""Admin endpoints: user management, audit log queries, and compliance reports.

All endpoints require admin or super_admin role.

GET /api/v1/admin/users
GET /api/v1/admin/audit-logs
GET /api/v1/admin/compliance-report
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.redis_client import revoke_all_user_refresh_tokens
from app.api.v1.deps import get_db, require_role
from app.config import settings
from app.core.security import hash_password
from app.domain.models import AuditLog, LoginAttempt, PasswordReset, User
from app.domain.schemas import (
    AuditLogEntry,
    ComplianceReport,
    ErrorResponse,
    PaginatedAuditLogsResponse,
    PaginatedUsersResponse,
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
    user: User = Depends(require_role("admin", "super_admin")),  # noqa: ARG001 — enforces role
    session: AsyncSession = Depends(get_db),
) -> PaginatedUsersResponse:
    """List users with pagination and optional tenant filter.

    Requires admin or super_admin role.
    """
    # Build base query
    query = select(User)
    if tenant_id is not None:
        query = query.where(User.tenant_id == tenant_id)

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
            details={"page": page, "page_size": page_size, "tenant_id": str(tenant_id) if tenant_id else None},
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
