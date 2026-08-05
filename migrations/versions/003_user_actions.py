"""Add user_actions table for frontend BI analytics.

Revision ID: 003
Revises: 002_inmobiliaria
Create Date: 2024-01-01 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002_inmobiliaria'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_actions table
    op.create_table(
        'user_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('details', postgresql.JSONB, nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_user_action_user_created', 'user_actions', ['user_id', 'created_at'])
    op.create_index('ix_user_action_created_at', 'user_actions', ['created_at'], postgresql_using='brin')
    op.create_index(op.f('ix_user_actions_action'), 'user_actions', ['action'], unique=False)


def downgrade() -> None:
    op.drop_table('user_actions')
