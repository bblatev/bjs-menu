"""Add TouchSale gap feature tables

Revision ID: 006
Revises: 005
Create Date: 2026-02-02

Adds tables for TouchSale gap features:
- price_lists: Multiple pricing contexts (dine-in, takeout, delivery, happy hour, VIP)
- product_prices: Product-specific prices per price list
- daily_menus: Menu of the day specials
- operator_recent_items: Recently used items per operator
- manager_alerts: SMS/email alert configurations
- customer_credits: Customer credit limits and balances
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Price Lists - Multiple pricing contexts
    op.create_table(
        'price_lists',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(50), nullable=False, unique=True),
        sa.Column('description', sa.String(500), nullable=True),
        # Time-based activation
        sa.Column('start_time', sa.Time(), nullable=True),
        sa.Column('end_time', sa.Time(), nullable=True),
        sa.Column('days_of_week', sa.JSON(), nullable=True),  # [0,1,2,3,4,5,6] - Mon=0, Sun=6
        # Priority for auto-selection (higher = more priority)
        sa.Column('priority', sa.Integer(), default=0, nullable=False),
        # Conditions
        sa.Column('min_order_amount', sa.Float(), nullable=True),
        sa.Column('requires_membership', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_price_lists_code', 'price_lists', ['code'])
    op.create_index('ix_price_lists_is_active', 'price_lists', ['is_active'])
    op.create_index('ix_price_lists_location_id', 'price_lists', ['location_id'])

    # 2. Product Prices - Product-specific prices per price list
    op.create_table(
        'product_prices',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('price_list_id', sa.Integer(), sa.ForeignKey('price_lists.id', ondelete='CASCADE'), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        # Optional percentage adjustment instead of fixed price
        sa.Column('adjustment_type', sa.String(20), nullable=True),  # "fixed", "percent_markup", "percent_discount"
        sa.Column('adjustment_value', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_product_prices_product_id', 'product_prices', ['product_id'])
    op.create_index('ix_product_prices_price_list_id', 'product_prices', ['price_list_id'])
    op.create_unique_constraint('uq_product_prices_product_price_list', 'product_prices', ['product_id', 'price_list_id'])

    # 3. Daily Menus - Menu of the day specials
    op.create_table(
        'daily_menus',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        # Time availability
        sa.Column('available_from', sa.Time(), nullable=True),
        sa.Column('available_until', sa.Time(), nullable=True),
        # Menu items with special pricing
        sa.Column('items', sa.JSON(), nullable=True),  # [{"product_id": 1, "special_price": 12.99, "portion_size": "regular", "note": "Includes salad"}]
        # Pricing
        sa.Column('set_price', sa.Float(), nullable=True),  # Fixed price for entire menu
        # Limits
        sa.Column('max_orders', sa.Integer(), nullable=True),
        sa.Column('orders_sold', sa.Integer(), default=0, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_daily_menus_date', 'daily_menus', ['date'])
    op.create_index('ix_daily_menus_is_active', 'daily_menus', ['is_active'])
    op.create_index('ix_daily_menus_location_id', 'daily_menus', ['location_id'])

    # 4. Operator Recent Items - Track recently used items per operator
    op.create_table(
        'operator_recent_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('staff_id', sa.Integer(), sa.ForeignKey('staff_users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('last_used', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('use_count', sa.Integer(), default=1, nullable=False),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_operator_recent_items_staff_id', 'operator_recent_items', ['staff_id'])
    op.create_index('ix_operator_recent_items_product_id', 'operator_recent_items', ['product_id'])
    op.create_index('ix_operator_recent_items_last_used', 'operator_recent_items', ['last_used'])
    op.create_unique_constraint('uq_operator_recent_items_staff_product', 'operator_recent_items', ['staff_id', 'product_id'])

    # 5. Manager Alerts - SMS/email alert configurations
    op.create_table(
        'manager_alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),  # "void", "discount", "daily_close", "stock_critical", "large_order", "no_sale_open", "reversal"
        # Threshold for triggering (e.g., discount > 20%)
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('threshold_operator', sa.String(10), nullable=True),  # ">", "<", ">=", "<=", "="
        # Recipients
        sa.Column('recipient_phones', sa.JSON(), nullable=True),  # ["+359888123456"]
        sa.Column('recipient_emails', sa.JSON(), nullable=True),  # ["manager@restaurant.com"]
        # Notification methods
        sa.Column('send_sms', sa.Boolean(), default=True, nullable=False),
        sa.Column('send_email', sa.Boolean(), default=False, nullable=False),
        sa.Column('send_push', sa.Boolean(), default=False, nullable=False),
        # Timing
        sa.Column('cooldown_minutes', sa.Integer(), default=5, nullable=False),
        sa.Column('last_triggered', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_manager_alerts_alert_type', 'manager_alerts', ['alert_type'])
    op.create_index('ix_manager_alerts_is_active', 'manager_alerts', ['is_active'])
    op.create_index('ix_manager_alerts_location_id', 'manager_alerts', ['location_id'])

    # 6. Customer Credits - Credit limits and balances
    op.create_table(
        'customer_credits',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(), nullable=False, unique=True),
        sa.Column('credit_limit', sa.Float(), default=0, nullable=False),
        sa.Column('current_balance', sa.Float(), default=0, nullable=False),  # Positive = owes money
        # Status
        sa.Column('is_blocked', sa.Boolean(), default=False, nullable=False),
        sa.Column('block_reason', sa.String(255), nullable=True),
        # History
        sa.Column('last_payment_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_payment_amount', sa.Float(), nullable=True),
        sa.Column('location_id', sa.Integer(), nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_customer_credits_customer_id', 'customer_credits', ['customer_id'])
    op.create_index('ix_customer_credits_is_blocked', 'customer_credits', ['is_blocked'])
    op.create_index('ix_customer_credits_location_id', 'customer_credits', ['location_id'])


def downgrade() -> None:
    # Drop tables in reverse order of creation
    op.drop_table('customer_credits')
    op.drop_table('manager_alerts')
    op.drop_table('operator_recent_items')
    op.drop_table('daily_menus')
    op.drop_table('product_prices')
    op.drop_table('price_lists')
