"""024: Add UNIQUE constraints for data integrity.

Adds unique indexes to prevent duplicate records:
- customers.email (partial unique, allows NULL)
- customers.phone (unique per location)
- tables.number + location_id (composite unique)
"""

from alembic import op

revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Customer email uniqueness (SQLite supports unique indexes)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_customers_email_unique
        ON customers(email) WHERE email IS NOT NULL
    """)

    # Customer phone uniqueness per location
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_customers_phone_location
        ON customers(phone, location_id) WHERE phone IS NOT NULL
    """)

    # Table number uniqueness per location
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_tables_number_location
        ON tables(number, location_id)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_customers_email_unique")
    op.execute("DROP INDEX IF EXISTS ix_customers_phone_location")
    op.execute("DROP INDEX IF EXISTS ix_tables_number_location")
