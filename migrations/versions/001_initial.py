"""initial — create all 7 tables with indexes and CITEXT extension.

Revision ID: 001
Revises:
Create Date: 2026-07-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, CITEXT

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable CITEXT extension for case-insensitive usernames
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # ── roles ────────────────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
    )

    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("username", CITEXT(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("is_locked", sa.Boolean, nullable=False, default=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_given_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_user_email", "users", ["email"])
    op.create_index("ix_user_tenant_id", "users", ["tenant_id"])
    op.create_unique_constraint(
        "uq_user_username_tenant", "users", ["username", "tenant_id"]
    )

    # ── user_roles ──────────────────────────────────────────────────────────
    op.create_table(
        "user_roles",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )

    # ── audit_logs ───────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("details", JSONB, nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_audit_user_created", "audit_logs", ["user_id", "created_at"])
    op.create_index(
        "ix_audit_created_at", "audit_logs", ["created_at"],
        postgresql_using="brin"
    )

    # ── refresh_tokens ───────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jti", sa.String(255), nullable=False, unique=True),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_refresh_user_expires", "refresh_tokens", ["user_id", "expires_at"])

    # ── password_resets ─────────────────────────────────────────────────────
    op.create_table(
        "password_resets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── login_attempts ───────────────────────────────────────────────────────
    op.create_table(
        "login_attempts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("success", sa.Boolean, nullable=False, default=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_login_attempt_user_time", "login_attempts", ["user_id", "attempted_at"])


def downgrade() -> None:
    op.drop_table("login_attempts")
    op.drop_table("password_resets")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_audit_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_user_created", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("user_roles")
    op.drop_index("uq_user_username_tenant", table_name="users")
    op.drop_index("ix_user_tenant_id", table_name="users")
    op.drop_index("ix_user_email", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")
