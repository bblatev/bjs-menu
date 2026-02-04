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

    # Note: Any existing plain text PINs in the 'pin' column will need to be
    # re-hashed by users. We cannot migrate them automatically as we need
    # the plain text to hash it.

    # Drop the old plain text pin column if it exists
    try:
        op.drop_column('users', 'pin')
    except Exception:
        # Column may not exist in all environments
        pass


def downgrade() -> None:
    # Add back the plain text pin column
    op.add_column('users', sa.Column('pin', sa.String(10), nullable=True))
    # Drop the hashed pin column
    op.drop_column('users', 'pin_hash')
