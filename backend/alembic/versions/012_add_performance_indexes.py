"""Add performance indexes for frequently queried columns.

Revision ID: 012
Revises: 011
Create Date: 2026-02-03

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tables - status and location lookups
    op.create_index('ix_tables_status', 'tables', ['status'], if_not_exists=True)
    op.create_index('ix_tables_location_id', 'tables', ['location_id'], if_not_exists=True)

    # Checks - foreign keys and status filtering
    op.create_index('ix_checks_table_id', 'checks', ['table_id'], if_not_exists=True)
    op.create_index('ix_checks_server_id', 'checks', ['server_id'], if_not_exists=True)
    op.create_index('ix_checks_location_id', 'checks', ['location_id'], if_not_exists=True)
    op.create_index('ix_checks_status', 'checks', ['status'], if_not_exists=True)
    op.create_index('ix_checks_opened_at', 'checks', ['opened_at'], if_not_exists=True)

    # Check items - foreign key and status
    op.create_index('ix_check_items_check_id', 'check_items', ['check_id'], if_not_exists=True)
    op.create_index('ix_check_items_status', 'check_items', ['status'], if_not_exists=True)

    # Check payments
    op.create_index('ix_check_payments_check_id', 'check_payments', ['check_id'], if_not_exists=True)

    # Menu items - category and availability filtering
    op.create_index('ix_menu_items_category', 'menu_items', ['category'], if_not_exists=True)
    op.create_index('ix_menu_items_location_id', 'menu_items', ['location_id'], if_not_exists=True)
    op.create_index('ix_menu_items_available', 'menu_items', ['available'], if_not_exists=True)

    # Kitchen orders - status and location filtering
    op.create_index('ix_kitchen_orders_status', 'kitchen_orders', ['status'], if_not_exists=True)
    op.create_index('ix_kitchen_orders_location_id', 'kitchen_orders', ['location_id'], if_not_exists=True)
    op.create_index('ix_kitchen_orders_check_id', 'kitchen_orders', ['check_id'], if_not_exists=True)
    op.create_index('ix_kitchen_orders_created_at', 'kitchen_orders', ['created_at'], if_not_exists=True)

    # Guest orders - status and location filtering
    op.create_index('ix_guest_orders_status', 'guest_orders', ['status'], if_not_exists=True)
    op.create_index('ix_guest_orders_table_id', 'guest_orders', ['table_id'], if_not_exists=True)
    op.create_index('ix_guest_orders_location_id', 'guest_orders', ['location_id'], if_not_exists=True)
    op.create_index('ix_guest_orders_created_at', 'guest_orders', ['created_at'], if_not_exists=True)

    # Staff users - role and active status filtering
    op.create_index('ix_staff_users_role', 'staff_users', ['role'], if_not_exists=True)
    op.create_index('ix_staff_users_is_active', 'staff_users', ['is_active'], if_not_exists=True)

    # Customers - segment and common filters
    op.create_index('ix_customers_segment', 'customers', ['segment'], if_not_exists=True)
    op.create_index('ix_customers_created_at', 'customers', ['created_at'], if_not_exists=True)

    # Inventory sessions - status filtering
    op.create_index('ix_inventory_sessions_status', 'inventory_sessions', ['status'], if_not_exists=True)
    op.create_index('ix_inventory_sessions_location_id', 'inventory_sessions', ['location_id'], if_not_exists=True)

    # Purchase orders - status filtering
    op.create_index('ix_purchase_orders_status', 'purchase_orders', ['status'], if_not_exists=True)
    op.create_index('ix_purchase_orders_supplier_id', 'purchase_orders', ['supplier_id'], if_not_exists=True)


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('ix_purchase_orders_supplier_id', table_name='purchase_orders')
    op.drop_index('ix_purchase_orders_status', table_name='purchase_orders')
    op.drop_index('ix_inventory_sessions_location_id', table_name='inventory_sessions')
    op.drop_index('ix_inventory_sessions_status', table_name='inventory_sessions')
    op.drop_index('ix_customers_created_at', table_name='customers')
    op.drop_index('ix_customers_segment', table_name='customers')
    op.drop_index('ix_staff_users_is_active', table_name='staff_users')
    op.drop_index('ix_staff_users_role', table_name='staff_users')
    op.drop_index('ix_guest_orders_created_at', table_name='guest_orders')
    op.drop_index('ix_guest_orders_location_id', table_name='guest_orders')
    op.drop_index('ix_guest_orders_table_id', table_name='guest_orders')
    op.drop_index('ix_guest_orders_status', table_name='guest_orders')
    op.drop_index('ix_kitchen_orders_created_at', table_name='kitchen_orders')
    op.drop_index('ix_kitchen_orders_check_id', table_name='kitchen_orders')
    op.drop_index('ix_kitchen_orders_location_id', table_name='kitchen_orders')
    op.drop_index('ix_kitchen_orders_status', table_name='kitchen_orders')
    op.drop_index('ix_menu_items_available', table_name='menu_items')
    op.drop_index('ix_menu_items_location_id', table_name='menu_items')
    op.drop_index('ix_menu_items_category', table_name='menu_items')
    op.drop_index('ix_check_payments_check_id', table_name='check_payments')
    op.drop_index('ix_check_items_status', table_name='check_items')
    op.drop_index('ix_check_items_check_id', table_name='check_items')
    op.drop_index('ix_checks_opened_at', table_name='checks')
    op.drop_index('ix_checks_status', table_name='checks')
    op.drop_index('ix_checks_location_id', table_name='checks')
    op.drop_index('ix_checks_server_id', table_name='checks')
    op.drop_index('ix_checks_table_id', table_name='checks')
    op.drop_index('ix_tables_location_id', table_name='tables')
    op.drop_index('ix_tables_status', table_name='tables')
