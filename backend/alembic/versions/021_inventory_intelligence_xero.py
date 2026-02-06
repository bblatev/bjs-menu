"""021: Add inventory_snapshots, xero_connections, xero_sync_logs, xero_account_mappings tables.

Supports Inventory Intelligence (snapshots, cycle counts) and Xero accounting integration.
"""

from alembic import op
import sqlalchemy as sa

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Inventory Snapshots
    op.execute("""
        CREATE TABLE IF NOT EXISTS inventory_snapshots (
            id SERIAL PRIMARY KEY,
            location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
            name VARCHAR(200) NOT NULL,
            notes TEXT,
            snapshot_data JSONB NOT NULL DEFAULT '[]',
            total_items INTEGER NOT NULL DEFAULT 0,
            total_value NUMERIC(12,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_location ON inventory_snapshots(location_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_created ON inventory_snapshots(created_at DESC)")

    # Xero Connections
    op.execute("""
        CREATE TABLE IF NOT EXISTS xero_connections (
            id SERIAL PRIMARY KEY,
            organization_name VARCHAR(200),
            tenant_id VARCHAR(200),
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TIMESTAMP WITH TIME ZONE,
            connected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_sync_at TIMESTAMP WITH TIME ZONE,
            is_active BOOLEAN DEFAULT true,
            auto_sync_enabled BOOLEAN DEFAULT false,
            sync_invoices BOOLEAN DEFAULT true,
            sync_bills BOOLEAN DEFAULT true,
            sync_bank_transactions BOOLEAN DEFAULT true,
            sync_contacts BOOLEAN DEFAULT false,
            sync_frequency VARCHAR(20) DEFAULT 'daily'
        )
    """)

    # Xero Sync Logs
    op.execute("""
        CREATE TABLE IF NOT EXISTS xero_sync_logs (
            id SERIAL PRIMARY KEY,
            sync_type VARCHAR(50) NOT NULL,
            records_synced INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE,
            error_message TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_xero_logs_started ON xero_sync_logs(started_at DESC)")

    # Xero Account Mappings
    op.execute("""
        CREATE TABLE IF NOT EXISTS xero_account_mappings (
            id SERIAL PRIMARY KEY,
            local_category VARCHAR(100) NOT NULL,
            xero_account_code VARCHAR(50) NOT NULL,
            xero_account_name VARCHAR(200),
            sync_direction VARCHAR(10) DEFAULT 'push',
            is_active BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # Seed default Xero mappings
    op.execute("""
        INSERT INTO xero_account_mappings (local_category, xero_account_code, xero_account_name, sync_direction) VALUES
        ('Food Revenue', '200', 'Sales - Food', 'push'),
        ('Beverage Revenue', '201', 'Sales - Beverage', 'push'),
        ('Food COGS', '500', 'Cost of Goods - Food', 'push'),
        ('Beverage COGS', '501', 'Cost of Goods - Beverage', 'push'),
        ('Labor', '600', 'Wages & Salaries', 'push'),
        ('Rent', '700', 'Occupancy Costs', 'push'),
        ('Utilities', '710', 'Utilities', 'push'),
        ('Supplies', '520', 'Operating Supplies', 'push'),
        ('Accounts Payable', '800', 'Accounts Payable', 'both'),
        ('Bank Account', '090', 'Business Bank Account', 'both')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS xero_account_mappings CASCADE")
    op.execute("DROP TABLE IF EXISTS xero_sync_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS xero_connections CASCADE")
    op.execute("DROP TABLE IF EXISTS inventory_snapshots CASCADE")
