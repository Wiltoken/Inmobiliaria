"""Add soft delete fields for Ley 1581 compliance.

Revision ID: 004
Revises: 003_user_actions
Create Date: 2024-01-01 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003_user_actions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("deletion_reason", sa.String(length=50), nullable=True))
    op.add_column(
        "buyer_profiles",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "seller_profiles",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "agent_profiles",
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("agent_profiles", "is_deleted")
    op.drop_column("seller_profiles", "is_deleted")
    op.drop_column("buyer_profiles", "is_deleted")
    op.drop_column("users", "deletion_reason")
    op.drop_column("users", "deleted_at")
