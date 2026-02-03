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
    # Add workflow mode fields to kitchen_orders (Gap 11 - Request/Order modes)
    op.add_column('kitchen_orders', sa.Column('workflow_mode', sa.String(20), nullable=False, server_default='order'))
    op.add_column('kitchen_orders', sa.Column('is_confirmed', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('kitchen_orders', sa.Column('confirmed_by', sa.Integer(), nullable=True))
    op.add_column('kitchen_orders', sa.Column('confirmed_at', sa.DateTime(), nullable=True))
    op.add_column('kitchen_orders', sa.Column('rejection_reason', sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column('kitchen_orders', 'rejection_reason')
    op.drop_column('kitchen_orders', 'confirmed_at')
    op.drop_column('kitchen_orders', 'confirmed_by')
    op.drop_column('kitchen_orders', 'is_confirmed')
    op.drop_column('kitchen_orders', 'workflow_mode')
