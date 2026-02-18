"""028: Add is_deleted boolean column to soft-delete tables.

Adds ``is_deleted BOOLEAN NOT NULL DEFAULT FALSE`` alongside the existing
``deleted_at`` column for faster filtering and indexing.
"""

from alembic import op
import sqlalchemy as sa

revision = "028"
down_revision = "027"
branch_labels = None
depends_on = None

SOFT_DELETE_TABLES = [
    "checks",
    "check_items",
    "menu_items",
    "customers",
    "staff_users",
    "purchase_orders",
    "products",
    "suppliers",
]


def upgrade() -> None:
    for table in SOFT_DELETE_TABLES:
        try:
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "is_deleted",
                        sa.Boolean(),
                        nullable=False,
                        server_default=sa.text("0"),
                    )
                )
                batch_op.create_index(
                    f"ix_{table}_is_deleted",
                    ["is_deleted"],
                )
        except Exception:
            pass  # Column may already exist


def downgrade() -> None:
    for table in SOFT_DELETE_TABLES:
        try:
            with op.batch_alter_table(table) as batch_op:
                batch_op.drop_index(f"ix_{table}_is_deleted")
                batch_op.drop_column("is_deleted")
        except Exception:
            pass
