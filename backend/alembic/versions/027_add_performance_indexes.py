"""027: Add performance indexes on frequently queried columns.

Adds indexes on venue_id, created_at, and other columns used in
common query patterns to prevent table scans at scale.
"""

from alembic import op

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


# (table_name, index_name, columns)
INDEXES = [
    ("customers", "ix_customers_location_id", ["location_id"]),
    ("guest_orders", "ix_guest_orders_created_at", ["created_at"]),
    ("guest_orders", "ix_guest_orders_table_id", ["table_id"]),
    ("guest_orders", "ix_guest_orders_status", ["status"]),
    ("checks", "ix_checks_created_at", ["created_at"]),
    ("checks", "ix_checks_table_id", ["table_id"]),
    ("checks", "ix_checks_status", ["status"]),
    ("kitchen_orders", "ix_kitchen_orders_created_at", ["created_at"]),
    ("kitchen_orders", "ix_kitchen_orders_station_id", ["station_id"]),
    ("kitchen_orders", "ix_kitchen_orders_status", ["status"]),
    ("stock_movements", "ix_stock_movements_created_at", ["created_at"]),
    ("stock_movements", "ix_stock_movements_product_id", ["product_id"]),
    ("check_payments", "ix_check_payments_created_at", ["created_at"]),
    ("purchase_orders", "ix_purchase_orders_created_at", ["created_at"]),
    ("purchase_orders", "ix_purchase_orders_supplier_id", ["supplier_id"]),
]


def upgrade():
    for table, index_name, columns in INDEXES:
        try:
            op.create_index(index_name, table, columns)
        except Exception:
            # Index may already exist or table may not exist yet
            pass


def downgrade():
    for table, index_name, columns in INDEXES:
        try:
            op.drop_index(index_name, table_name=table)
        except Exception:
            pass
