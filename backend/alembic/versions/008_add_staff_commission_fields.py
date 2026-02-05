"""Add staff commission and auto-logout fields.

Revision ID: 008
Revises: 007
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add commission and service fee tracking to staff
    op.add_column('users', sa.Column('commission_percentage', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('users', sa.Column('service_fee_percentage', sa.Float(), nullable=False, server_default='0.0'))
    op.add_column('users', sa.Column('auto_logout_after_close', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'auto_logout_after_close')
    op.drop_column('users', 'service_fee_percentage')
    op.drop_column('users', 'commission_percentage')
