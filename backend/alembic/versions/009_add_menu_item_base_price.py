"""Add base_price to menu_items for turnover reporting.

Revision ID: 009
Revises: 008
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add base_price column to menu_items for cost/base price tracking
    op.add_column('menu_items', sa.Column('base_price', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('menu_items', 'base_price')
