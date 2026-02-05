"""Add stock reservation system: reserved_qty column and RESERVATION movement reasons.

Revision ID: 020
Revises: 019
Create Date: 2026-02-05

Changes:
- Add reserved_qty column to stock_on_hand (default 0)
- Add RESERVATION and RESERVATION_RELEASE to MovementReason enum values
  (PostgreSQL enum type update)
"""

from alembic import op
import sqlalchemy as sa

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade():
    # Add reserved_qty column to stock_on_hand
    op.add_column(
        "stock_on_hand",
        sa.Column("reserved_qty", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )

    # Add new enum values to the reason column
    # Since stock_movements.reason is a VARCHAR(50), not a PostgreSQL enum type,
    # no enum migration is needed - the new string values are automatically supported.


def downgrade():
    op.drop_column("stock_on_hand", "reserved_qty")
