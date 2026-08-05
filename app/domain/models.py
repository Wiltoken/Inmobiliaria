"""SQLAlchemy 2.0 async ORM models — all tables with indexes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Shared base for all ORM models. Used by Alembic to generate migrations."""

    pass


# ── Timestamp helper ────────────────────────────────────────────────────────


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ───────────────────────────────────────────────────────────────────


class PropertyType(str, PyEnum):
    APARTMENT = "apartment"
    HOUSE = "house"
    COMMERCIAL = "commercial"
    LAND = "land"
    OFFICE = "office"
    WAREHOUSE = "warehouse"
    ROOM = "room"


class PropertyOperation(str, PyEnum):
    SALE = "sale"
    RENT = "rent"
    LEASE = "lease"


class PropertyStatus(str, PyEnum):
    ACTIVE = "active"
    PENDING = "pending"
    SOLD = "sold"
    RENTED = "rented"
    WITHDRAWN = "withdrawn"
    REJECTED = "rejected"


class ContactPreference(str, PyEnum):
    EMAIL = "email"
    PHONE = "phone"
    WHATSAPP = "whatsapp"
    EITHER = "either"


class InquiryStatus(str, PyEnum):
    PENDING = "pending"
    REPLIED = "replied"
    INTERESTED = "interested"
    NOT_INTERESTED = "not_interested"


class ResponseAction(str, PyEnum):
    SENT_EMAIL = "sent_email"
    SENT_WHATSAPP = "sent_whatsapp"
    CALLED = "called"
    SCHEDULED_VIEWING = "scheduled_viewing"
    NO_ACTION = "no_action"


# ── Auth & User Models ─────────────────────────────────────────────────────


class User(Base):
    """Authenticated user with multi-tenant support."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        CITEXT(), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consent_given_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deletion_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relations
    roles: Mapped[list[Role]] = relationship(
        "Role", secondary="user_roles", back_populates="users"
    )
    audit_logs: Mapped[list[AuditLog]] = relationship("AuditLog", back_populates="user")
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user"
    )
    password_resets: Mapped[list[PasswordReset]] = relationship(
        "PasswordReset", back_populates="user"
    )
    login_attempts: Mapped[list[LoginAttempt]] = relationship(
        "LoginAttempt", back_populates="user"
    )
    buyer_profile: Mapped[BuyerProfile | None] = relationship(
        "BuyerProfile", back_populates="user", uselist=False
    )
    seller_profile: Mapped[SellerProfile | None] = relationship(
        "SellerProfile", back_populates="user", uselist=False
    )
    agent_profile: Mapped[AgentProfile | None] = relationship(
        "AgentProfile", back_populates="user", uselist=False
    )
    favorites: Mapped[list[Favorite]] = relationship("Favorite", back_populates="user")
    actions: Mapped[list[UserAction]] = relationship("UserAction", back_populates="user")

    __table_args__ = (
        UniqueConstraint("username", "tenant_id", name="uq_user_username_tenant"),
        Index("ix_user_email", "email"),
        Index("ix_user_tenant_id", "tenant_id"),
    )


class Role(Base):
    """Role for RBAC."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    # Relations
    users: Mapped[list[User]] = relationship(
        "User", secondary="user_roles", back_populates="roles"
    )


class UserRole(Base):
    """Join table for User <-> Role."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )


class AuditLog(Base):
    """Immutable audit trail for all auth events."""

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relations
    user: Mapped[User | None] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_user_created", "user_id", "created_at"),
        Index("ix_audit_created_at", "created_at", postgresql_using="brin"),
    )


class RefreshToken(Base):
    """Stored refresh token with revocation support."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    jti: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relations
    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_user_expires", "user_id", "expires_at"),
    )


class PasswordReset(Base):
    """Password reset token (single-use, time-limited)."""

    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relations
    user: Mapped[User] = relationship("User", back_populates="password_resets")


class LoginAttempt(Base):
    """Per-user login attempt log for lockout detection."""

    __tablename__ = "login_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relations
    user: Mapped[User] = relationship("User", back_populates="login_attempts")

    __table_args__ = (
        Index("ix_login_attempt_user_time", "user_id", "attempted_at"),
    )


# ── Profile Models ───────────────────────────────────────────────────────────


class BuyerProfile(Base):
    """Buyer profile with preferences for property matching."""

    __tablename__ = "buyer_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    budget_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_locations: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    rooms_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    area_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    area_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_features: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    preferred_property_types: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Relations
    user: Mapped[User] = relationship("User", back_populates="buyer_profile")
    matches: Mapped[list[Match]] = relationship("Match", back_populates="buyer")

    __table_args__ = (
        Index("ix_buyer_user_id", "user_id"),
    )


class SellerProfile(Base):
    """Seller profile with contact information."""

    __tablename__ = "seller_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Relations
    user: Mapped[User] = relationship("User", back_populates="seller_profile")

    __table_args__ = (
        Index("ix_seller_user_id", "user_id"),
    )


class AgentProfile(Base):
    """Agent profile with license information."""

    __tablename__ = "agent_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    license_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    agency_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    # Relations
    user: Mapped[User] = relationship("User", back_populates="agent_profile")

    __table_args__ = (
        Index("ix_agent_user_id", "user_id"),
        Index("ix_agent_license_number", "license_number"),
    )


# ── Property Models ──────────────────────────────────────────────────────────


class Project(Base):
    """Development project containing multiple properties."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    construction_stage: Mapped[str | None] = mapped_column(String(100), nullable=True)
    total_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relations
    properties: Mapped[list[Property]] = relationship("Property", back_populates="project")


class Property(Base):
    """Real estate property listing."""

    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(
        SAEnum(PropertyType, name="property_type_enum", create_constraint=True),
        nullable=False,
    )
    operation: Mapped[str] = mapped_column(
        SAEnum(PropertyOperation, name="property_operation_enum", create_constraint=True),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        SAEnum(PropertyStatus, name="property_status_enum", create_constraint=True),
        nullable=False,
        default=PropertyStatus.ACTIVE,
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    area_m2: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # GeoJSON Point for PostGIS
    rooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    features: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relations
    owner: Mapped[User | None] = relationship("User", foreign_keys=[owner_id])
    agent: Mapped[User | None] = relationship("User", foreign_keys=[agent_id])
    project: Mapped[Project | None] = relationship("Project", back_populates="properties")
    photos: Mapped[list[PropertyPhoto]] = relationship(
        "PropertyPhoto", back_populates="property", order_by="PropertyPhoto.order"
    )
    matches: Mapped[list[Match]] = relationship("Match", back_populates="property")
    favorites: Mapped[list[Favorite]] = relationship("Favorite", back_populates="property")
    inquiries: Mapped[list[Inquiry]] = relationship("Inquiry", foreign_keys="Inquiry.property_id", back_populates="property")

    __table_args__ = (
        Index("ix_property_type", "type"),
        Index("ix_property_operation", "operation"),
        Index("ix_property_status", "status"),
        Index("ix_property_price", "price"),
        Index("ix_property_location", "location", postgresql_using="gist"),
        Index("ix_property_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
        Index("ix_property_description_trgm", "description", postgresql_using="gin", postgresql_ops={"description": "gin_trgm_ops"}),
    )


class PropertyPhoto(Base):
    """Photos for a property listing."""

    __tablename__ = "property_photos"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relations
    property: Mapped[Property] = relationship("Property", back_populates="photos")

    __table_args__ = (
        Index("ix_photo_property_id", "property_id"),
    )


# ── Matching Models ──────────────────────────────────────────────────────────


class Match(Base):
    """Computed match between a buyer profile and a property."""

    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buyer_profiles.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relations
    buyer: Mapped[BuyerProfile] = relationship("BuyerProfile", back_populates="matches")
    property: Mapped[Property] = relationship("Property", back_populates="matches")

    __table_args__ = (
        UniqueConstraint("buyer_id", "property_id", name="uq_match_buyer_property"),
        Index("ix_match_buyer_id", "buyer_id"),
        Index("ix_match_property_id", "property_id"),
    )


# ── Inquiry Models ──────────────────────────────────────────────────────────


class Inquiry(Base):
    """Inquiry from a user regarding a property."""

    __tablename__ = "inquiries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    from_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    to_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    contact_preference: Mapped[str] = mapped_column(
        SAEnum(ContactPreference, name="contact_preference_enum", create_constraint=True),
        nullable=False,
        default=ContactPreference.EMAIL,
    )
    status: Mapped[str] = mapped_column(
        SAEnum(InquiryStatus, name="inquiry_status_enum", create_constraint=True),
        nullable=False,
        default=InquiryStatus.PENDING,
    )
    response_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_action: Mapped[str | None] = mapped_column(
        SAEnum(ResponseAction, name="response_action_enum", create_constraint=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relations
    from_user: Mapped[User] = relationship("User", foreign_keys=[from_user_id])
    to_user: Mapped[User] = relationship("User", foreign_keys=[to_user_id])
    property: Mapped[Property] = relationship("Property", foreign_keys=[property_id])

    __table_args__ = (
        Index("ix_inquiry_from_user_id", "from_user_id"),
        Index("ix_inquiry_to_user_id", "to_user_id"),
        Index("ix_inquiry_property_id", "property_id"),
        Index("ix_inquiry_status", "status"),
    )


# ── Favorite Models ──────────────────────────────────────────────────────────


class Favorite(Base):
    """User's favorite property."""

    __tablename__ = "favorites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relations
    user: Mapped[User] = relationship("User", back_populates="favorites")
    property: Mapped[Property] = relationship("Property", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "property_id", name="uq_favorite_user_property"),
        Index("ix_favorite_user_id", "user_id"),
        Index("ix_favorite_property_id", "property_id"),
    )


# ── User Action / BI Model ────────────────────────────────────────────────────


class UserAction(Base):
    """Frontend user action events for BI/analytics."""

    __tablename__ = "user_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relations
    user: Mapped[User | None] = relationship("User", back_populates="actions")

    __table_args__ = (
        Index("ix_user_action_user_created", "user_id", "created_at"),
        Index("ix_user_action_created_at", "created_at", postgresql_using="brin"),
        Index("ix_user_action_action", "action"),
    )
