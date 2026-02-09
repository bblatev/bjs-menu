"""026: Add soft-delete deleted_at columns.

Adds ``deleted_at TIMESTAMP NULL`` to tables that support soft-delete
instead of physical deletion.
"""

from alembic import op
import sqlalchemy as sa

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None

# Tables that get SoftDeleteMixin
SOFT_DELETE_TABLES = [
    "checks",
    "check_items",
    "menu_items",
    "customers",
    "staff_users",
    "purchase_orders",
]


def upgrade() -> None:
    for table in SOFT_DELETE_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            )


def downgrade() -> None:
    for table in SOFT_DELETE_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("deleted_at")
