"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, default="staff"),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Suppliers table
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Products table
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("barcode", sa.String(50), unique=True, nullable=True, index=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=True, index=True),
        sa.Column("pack_size", sa.Integer(), default=1, nullable=False),
        sa.Column("unit", sa.String(20), default="pcs", nullable=False),
        sa.Column("min_stock", sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column("target_stock", sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column("lead_time_days", sa.Integer(), default=1, nullable=False),
        sa.Column("cost_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("sku", sa.String(50), nullable=True, index=True),
        sa.Column("ai_label", sa.String(100), nullable=True),
        sa.Column("active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Locations table
    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_default", sa.Boolean(), default=False, nullable=False),
        sa.Column("active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Stock on hand table
    op.create_table(
        "stock_on_hand",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("qty", sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("product_id", "location_id", name="uq_stock_product_location"),
    )

    # Stock movements table
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("qty_delta", sa.Numeric(10, 2), nullable=False),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("ref_type", sa.String(50), nullable=True),
        sa.Column("ref_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(500), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    )

    # AI photos table
    op.create_table(
        "ai_photos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), nullable=True),  # FK added later to avoid circular
        sa.Column("storage_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Inventory sessions table
    op.create_table(
        "inventory_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(20), default="draft", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
    )

    # Add FK to ai_photos after inventory_sessions exists
    op.create_foreign_key(
        "fk_ai_photos_session",
        "ai_photos",
        "inventory_sessions",
        ["session_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Inventory lines table
    op.create_table(
        "inventory_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("inventory_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("counted_qty", sa.Numeric(10, 2), nullable=False),
        sa.Column("method", sa.String(20), default="manual", nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=True),
        sa.Column("photo_id", sa.Integer(), sa.ForeignKey("ai_photos.id", ondelete="SET NULL"), nullable=True),
        sa.Column("counted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Purchase orders table
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("status", sa.String(20), default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.String(1000), nullable=True),
    )

    # Purchase order lines table
    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("po_id", sa.Integer(), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("qty", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_cost", sa.Numeric(10, 2), nullable=True),
    )

    # POS raw events table
    op.create_table(
        "pos_raw_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source", sa.String(50), nullable=False, index=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed", sa.Boolean(), default=False, nullable=False),
        sa.Column("error", sa.String(1000), nullable=True),
    )

    # POS sales lines table
    op.create_table(
        "pos_sales_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("pos_item_id", sa.String(100), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("qty", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_refund", sa.Boolean(), default=False, nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("raw_event_id", sa.Integer(), sa.ForeignKey("pos_raw_events.id", ondelete="SET NULL"), nullable=True),
        sa.Column("processed", sa.Boolean(), default=False, nullable=False),
    )

    # Recipes table
    op.create_table(
        "recipes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("pos_item_id", sa.String(100), nullable=True, index=True),
        sa.Column("pos_item_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Recipe lines table
    op.create_table(
        "recipe_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipe_id", sa.Integer(), sa.ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("qty", sa.Numeric(10, 4), nullable=False),
        sa.Column("unit", sa.String(20), default="pcs", nullable=False),
    )

    # ========== CORE POS TABLES ==========

    # Tables table (restaurant tables)
    op.create_table(
        "tables",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("number", sa.String(50), nullable=False),
        sa.Column("capacity", sa.Integer(), default=4),
        sa.Column("status", sa.String(20), default="available"),
        sa.Column("area", sa.String(50), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True, index=True),
        sa.Column("token", sa.String(100), nullable=True, unique=True),
        sa.Column("pos_table_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Menu items table
    op.create_table(
        "menu_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("available", sa.Boolean(), default=True),
        sa.Column("prep_time_minutes", sa.Integer(), nullable=True),
        sa.Column("station", sa.String(50), nullable=True),
        sa.Column("allergens", sa.JSON(), nullable=True),
        sa.Column("modifiers", sa.JSON(), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True, index=True),
        sa.Column("pos_item_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Checks table (bills)
    op.create_table(
        "checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id"), nullable=True, index=True),
        sa.Column("server_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True, index=True),
        sa.Column("guest_count", sa.Integer(), default=1),
        sa.Column("status", sa.String(20), default="open"),
        sa.Column("subtotal", sa.Numeric(10, 2), default=0),
        sa.Column("tax", sa.Numeric(10, 2), default=0),
        sa.Column("discount", sa.Numeric(10, 2), default=0),
        sa.Column("total", sa.Numeric(10, 2), default=0),
        sa.Column("balance_due", sa.Numeric(10, 2), default=0),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Check items table
    op.create_table(
        "check_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("checks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("menu_item_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), default=1),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("seat_number", sa.Integer(), nullable=True),
        sa.Column("course", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), default="ordered"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("modifiers", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("fired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("served_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("void_reason", sa.String(200), nullable=True),
    )

    # Check payments table
    op.create_table(
        "check_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("checks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("payment_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("tip", sa.Numeric(10, 2), default=0),
        sa.Column("card_last_four", sa.String(4), nullable=True),
        sa.Column("authorization_code", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Kitchen orders table
    op.create_table(
        "kitchen_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("check_id", sa.Integer(), sa.ForeignKey("checks.id"), nullable=True, index=True),
        sa.Column("table_number", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("priority", sa.Integer(), default=0),
        sa.Column("station", sa.String(50), nullable=True),
        sa.Column("course", sa.String(20), nullable=True),
        sa.Column("workflow_mode", sa.String(20), default="order"),
        sa.Column("is_confirmed", sa.Boolean(), default=True),
        sa.Column("confirmed_by", sa.Integer(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("items", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True, index=True),
    )

    # Guest orders table
    op.create_table(
        "guest_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id"), nullable=True, index=True),
        sa.Column("table_token", sa.String(100), nullable=True),
        sa.Column("table_number", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), default="received"),
        sa.Column("order_type", sa.String(20), default="dine-in"),
        sa.Column("subtotal", sa.Numeric(10, 2), default=0),
        sa.Column("tax", sa.Numeric(10, 2), default=0),
        sa.Column("total", sa.Numeric(10, 2), default=0),
        sa.Column("items", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("customer_name", sa.String(100), nullable=True),
        sa.Column("customer_phone", sa.String(20), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True, index=True),
        sa.Column("payment_status", sa.String(20), default="unpaid"),
        sa.Column("payment_method", sa.String(20), nullable=True),
        sa.Column("tip_amount", sa.Numeric(10, 2), default=0),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("email", sa.String(255), nullable=True, unique=True, index=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("segment", sa.String(50), nullable=True),
        sa.Column("total_visits", sa.Integer(), default=0),
        sa.Column("total_spend", sa.Numeric(12, 2), default=0),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("locations.id"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    # Drop POS tables first
    op.drop_table("customers")
    op.drop_table("guest_orders")
    op.drop_table("kitchen_orders")
    op.drop_table("check_payments")
    op.drop_table("check_items")
    op.drop_table("checks")
    op.drop_table("menu_items")
    op.drop_table("tables")
    # Original tables
    op.drop_table("recipe_lines")
    op.drop_table("recipes")
    op.drop_table("pos_sales_lines")
    op.drop_table("pos_raw_events")
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_orders")
    op.drop_table("inventory_lines")
    op.drop_constraint("fk_ai_photos_session", "ai_photos", type_="foreignkey")
    op.drop_table("inventory_sessions")
    op.drop_table("ai_photos")
    op.drop_table("stock_movements")
    op.drop_table("stock_on_hand")
    op.drop_table("locations")
    op.drop_table("products")
    op.drop_table("suppliers")
    op.drop_table("users")
