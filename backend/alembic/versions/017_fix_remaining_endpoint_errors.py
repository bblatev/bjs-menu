"""Fix remaining endpoint errors: invoice_lines columns, kitchen_capacities
table, order_throttle_events table, seed default gift card program, and
add missing updated_at to gift_card_transactions.

- invoice_lines: rename 'unit' -> 'unit_of_measure', add item_code,
  previous_price, price_change_percent, price_alert_triggered, cost_category
- kitchen_capacities: create table (model __tablename__)
- order_throttle_events: create table
- gift_card_programs: insert default program so program_id=1 FK works
- gift_card_transactions: add updated_at column (required by TimestampMixin)

Revision ID: 017
Revises: 016
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ================================================================
    # 1. Fix invoice_lines table - add missing columns
    # ================================================================

    # Rename 'unit' column to 'unit_of_measure' to match the model
    op.alter_column(
        "invoice_lines",
        "unit",
        new_column_name="unit_of_measure",
    )

    # Add missing columns
    op.add_column(
        "invoice_lines",
        sa.Column("item_code", sa.String(100), nullable=True),
    )
    op.add_column(
        "invoice_lines",
        sa.Column("previous_price", sa.Float(), nullable=True),
    )
    op.add_column(
        "invoice_lines",
        sa.Column("price_change_percent", sa.Float(), nullable=True),
    )
    op.add_column(
        "invoice_lines",
        sa.Column("price_alert_triggered", sa.Boolean(), server_default="false", nullable=True),
    )
    op.add_column(
        "invoice_lines",
        sa.Column("cost_category", sa.String(100), nullable=True),
    )

    # ================================================================
    # 2. Create kitchen_capacities table (for KitchenCapacity model)
    # ================================================================
    op.create_table(
        "kitchen_capacities",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=False, index=True),
        sa.Column("max_orders_per_15min", sa.Integer(), server_default="20"),
        sa.Column("max_items_per_15min", sa.Integer(), server_default="100"),
        sa.Column("station_capacities", sa.JSON(), nullable=True),
        sa.Column("peak_hour_multiplier", sa.Float(), server_default="1.0"),
        sa.Column("off_peak_multiplier", sa.Float(), server_default="1.5"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 3. Create order_throttle_events table
    # ================================================================
    op.create_table(
        "order_throttle_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=False, index=True),
        sa.Column("event_time", sa.DateTime(), nullable=False),
        sa.Column("throttle_type", sa.String(50), nullable=False),
        sa.Column("current_load", sa.Integer(), nullable=False),
        sa.Column("max_capacity", sa.Integer(), nullable=False),
        sa.Column("orders_affected", sa.Integer(), server_default="0"),
        sa.Column("avg_delay_minutes", sa.Float(), nullable=True),
        sa.Column("auto_recovered", sa.Boolean(), server_default="false"),
        sa.Column("recovered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 4. Seed default gift card program (program_id=1)
    # ================================================================
    op.execute("""
        INSERT INTO gift_card_programs (id, name, denominations, custom_amount_allowed,
            min_amount, max_amount, bonus_enabled, is_active, created_at)
        VALUES (1, 'Default Gift Card Program', '[25, 50, 75, 100]', true,
            5.00, 500.00, false, true, NOW())
        ON CONFLICT (id) DO NOTHING
    """)

    # ================================================================
    # 5. Fix gift_card_transactions:
    #    - Add missing updated_at (TimestampMixin requires it)
    #    - Make old card_id column nullable (model uses gift_card_id now)
    # ================================================================
    op.add_column(
        "gift_card_transactions",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.alter_column(
        "gift_card_transactions",
        "card_id",
        nullable=True,
    )


def downgrade() -> None:
    # Restore card_id NOT NULL constraint
    op.alter_column("gift_card_transactions", "card_id", nullable=False)

    # Remove updated_at from gift_card_transactions
    op.drop_column("gift_card_transactions", "updated_at")

    # Remove seeded program
    op.execute("DELETE FROM gift_card_programs WHERE id = 1 AND name = 'Default Gift Card Program'")

    # Drop tables
    op.drop_table("order_throttle_events")
    op.drop_table("kitchen_capacities")

    # Remove added columns from invoice_lines
    op.drop_column("invoice_lines", "cost_category")
    op.drop_column("invoice_lines", "price_alert_triggered")
    op.drop_column("invoice_lines", "price_change_percent")
    op.drop_column("invoice_lines", "previous_price")
    op.drop_column("invoice_lines", "item_code")

    # Rename back
    op.alter_column(
        "invoice_lines",
        "unit_of_measure",
        new_column_name="unit",
    )
