"""Pydantic request/response schemas for the auth API.

All schemas match the API contract from design.md.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


# ── Auth request/response schemas ────────────────────────────────────────────


class LoginRequest(BaseModel):
    """POST /api/v1/auth/login request body."""

    username: Annotated[str, Field(min_length=1, max_length=255)]
    password: Annotated[str, Field(min_length=1, max_length=128)]
    tenant_id: uuid.UUID | None = None
    recaptcha_token: str | None = None


class TokenResponse(BaseModel):
    """Response schema for successful authentication."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    expires_in: int  # seconds
    token_type: str = "Bearer"


class RefreshRequest(BaseModel):
    """POST /api/v1/auth/refresh request body."""

    refresh_token: str


class RefreshResponse(BaseModel):
    """Response schema for token refresh."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    expires_in: int  # seconds
    token_type: str = "Bearer"


class ErrorResponse(BaseModel):
    """Standard error response per API contract."""

    model_config = ConfigDict(from_attributes=True)

    detail: str
    error_code: str
    remaining_attempts: int | None = None
    locked_until: str | None = None
    required_roles: list[str] | None = None


# ── User schemas ──────────────────────────────────────────────────────────────


class UserProfile(BaseModel):
    """GET /api/v1/users/me response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    tenant_id: uuid.UUID
    roles: list[str]
    is_active: bool
    is_locked: bool
    consent_given_at: datetime | None = None
    password_changed_at: datetime | None = None


# ── Password policy schemas ────────────────────────────────────────────────────


class PasswordPolicyViolation(BaseModel):
    """Single password policy violation."""

    field: str
    message: str


class PasswordPolicyErrorResponse(BaseModel):
    """Response when password doesn't meet policy."""

    model_config = ConfigDict(from_attributes=True)

    detail: str = "Password policy violation"
    error_code: str = "AUTH_PASSWORD_POLICY_VIOLATION"
    violations: list[PasswordPolicyViolation]


# ── Password recovery schemas ──────────────────────────────────────────────────


class ForgotPasswordRequest(BaseModel):
    """POST /api/v1/auth/forgot-password request body."""

    email: Annotated[str, Field(min_length=1, max_length=255)]


class ForgotPasswordResponse(BaseModel):
    """POST /api/v1/auth/forgot-password response."""

    message: str = "If the email exists, a password reset link has been sent."


class ResetPasswordRequest(BaseModel):
    """POST /api/v1/auth/reset-password request body."""

    token: Annotated[str, Field(min_length=1)]
    new_password: Annotated[str, Field(min_length=1, max_length=128)]


class ResetPasswordResponse(BaseModel):
    """POST /api/v1/auth/reset-password response."""

    message: str = "Password has been reset successfully."


# ── Admin schemas ────────────────────────────────────────────────────────────────


class PaginatedUsersResponse(BaseModel):
    """GET /api/v1/admin/users response (paginated)."""

    model_config = ConfigDict(from_attributes=True)

    users: list[UserProfile]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogEntry(BaseModel):
    """Single audit log record in list responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    action: str
    ip_address: str | None
    details: dict | None
    created_at: datetime


class PaginatedAuditLogsResponse(BaseModel):
    """GET /api/v1/admin/audit-logs response (paginated)."""

    audit_logs: list[AuditLogEntry]
    total: int
    page: int
    page_size: int
    total_pages: int


class ComplianceReport(BaseModel):
    """GET /api/v1/admin/compliance-report response for Ley 1581/2012."""

    model_config = ConfigDict(from_attributes=True)

    active_users: int
    locked_accounts: int
    failed_logins_today: int
    users_without_consent: int
    password_expired_count: int

