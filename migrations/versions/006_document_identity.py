"""Add document identity fields to users.

Revision ID: 006
Revises: 005
Create Date: 2024-01-01 00:00:00

"""
from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("document_type", sa.String(length=10), nullable=True))
    op.add_column("users", sa.Column("document_number", sa.String(length=50), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "is_verified")
    op.drop_column("users", "document_number")
    op.drop_column("users", "document_type")
