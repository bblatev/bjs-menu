"""Add composite indexes for frequently used query patterns.

Revision ID: 013
Revises: 012
Create Date: 2026-02-04

These indexes target specific query patterns identified in code analysis:
- Stock lookups by product + location
- Sales queries by date + location
- User email lookups for authentication
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users - email lookup for authentication
    op.create_index('ix_users_email', 'users', ['email'], if_not_exists=True)
    op.create_index('ix_users_pin_hash', 'users', ['pin_hash'], if_not_exists=True)

    # Stock on hand - composite index for product + location lookups
    op.create_index(
        'ix_stock_on_hand_product_location',
        'stock_on_hand',
        ['product_id', 'location_id'],
        if_not_exists=True
    )

    # POS sales lines - composite index for date range + location queries
    op.create_index(
        'ix_pos_sales_lines_ts_location',
        'pos_sales_lines',
        ['ts', 'location_id'],
        if_not_exists=True
    )

    # POS sales lines - index for refund filtering (commonly filtered)
    op.create_index(
        'ix_pos_sales_lines_is_refund',
        'pos_sales_lines',
        ['is_refund'],
        if_not_exists=True
    )

    # Products - barcode and SKU lookups
    op.create_index('ix_products_barcode', 'products', ['barcode'], if_not_exists=True)
    op.create_index('ix_products_sku', 'products', ['sku'], if_not_exists=True)
    op.create_index('ix_products_supplier_id', 'products', ['supplier_id'], if_not_exists=True)

    # Daily metrics - composite for location + date queries
    op.create_index(
        'ix_daily_metrics_location_date',
        'daily_metrics',
        ['location_id', 'date'],
        if_not_exists=True
    )


def downgrade() -> None:
    op.drop_index('ix_daily_metrics_location_date', table_name='daily_metrics')
    op.drop_index('ix_products_supplier_id', table_name='products')
    op.drop_index('ix_products_sku', table_name='products')
    op.drop_index('ix_products_barcode', table_name='products')
    op.drop_index('ix_pos_sales_lines_is_refund', table_name='pos_sales_lines')
    op.drop_index('ix_pos_sales_lines_ts_location', table_name='pos_sales_lines')
    op.drop_index('ix_stock_on_hand_product_location', table_name='stock_on_hand')
    op.drop_index('ix_users_pin_hash', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
