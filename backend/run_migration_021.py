"""Run migration 021: Inventory Intelligence + Xero tables."""
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

statements = [
    """CREATE TABLE IF NOT EXISTS inventory_snapshots (
        id SERIAL PRIMARY KEY,
        location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
        name VARCHAR(200) NOT NULL,
        notes TEXT,
        snapshot_data JSONB NOT NULL DEFAULT '[]'::jsonb,
        total_items INTEGER NOT NULL DEFAULT 0,
        total_value NUMERIC(12,2) NOT NULL DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
    )""",
    "CREATE INDEX IF NOT EXISTS idx_snapshots_location ON inventory_snapshots(location_id)",
    "CREATE INDEX IF NOT EXISTS idx_snapshots_created ON inventory_snapshots(created_at DESC)",

    """CREATE TABLE IF NOT EXISTS xero_connections (
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
    )""",

    """CREATE TABLE IF NOT EXISTS xero_sync_logs (
        id SERIAL PRIMARY KEY,
        sync_type VARCHAR(50) NOT NULL,
        records_synced INTEGER NOT NULL DEFAULT 0,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE,
        error_message TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_xero_logs_started ON xero_sync_logs(started_at DESC)",

    """CREATE TABLE IF NOT EXISTS xero_account_mappings (
        id SERIAL PRIMARY KEY,
        local_category VARCHAR(100) NOT NULL,
        xero_account_code VARCHAR(50) NOT NULL,
        xero_account_name VARCHAR(200),
        sync_direction VARCHAR(10) DEFAULT 'push',
        is_active BOOLEAN DEFAULT true,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    )""",
]

for s in statements:
    db.execute(text(s))
db.commit()
print("Tables created!")

# Seed Xero mappings
db.execute(text("""
    INSERT INTO xero_account_mappings (local_category, xero_account_code, xero_account_name, sync_direction)
    SELECT v.cat, v.code, v.name, v.dir FROM (VALUES
        ('Food Revenue', '200', 'Sales - Food', 'push'),
        ('Beverage Revenue', '201', 'Sales - Beverage', 'push'),
        ('Food COGS', '500', 'Cost of Goods - Food', 'push'),
        ('Beverage COGS', '501', 'Cost of Goods - Beverage', 'push'),
        ('Labor', '600', 'Wages and Salaries', 'push'),
        ('Rent', '700', 'Occupancy Costs', 'push'),
        ('Utilities', '710', 'Utilities', 'push'),
        ('Supplies', '520', 'Operating Supplies', 'push'),
        ('Accounts Payable', '800', 'Accounts Payable', 'both'),
        ('Bank Account', '090', 'Business Bank Account', 'both')
    ) AS v(cat, code, name, dir)
    WHERE NOT EXISTS (SELECT 1 FROM xero_account_mappings LIMIT 1)
"""))
db.commit()
db.close()
print("Migration 021 complete!")
