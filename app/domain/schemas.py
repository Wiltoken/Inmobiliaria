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


# ── Registration schemas ───────────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    """POST /api/v1/auth/register request body."""

    username: Annotated[str, Field(min_length=3, max_length=255)]
    email: Annotated[str, Field(min_length=1, max_length=255)]
    password: Annotated[str, Field(min_length=8, max_length=128)]
    role: Annotated[str, Field(min_length=1, max_length=50)]
    # Seller profile fields
    phone: str | None = None
    company_name: str | None = None
    # Buyer profile fields
    budget_min: float | None = None
    budget_max: float | None = None
    preferred_locations: list[str] | None = None
    # Agent profile fields
    license_number: str | None = None
    agency_name: str | None = None


class RegisterUserResponse(BaseModel):
    """User payload returned by registration."""

    id: uuid.UUID
    username: str
    email: str
    role_id: uuid.UUID
    roles: list[str]


class RegisterResponse(BaseModel):
    """POST /api/v1/auth/register response."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    user: RegisterUserResponse


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


# ── Property schemas ────────────────────────────────────────────────────────────


class PropertyPhotoResponse(BaseModel):
    """Photo in property response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    order: int


class PropertyCreate(BaseModel):
    """POST /api/v1/properties request body."""

    type: str
    operation: str
    price: float
    area_m2: float | None = None
    lat: float | None = None
    lon: float | None = None
    rooms: int | None = None
    bathrooms: int | None = None
    features: list[str] | None = None
    title: str
    description: str | None = None
    project_id: uuid.UUID | None = None


class PropertyUpdate(BaseModel):
    """PUT /api/v1/properties/{id} request body — all optional."""

    type: str | None = None
    operation: str | None = None
    price: float | None = None
    area_m2: float | None = None
    lat: float | None = None
    lon: float | None = None
    rooms: int | None = None
    bathrooms: int | None = None
    features: list[str] | None = None
    title: str | None = None
    description: str | None = None
    project_id: uuid.UUID | None = None


class PropertySearch(BaseModel):
    """GET /api/v1/properties query parameters for search."""

    type: str | None = None
    operation: str | None = None
    price_min: float | None = None
    price_max: float | None = None
    lat: float | None = None
    lon: float | None = None
    radius_km: float | None = None
    rooms_min: int | None = None
    bathrooms_min: int | None = None
    area_min: float | None = None
    area_max: float | None = None
    query: str | None = None
    page: int = 1
    limit: int = 20


class PropertyResponse(BaseModel):
    """Property in list/detail responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    operation: str
    status: str
    price: float
    area_m2: float | None
    lat: float | None
    lon: float | None
    rooms: int | None
    bathrooms: int | None
    features: dict | None
    title: str
    description: str | None
    is_active: bool
    owner_id: uuid.UUID | None
    agent_id: uuid.UUID | None
    project_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    distance: float | None = None
    photos: list[PropertyPhotoResponse] = []


class PropertyStatusUpdate(BaseModel):
    """PATCH /api/v1/properties/{id}/status request body."""

    status: str


class PhotoUploadResponse(BaseModel):
    """Response after uploading a photo."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    order: int


class PaginatedPropertiesResponse(BaseModel):
    """GET /api/v1/properties paginated response."""

    properties: list[PropertyResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# ── Profile schemas ────────────────────────────────────────────────────────────


class PreferredLocationItem(BaseModel):
    """Single preferred location with radius."""

    lat: float
    lon: float
    radius_km: float = 5.0


class BuyerProfileUpdate(BaseModel):
    """PUT /api/v1/profiles/me request body."""

    budget_min: float | None = None
    budget_max: float | None = None
    preferred_locations: list[PreferredLocationItem] | None = None
    rooms_min: int | None = None
    bathrooms_min: int | None = None
    area_min: float | None = None
    area_max: float | None = None
    preferred_features: list[str] | None = None
    preferred_property_types: list[str] | None = None


class BuyerProfileResponse(BaseModel):
    """Buyer profile in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    budget_min: float | None
    budget_max: float | None
    preferred_locations: list[PreferredLocationItem] | None
    rooms_min: int | None
    bathrooms_min: int | None
    area_min: float | None
    area_max: float | None
    preferred_features: dict | None
    preferred_property_types: list[str] | None
    created_at: datetime
    updated_at: datetime


class SellerProfileResponse(BaseModel):
    """Seller profile in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    phone: str | None
    company_name: str | None
    created_at: datetime
    updated_at: datetime


class AgentProfileResponse(BaseModel):
    """Agent profile in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    license_number: str
    agency_name: str | None
    created_at: datetime
    updated_at: datetime


class SellerProfileUpdate(BaseModel):
    """PUT /api/v1/profiles/me for seller."""

    phone: str | None = None
    company_name: str | None = None


class AgentProfileUpdate(BaseModel):
    """PUT /api/v1/profiles/me for agent."""

    license_number: str | None = None
    agency_name: str | None = None


# ── Inquiry schemas ─────────────────────────────────────────────────────────────


class InquiryCreate(BaseModel):
    """POST /api/v1/inquiries request body."""

    property_id: uuid.UUID
    message: Annotated[str, Field(min_length=1, max_length=2000)]
    contact_preference: str = "email"


class InquiryResponse(BaseModel):
    """Single inquiry in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_user_id: uuid.UUID
    to_user_id: uuid.UUID
    property_id: uuid.UUID
    message: str
    contact_preference: str
    status: str
    response_message: str | None
    response_action: str | None
    created_at: datetime


class InquiryListResponse(BaseModel):
    """GET /api/v1/inquiries response."""

    inquiries: list[InquiryResponse]
    total: int


class InquiryAction(BaseModel):
    """PATCH /api/v1/inquiries/{id} request body."""

    action: str  # accept | decline | request_more_info
    response_message: str | None = None


# ── Favorite schemas ────────────────────────────────────────────────────────────


class FavoriteResponse(BaseModel):
    """Single favorite in responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    property_id: uuid.UUID
    created_at: datetime


class FavoriteCreate(BaseModel):
    """POST /api/v1/favorites request body."""

    property_id: uuid.UUID

