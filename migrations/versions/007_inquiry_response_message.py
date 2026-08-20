"""Add inquiries.response_message and 'closed' to inquiry_status_enum.

Revision ID: 007
Revises: 006
Create Date: 2026-08-20

Fixes drift between the Inquiry model and the migrations:
- ``inquiries.response_message`` exists in the model but no migration ever
  created it.
- ``inquiry_status_enum`` was created with only 4 values while the model
  defines a 5th value, ``closed``.
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # a. response_message column present in the model but missing from migrations.
    op.add_column(
        "inquiries",
        sa.Column("response_message", sa.Text(), nullable=True),
    )

    # b. inquiry_status_enum is missing the 'closed' value defined by the model.
    #    ALTER TYPE ... ADD VALUE cannot run inside a transaction on PostgreSQL
    #    < 12 (and its value cannot be used in the same transaction on >= 12),
    #    so run it in an autocommit block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE inquiry_status_enum ADD VALUE IF NOT EXISTS 'closed'")


def downgrade() -> None:
    op.drop_column("inquiries", "response_message")
    # PostgreSQL does not support removing a value from an enum type. Leaving
    # 'closed' in place is intentional; the downgrade only reverts the column.
