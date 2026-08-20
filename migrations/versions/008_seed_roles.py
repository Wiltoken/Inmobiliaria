"""Seed default roles.

Revision ID: 008
Revises: 007
Create Date: 2026-08-20

Inserts the default RBAC roles defined by the application. Idempotent: rows
whose ``name`` already exists are skipped via ``ON CONFLICT ... DO NOTHING``.
"""

import uuid
from typing import Sequence

from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_ROLES = ["super_admin", "admin", "agent", "seller", "buyer"]


def upgrade() -> None:
    values = ", ".join(f"('{uuid.uuid4()}', '{name}')" for name in DEFAULT_ROLES)
    op.execute(
        f"INSERT INTO roles (id, name) VALUES {values} "
        "ON CONFLICT (name) DO NOTHING"
    )


def downgrade() -> None:
    names = ", ".join(f"'{name}'" for name in DEFAULT_ROLES)
    op.execute(f"DELETE FROM roles WHERE name IN ({names})")
