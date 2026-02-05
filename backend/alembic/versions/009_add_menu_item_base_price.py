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
    # base_price is now included in the initial migration (001)
    pass


def downgrade() -> None:
    # No-op - base_price is part of initial migration
    pass
