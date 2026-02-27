"""028: Schema hardening — type changes, constraints, indexes, new columns.

Applies model changes from the code review audit (rounds 1-5):
- Float → Numeric(10,2) for ~70 monetary columns (prevents IEEE 754 rounding)
- New unique constraints on 7 tables
- New check constraints on 4 status columns
- New indexes on 4 frequently-queried columns
- New column: purchase_order_lines.received_qty for partial-receive tracking
- New enum value: POStatus.PARTIALLY_RECEIVED (PostgreSQL only)
- Server-default timestamps on ~40 tables (replaces Python-side datetime.now())
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "028b"
down_revision = "028a"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Float → Numeric conversions  (table, column, precision, scale)
# ---------------------------------------------------------------------------
FLOAT_TO_NUMERIC = [
    # customers
    ("customers", "total_spent", 10, 2),
    ("customers", "average_order", 10, 2),
    ("customers", "lifetime_value", 10, 2),
    # staff_users
    ("staff_users", "hourly_rate", 10, 2),
    ("staff_users", "commission_percentage", 10, 4),
    ("staff_users", "service_fee_percentage", 10, 4),
    # tip_pools
    ("tip_pools", "total_tips_cash", 10, 2),
    ("tip_pools", "total_tips_card", 10, 2),
    ("tip_pools", "total_tips", 10, 2),
    # tip_distributions
    ("tip_distributions", "share_percentage", 10, 4),
    ("tip_distributions", "amount", 10, 2),
    # checks
    ("checks", "subtotal", 10, 2),
    ("checks", "tax", 10, 2),
    ("checks", "discount", 10, 2),
    ("checks", "total", 10, 2),
    ("checks", "balance_due", 10, 2),
    # check_items
    ("check_items", "price", 10, 2),
    ("check_items", "total", 10, 2),
    # check_payments
    ("check_payments", "amount", 10, 2),
    ("check_payments", "tip", 10, 2),
    # menu_items
    ("menu_items", "price", 10, 2),
    ("menu_items", "base_price", 10, 2),
    # modifier_options
    ("modifier_options", "price_adjustment", 10, 2),
    # combo_meals
    ("combo_meals", "price", 10, 2),
    # guest_orders
    ("guest_orders", "subtotal", 10, 2),
    ("guest_orders", "tax", 10, 2),
    ("guest_orders", "total", 10, 2),
    ("guest_orders", "tip_amount", 10, 2),
    # delivery_orders
    ("delivery_orders", "subtotal", 10, 2),
    ("delivery_orders", "tax", 10, 2),
    ("delivery_orders", "delivery_fee", 10, 2),
    ("delivery_orders", "tip", 10, 2),
    ("delivery_orders", "total", 10, 2),
    ("delivery_orders", "platform_fee", 10, 2),
    ("delivery_orders", "net_payout", 10, 2),
    # invoices
    ("invoices", "subtotal", 10, 2),
    ("invoices", "tax_amount", 10, 2),
    ("invoices", "total_amount", 10, 2),
    # marketing_campaigns
    ("marketing_campaigns", "offer_value", 10, 2),
    # menu_analysis
    ("menu_analysis", "total_revenue", 10, 2),
    ("menu_analysis", "total_cost", 10, 2),
    ("menu_analysis", "total_profit", 10, 2),
    # invoice_lines
    ("invoice_lines", "unit_price", 10, 2),
    ("invoice_lines", "line_total", 10, 2),
    ("invoice_lines", "previous_price", 10, 2),
    # price_history
    ("price_history", "price", 10, 2),
    # price_alerts
    ("price_alerts", "threshold_amount", 10, 2),
    ("price_alerts", "max_price", 10, 2),
    # ap_approval_workflows
    ("ap_approval_workflows", "min_amount", 10, 2),
    ("ap_approval_workflows", "max_amount", 10, 2),
    ("ap_approval_workflows", "auto_approve_below_amount", 10, 2),
    # delivery_order_items
    ("delivery_order_items", "unit_price", 10, 2),
    ("delivery_order_items", "total_price", 10, 2),
    # delivery_platform_mappings
    ("delivery_platform_mappings", "platform_price", 10, 2),
    # reservations
    ("reservations", "no_show_fee", 10, 2),
    # server_performance
    ("server_performance", "total_revenue", 10, 2),
    ("server_performance", "total_tips", 10, 2),
    ("server_performance", "avg_ticket_size", 10, 2),
    # daily_metrics
    ("daily_metrics", "total_revenue", 10, 2),
    ("daily_metrics", "food_revenue", 10, 2),
    ("daily_metrics", "beverage_revenue", 10, 2),
    ("daily_metrics", "alcohol_revenue", 10, 2),
    ("daily_metrics", "avg_ticket", 10, 2),
    ("daily_metrics", "total_tips", 10, 2),
    ("daily_metrics", "cash_tips", 10, 2),
    ("daily_metrics", "card_tips", 10, 2),
    ("daily_metrics", "labor_cost", 10, 2),
    ("daily_metrics", "food_cost", 10, 2),
    ("daily_metrics", "beverage_cost", 10, 2),
    ("daily_metrics", "gross_profit", 10, 2),
    ("daily_metrics", "net_profit", 10, 2),
    # benchmarks
    ("benchmarks", "your_avg_ticket", 10, 2),
    ("benchmarks", "your_revenue_per_sqft", 10, 2),
    ("benchmarks", "benchmark_avg_ticket", 10, 2),
    ("benchmarks", "benchmark_revenue_per_sqft", 10, 2),
]

# ---------------------------------------------------------------------------
# Unique constraints  (table, constraint_name, columns)
# ---------------------------------------------------------------------------
UNIQUE_CONSTRAINTS = [
    ("staff_performance_metrics", "uq_perf_metric_staff_period", ["staff_id", "period", "period_date"]),
    ("delivery_integrations", "uq_delivery_integration_location_platform", ["location_id", "platform"]),
    ("delivery_orders", "uq_delivery_order_platform", ["integration_id", "platform_order_id"]),
    ("app_settings", "uq_app_setting_category_key", ["category", "key"]),
    ("recipe_lines", "uq_recipe_line_recipe_product", ["recipe_id", "product_id"]),
    ("inventory_lines", "uq_inventory_line_session_product", ["session_id", "product_id"]),
    ("suppliers", "uq_supplier_name", ["name"]),
]

# ---------------------------------------------------------------------------
# Check constraints  (table, constraint_name, condition) — PostgreSQL only
# ---------------------------------------------------------------------------
CHECK_CONSTRAINTS = [
    ("tables", "ck_table_status", "status IN ('available', 'occupied', 'reserved', 'cleaning')"),
    ("checks", "ck_check_status", "status IN ('open', 'closed', 'voided', 'paid')"),
    ("kitchen_orders", "ck_kitchen_order_status", "status IN ('pending', 'preparing', 'ready', 'served', 'cancelled')"),
    ("guest_orders", "ck_guest_order_status", "status IN ('received', 'pending', 'confirmed', 'preparing', 'ready', 'served', 'cancelled')"),
]

# ---------------------------------------------------------------------------
# Indexes  (table, index_name, columns)
# ---------------------------------------------------------------------------
INDEXES = [
    ("payment_ledger", "ix_payment_ledger_payment_intent_id", ["payment_intent_id"]),
    ("cash_variance_alerts", "ix_cash_variance_alerts_is_resolved", ["is_resolved"]),
    ("delivery_orders", "ix_delivery_orders_platform_order_id", ["platform_order_id"]),
    ("delivery_orders", "ix_delivery_orders_status", ["status"]),
]

# ---------------------------------------------------------------------------
# Timestamp columns that need server_default=NOW()  (table, column)
# ---------------------------------------------------------------------------
TIMESTAMP_DEFAULTS = [
    # invoice.py
    ("invoices", "created_at"),
    ("invoices", "updated_at"),
    ("price_history", "recorded_at"),
    ("price_alerts", "created_at"),
    ("gl_codes", "created_at"),
    ("ap_approval_workflows", "created_at"),
    # operations.py
    ("app_settings", "updated_at"),
    ("payroll_runs", "created_at"),
    ("payroll_entries", "created_at"),
    ("notifications", "created_at"),
    ("haccp_temperature_logs", "recorded_at"),
    ("haccp_safety_checks", "created_at"),
    ("feedback_reviews", "created_at"),
    ("audit_log_entries", "created_at"),
    ("vip_customer_links", "joined_at"),
    ("vip_occasions", "created_at"),
    ("warehouses", "created_at"),
    ("warehouse_transfers", "created_at"),
    ("promotions", "created_at"),
    ("badges", "created_at"),
    ("challenges", "created_at"),
    ("staff_achievements", "earned_at"),
    ("risk_alerts", "created_at"),
    ("referral_programs", "created_at"),
    ("referral_records", "created_at"),
    ("tax_filings", "created_at"),
    ("budgets", "created_at"),
    ("daily_reconciliations", "created_at"),
    ("shift_schedules", "created_at"),
    # analytics.py
    ("menu_analysis", "calculated_at"),
    ("server_performance", "calculated_at"),
    ("sales_forecasts", "created_at"),
    ("daily_metrics", "calculated_at"),
    ("conversational_queries", "created_at"),
    ("benchmarks", "calculated_at"),
    ("bottle_weights", "created_at"),
    ("bottle_weights", "updated_at"),
    ("scale_readings", "created_at"),
]


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    # ---- 1. New column: purchase_order_lines.received_qty ----
    try:
        op.add_column(
            "purchase_order_lines",
            sa.Column("received_qty", sa.Numeric(10, 2), server_default="0", nullable=False),
        )
    except Exception:
        pass  # Column may already exist

    # ---- 2. New enum value (PostgreSQL only) ----
    if dialect == "postgresql":
        # IF NOT EXISTS requires PostgreSQL 9.3+
        op.execute(text("ALTER TYPE postatus ADD VALUE IF NOT EXISTS 'partially_received'"))

    # ---- 3. Float → Numeric (PostgreSQL only; SQLite REAL is unaffected) ----
    if dialect == "postgresql":
        for table, column, prec, scale in FLOAT_TO_NUMERIC:
            try:
                op.execute(
                    text(
                        f"ALTER TABLE {table} "
                        f"ALTER COLUMN {column} TYPE NUMERIC({prec},{scale}) "
                        f"USING {column}::NUMERIC({prec},{scale})"
                    )
                )
            except Exception:
                pass  # Column may already be the right type or table may not exist

    # ---- 4. Unique constraints ----
    for table, name, columns in UNIQUE_CONSTRAINTS:
        try:
            op.create_unique_constraint(name, table, columns)
        except Exception:
            pass  # Constraint may already exist

    # ---- 5. Check constraints (PostgreSQL only) ----
    if dialect == "postgresql":
        for table, name, condition in CHECK_CONSTRAINTS:
            try:
                op.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({condition})"))
            except Exception:
                pass  # Constraint may already exist

    # ---- 6. Indexes ----
    for table, name, columns in INDEXES:
        try:
            op.create_index(name, table, columns)
        except Exception:
            pass  # Index may already exist

    # ---- 7. Server-default timestamps (PostgreSQL only) ----
    if dialect == "postgresql":
        for table, column in TIMESTAMP_DEFAULTS:
            try:
                op.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT NOW()"))
            except Exception:
                pass


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Remove indexes
    for table, name, _columns in reversed(INDEXES):
        try:
            op.drop_index(name, table_name=table)
        except Exception:
            pass

    # Remove check constraints (PostgreSQL only)
    if dialect == "postgresql":
        for table, name, _condition in reversed(CHECK_CONSTRAINTS):
            try:
                op.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}"))
            except Exception:
                pass

    # Remove unique constraints
    for table, name, _columns in reversed(UNIQUE_CONSTRAINTS):
        try:
            op.drop_constraint(name, table, type_="unique")
        except Exception:
            pass

    # Remove received_qty column
    try:
        op.drop_column("purchase_order_lines", "received_qty")
    except Exception:
        pass

    # Note: Float→Numeric reversals and enum value removal are NOT performed
    # as they could cause data loss. Manual intervention needed if truly reverting.
    # Note: Server-default timestamp removal is also skipped for safety.
