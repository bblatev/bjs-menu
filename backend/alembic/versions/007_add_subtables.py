"""Add subtables for table splitting

Revision ID: 007
Revises: 006
Create Date: 2026-02-03

Adds subtables feature for splitting large tables into sections.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Subtables - for splitting large tables into sections
    op.create_table(
        'subtables',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('parent_table_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),  # "A", "B", "C"
        # Capacity
        sa.Column('seats', sa.Integer(), default=2, nullable=False),
        sa.Column('current_guests', sa.Integer(), default=0, nullable=False),
        # Status
        sa.Column('status', sa.String(20), default='available', nullable=False),
        # Current order
        sa.Column('current_order_id', sa.Integer(), nullable=True),
        # Assigned waiter
        sa.Column('waiter_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_subtables_parent_table_id', 'subtables', ['parent_table_id'])
    op.create_index('ix_subtables_status', 'subtables', ['status'])
    op.create_index('ix_subtables_location_id', 'subtables', ['location_id'])


def downgrade() -> None:
    op.drop_table('subtables')
