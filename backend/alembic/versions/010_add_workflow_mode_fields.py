"""Add workflow mode fields to kitchen_orders.

Revision ID: 010
Revises: 009
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Workflow mode fields are now included in the initial migration (001)
    pass


def downgrade() -> None:
    # No-op - workflow fields are part of initial migration
    pass
