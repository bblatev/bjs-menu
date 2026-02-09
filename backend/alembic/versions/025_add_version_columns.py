"""025: Add optimistic locking version columns.

Adds ``version INTEGER NOT NULL DEFAULT 1`` to high-concurrency tables
for optimistic locking support.
"""

from alembic import op
import sqlalchemy as sa

revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None

# Tables that get VersionMixin
VERSION_TABLES = [
    "stock_on_hand",
    "checks",
    "check_items",
    "kitchen_orders",
    "purchase_orders",
    "gift_cards",
]


def upgrade() -> None:
    for table in VERSION_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            )


def downgrade() -> None:
    for table in VERSION_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("version")
