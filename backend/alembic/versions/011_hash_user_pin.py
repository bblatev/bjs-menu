"""Hash user PIN field for security.

Revision ID: 011
Revises: 010
Create Date: 2026-02-03

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add pin_hash column to users table (replaces plain text pin)
    op.add_column('users', sa.Column('pin_hash', sa.String(255), nullable=True))

    # Note: The 'pin' column was never part of the initial schema,
    # so we don't need to drop it.


def downgrade() -> None:
    # Drop the hashed pin column
    op.drop_column('users', 'pin_hash')
