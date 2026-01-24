"""Add reconciliation, reorder, and supplier order draft tables

Revision ID: 004
Revises: 003
Create Date: 2025-01-17

Adds:
- reconciliation_results table for stock variance analysis
- reorder_proposals table for suggested orders
- supplier_order_drafts table for order generation
- shelf_zone and ended_at columns to inventory_sessions
- barcode and notes columns to inventory_lines
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to inventory_sessions
    with op.batch_alter_table('inventory_sessions', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('shelf_zone', sa.String(100), nullable=True)
        )
        batch_op.add_column(
            sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True)
        )

    # Add columns to inventory_lines
    with op.batch_alter_table('inventory_lines', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('barcode', sa.String(50), nullable=True)
        )
        batch_op.add_column(
            sa.Column('notes', sa.String(500), nullable=True)
        )

    # Create reconciliation_results table
    op.create_table(
        'reconciliation_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(),
                  sa.ForeignKey('inventory_sessions.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('product_id', sa.Integer(),
                  sa.ForeignKey('products.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        # Quantities
        sa.Column('expected_qty', sa.Numeric(10, 2), nullable=False),
        sa.Column('counted_qty', sa.Numeric(10, 2), nullable=False),
        sa.Column('delta_qty', sa.Numeric(10, 2), nullable=False),
        sa.Column('delta_value', sa.Numeric(10, 2), nullable=True),
        sa.Column('delta_percent', sa.Numeric(5, 2), nullable=True),
        # Assessment
        sa.Column('severity', sa.Enum('ok', 'warning', 'critical', name='delta_severity'),
                  default='ok', nullable=False),
        sa.Column('reason', sa.String(500), nullable=True),
        # Source info
        sa.Column('expected_source', sa.String(50), nullable=True),
        sa.Column('confidence', sa.Numeric(3, 2), nullable=True),
        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # Create reorder_proposals table
    op.create_table(
        'reorder_proposals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(),
                  sa.ForeignKey('inventory_sessions.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('product_id', sa.Integer(),
                  sa.ForeignKey('products.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('supplier_id', sa.Integer(),
                  sa.ForeignKey('suppliers.id', ondelete='SET NULL'),
                  nullable=True, index=True),
        # Quantities
        sa.Column('current_stock', sa.Numeric(10, 2), nullable=False),
        sa.Column('target_stock', sa.Numeric(10, 2), nullable=False),
        sa.Column('in_transit', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('recommended_qty', sa.Numeric(10, 2), nullable=False),
        sa.Column('rounded_qty', sa.Numeric(10, 2), nullable=False),
        sa.Column('pack_size', sa.Integer(), default=1, nullable=False),
        # Cost
        sa.Column('unit_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('line_total', sa.Numeric(10, 2), nullable=True),
        # Rationale
        sa.Column('rationale_json', sa.Text(), nullable=True),
        # User edits
        sa.Column('user_qty', sa.Numeric(10, 2), nullable=True),
        sa.Column('included', sa.Boolean(), default=True, nullable=False),
        # Timestamp
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # Create supplier_order_drafts table
    op.create_table(
        'supplier_order_drafts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('session_id', sa.Integer(),
                  sa.ForeignKey('inventory_sessions.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        sa.Column('supplier_id', sa.Integer(),
                  sa.ForeignKey('suppliers.id', ondelete='CASCADE'),
                  nullable=False, index=True),
        # Status
        sa.Column('status', sa.Enum('draft', 'finalized', 'exported', 'sent', 'cancelled',
                                     name='order_draft_status'),
                  default='draft', nullable=False),
        # Order content
        sa.Column('payload_json', sa.Text(), nullable=True),
        sa.Column('line_count', sa.Integer(), default=0, nullable=False),
        sa.Column('total_qty', sa.Numeric(10, 2), default=0, nullable=False),
        sa.Column('total_value', sa.Numeric(10, 2), nullable=True),
        # Delivery
        sa.Column('requested_delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.String(1000), nullable=True),
        # Export tracking
        sa.Column('exported_csv_path', sa.String(500), nullable=True),
        sa.Column('exported_pdf_path', sa.String(500), nullable=True),
        sa.Column('email_sent_at', sa.DateTime(timezone=True), nullable=True),
        # Purchase order link
        sa.Column('purchase_order_id', sa.Integer(),
                  sa.ForeignKey('purchase_orders.id', ondelete='SET NULL'),
                  nullable=True),
        # Creator
        sa.Column('created_by', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL'),
                  nullable=True),
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('supplier_order_drafts')
    op.drop_table('reorder_proposals')
    op.drop_table('reconciliation_results')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS order_draft_status")
    op.execute("DROP TYPE IF EXISTS delta_severity")

    # Remove columns from inventory_lines
    with op.batch_alter_table('inventory_lines', schema=None) as batch_op:
        batch_op.drop_column('notes')
        batch_op.drop_column('barcode')

    # Remove columns from inventory_sessions
    with op.batch_alter_table('inventory_sessions', schema=None) as batch_op:
        batch_op.drop_column('ended_at')
        batch_op.drop_column('shelf_zone')
