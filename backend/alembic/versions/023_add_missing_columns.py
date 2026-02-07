"""023: Add missing columns to menu_items and stock_on_hand.

Fixes 500 errors caused by SQLAlchemy models referencing columns
that don't exist in the database:
- menu_items.recipe_id (FK to recipes.id)
- stock_on_hand.reserved_qty (NUMERIC(10,2) default 0)
"""

from alembic import op
import sqlalchemy as sa

revision = "023"
down_revision = "022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add recipe_id column to menu_items (nullable FK to recipes table)
    op.execute("""
        ALTER TABLE menu_items ADD COLUMN recipe_id INTEGER REFERENCES recipes(id)
    """)

    # Add reserved_qty column to stock_on_hand (non-null, default 0)
    op.execute("""
        ALTER TABLE stock_on_hand ADD COLUMN reserved_qty NUMERIC(10, 2) NOT NULL DEFAULT 0
    """)


def downgrade() -> None:
    # SQLite doesn't support DROP COLUMN before 3.35.0
    # For safety, we recreate the tables without the columns
    pass
