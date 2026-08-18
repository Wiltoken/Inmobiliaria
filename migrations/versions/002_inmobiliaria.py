"""002_inmobiliaria — create inmobiliaria extension and all property/match/inquiry tables.

Revision ID: 002
Revises: 001
Create Date: 2026-07-31

"""
from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable PostGIS extension for geography support
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Enable pg_trgm for fuzzy text search on titles and descriptions
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # ── projects ───────────────────────────────────────────────────────────────
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("construction_stage", sa.String(100), nullable=True),
        sa.Column("total_units", sa.Integer(), nullable=True),
        sa.Column("available_units", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── buyer_profiles ─────────────────────────────────────────────────────────
    op.create_table(
        "buyer_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("budget_min", sa.Float(), nullable=True),
        sa.Column("budget_max", sa.Float(), nullable=True),
        sa.Column("preferred_locations", JSONB, nullable=True, default=list),
        sa.Column("rooms_min", sa.Integer(), nullable=True),
        sa.Column("bathrooms_min", sa.Integer(), nullable=True),
        sa.Column("area_min", sa.Float(), nullable=True),
        sa.Column("area_max", sa.Float(), nullable=True),
        sa.Column("preferred_features", JSONB, nullable=True, default=dict),
        sa.Column("preferred_property_types", ARRAY(sa.String()), nullable=True, default=list),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_buyer_user_id", "buyer_profiles", ["user_id"])

    # ── seller_profiles ────────────────────────────────────────────────────────
    op.create_table(
        "seller_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("company_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_seller_user_id", "seller_profiles", ["user_id"])

    # ── agent_profiles ────────────────────────────────────────────────────────
    op.create_table(
        "agent_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("license_number", sa.String(100), nullable=False, unique=True),
        sa.Column("agency_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_user_id", "agent_profiles", ["user_id"])
    op.create_index("ix_agent_license_number", "agent_profiles", ["license_number"])

    # ── properties ──────────────────────────────────────────────────────────────
    op.create_table(
        "properties",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.Enum("apartment", "house", "commercial", "land", "office", "warehouse", "room", name="property_type_enum"), nullable=False),
        sa.Column("operation", sa.Enum("sale", "rent", "lease", name="property_operation_enum"), nullable=False),
        sa.Column("status", sa.Enum("active", "pending", "sold", "rented", "withdrawn", "rejected", name="property_status_enum"), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("area_m2", sa.Float(), nullable=True),
        sa.Column("location", JSONB, nullable=True, default=dict),
        sa.Column("rooms", sa.Integer(), nullable=True),
        sa.Column("bathrooms", sa.Integer(), nullable=True),
        sa.Column("features", JSONB, nullable=True, default=dict),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_property_type", "properties", ["type"])
    op.create_index("ix_property_operation", "properties", ["operation"])
    op.create_index("ix_property_status", "properties", ["status"])
    op.create_index("ix_property_price", "properties", ["price"])
    # GIN trgm indexes on title and description for fuzzy search
    op.create_index("ix_property_title_trgm", "properties", ["title"], postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"})
    op.create_index("ix_property_description_trgm", "properties", ["description"], postgresql_using="gin", postgresql_ops={"description": "gin_trgm_ops"})

    # ── property_photos ────────────────────────────────────────────────────────
    op.create_table(
        "property_photos",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(1000), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, default=0),
    )
    op.create_index("ix_photo_property_id", "property_photos", ["property_id"])

    # ── matches ─────────────────────────────────────────────────────────────────
    op.create_table(
        "matches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("buyer_id", UUID(as_uuid=True), sa.ForeignKey("buyer_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("score_breakdown", JSONB, nullable=True, default=dict),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_match_buyer_id", "matches", ["buyer_id"])
    op.create_index("ix_match_property_id", "matches", ["property_id"])
    op.create_unique_constraint("uq_match_buyer_property", "matches", ["buyer_id", "property_id"])

    # ── inquiries ────────────────────────────────────────────────────────────────
    op.create_table(
        "inquiries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("from_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("contact_preference", sa.Enum("email", "phone", "whatsapp", "either", name="contact_preference_enum"), nullable=False),
        sa.Column("status", sa.Enum("pending", "replied", "interested", "not_interested", name="inquiry_status_enum"), nullable=False),
        sa.Column("response_action", sa.Enum("sent_email", "sent_whatsapp", "called", "scheduled_viewing", "no_action", name="response_action_enum"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inquiry_from_user_id", "inquiries", ["from_user_id"])
    op.create_index("ix_inquiry_to_user_id", "inquiries", ["to_user_id"])
    op.create_index("ix_inquiry_property_id", "inquiries", ["property_id"])
    op.create_index("ix_inquiry_status", "inquiries", ["status"])

    # ── favorites ───────────────────────────────────────────────────────────────
    op.create_table(
        "favorites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("property_id", UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_favorite_user_id", "favorites", ["user_id"])
    op.create_index("ix_favorite_property_id", "favorites", ["property_id"])
    op.create_unique_constraint("uq_favorite_user_property", "favorites", ["user_id", "property_id"])


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_index("uq_favorite_user_property", table_name="favorites")
    op.drop_index("ix_favorite_property_id", table_name="favorites")
    op.drop_index("ix_favorite_user_id", table_name="favorites")
    op.drop_table("inquiries")
    op.drop_index("ix_inquiry_status", table_name="inquiries")
    op.drop_index("ix_inquiry_property_id", table_name="inquiries")
    op.drop_index("ix_inquiry_to_user_id", table_name="inquiries")
    op.drop_index("ix_inquiry_from_user_id", table_name="inquiries")
    op.drop_table("matches")
    op.drop_index("uq_match_buyer_property", table_name="matches")
    op.drop_index("ix_match_property_id", table_name="matches")
    op.drop_index("ix_match_buyer_id", table_name="matches")
    op.drop_table("property_photos")
    op.drop_index("ix_photo_property_id", table_name="property_photos")
    op.drop_table("properties")
    op.drop_index("ix_property_description_trgm", table_name="properties")
    op.drop_index("ix_property_title_trgm", table_name="properties")
    op.drop_index("ix_property_location", table_name="properties")
    op.drop_index("ix_property_price", table_name="properties")
    op.drop_index("ix_property_status", table_name="properties")
    op.drop_index("ix_property_operation", table_name="properties")
    op.drop_index("ix_property_type", table_name="properties")
    op.drop_table("agent_profiles")
    op.drop_index("ix_agent_license_number", table_name="agent_profiles")
    op.drop_index("ix_agent_user_id", table_name="agent_profiles")
    op.drop_table("seller_profiles")
    op.drop_index("ix_seller_user_id", table_name="seller_profiles")
    op.drop_table("buyer_profiles")
    op.drop_index("ix_buyer_user_id", table_name="buyer_profiles")
    op.drop_table("projects")

    op.execute("DROP TYPE IF EXISTS response_action_enum")
    op.execute("DROP TYPE IF EXISTS inquiry_status_enum")
    op.execute("DROP TYPE IF EXISTS contact_preference_enum")
    op.execute("DROP TYPE IF EXISTS property_status_enum")
    op.execute("DROP TYPE IF EXISTS property_operation_enum")
    op.execute("DROP TYPE IF EXISTS property_type_enum")

    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("DROP EXTENSION IF EXISTS postgis")
