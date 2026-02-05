"""Add missing staff_users, waitlist, and reservations tables.

Revision ID: 014
Revises: 013
Create Date: 2026-02-05

These tables are required for the staff management and reservation APIs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as pgEnum


# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types first (only if they don't exist)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reservationstatus') THEN
                CREATE TYPE reservationstatus AS ENUM ('PENDING', 'CONFIRMED', 'SEATED', 'COMPLETED', 'CANCELLED', 'NO_SHOW');
            END IF;
        END$$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'bookingsource') THEN
                CREATE TYPE bookingsource AS ENUM ('WEBSITE', 'PHONE', 'WALK_IN', 'GOOGLE', 'APP', 'THIRD_PARTY');
            END IF;
        END$$;
    """)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'waitliststatus') THEN
                CREATE TYPE waitliststatus AS ENUM ('WAITING', 'NOTIFIED', 'SEATED', 'LEFT', 'CANCELLED');
            END IF;
        END$$;
    """)

    # Create staff_users table
    op.create_table('staff_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('pin_hash', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('hourly_rate', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('max_hours_week', sa.Integer(), nullable=False, server_default=sa.text('40')),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('commission_percentage', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('service_fee_percentage', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('auto_logout_after_close', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_staff_users_id', 'staff_users', ['id'], unique=False)
    op.create_index('ix_staff_users_location_id', 'staff_users', ['location_id'], unique=False)

    # Create reservation_settings table
    op.create_table('reservation_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('min_party_size', sa.Integer(), nullable=True, server_default=sa.text('1')),
        sa.Column('max_party_size', sa.Integer(), nullable=True, server_default=sa.text('20')),
        sa.Column('default_duration_minutes', sa.Integer(), nullable=True, server_default=sa.text('90')),
        sa.Column('booking_window_days', sa.Integer(), nullable=True, server_default=sa.text('30')),
        sa.Column('min_advance_hours', sa.Integer(), nullable=True, server_default=sa.text('2')),
        sa.Column('slot_interval_minutes', sa.Integer(), nullable=True, server_default=sa.text('15')),
        sa.Column('first_seating_time', sa.String(length=10), nullable=True),
        sa.Column('last_seating_time', sa.String(length=10), nullable=True),
        sa.Column('max_covers_per_slot', sa.Integer(), nullable=True, server_default=sa.text('50')),
        sa.Column('buffer_between_seatings', sa.Integer(), nullable=True, server_default=sa.text('15')),
        sa.Column('require_confirmation', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('auto_confirm', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('send_confirmation_email', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('send_confirmation_sms', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('send_reminder_24h', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('send_reminder_2h', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('require_credit_card', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('require_credit_card_above', sa.Integer(), nullable=True, server_default=sa.text('6')),
        sa.Column('no_show_fee_per_person', sa.Float(), nullable=True, server_default=sa.text('0')),
        sa.Column('no_show_window_minutes', sa.Integer(), nullable=True, server_default=sa.text('15')),
        sa.Column('enable_waitlist', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('waitlist_sms_notification', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('max_waitlist_size', sa.Integer(), nullable=True, server_default=sa.text('20')),
        sa.Column('google_reserve_enabled', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('online_booking_enabled', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('location_id')
    )
    op.create_index('ix_reservation_settings_id', 'reservation_settings', ['id'], unique=False)

    # Create reservations table
    reservationstatus = pgEnum('PENDING', 'CONFIRMED', 'SEATED', 'COMPLETED', 'CANCELLED', 'NO_SHOW',
                                name='reservationstatus', create_type=False)
    bookingsource = pgEnum('WEBSITE', 'PHONE', 'WALK_IN', 'GOOGLE', 'APP', 'THIRD_PARTY',
                           name='bookingsource', create_type=False)

    op.create_table('reservations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('guest_name', sa.String(length=200), nullable=False),
        sa.Column('guest_phone', sa.String(length=50), nullable=True),
        sa.Column('guest_email', sa.String(length=255), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('party_size', sa.Integer(), nullable=False),
        sa.Column('reservation_date', sa.DateTime(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=True, server_default=sa.text('90')),
        sa.Column('table_ids', sa.JSON(), nullable=True),
        sa.Column('seating_preference', sa.String(length=100), nullable=True),
        sa.Column('status', reservationstatus, nullable=True),
        sa.Column('source', bookingsource, nullable=True),
        sa.Column('confirmation_code', sa.String(length=20), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True),
        sa.Column('reminder_sent_at', sa.DateTime(), nullable=True),
        sa.Column('reminder_24h_sent', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('reminder_2h_sent', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('arrived_at', sa.DateTime(), nullable=True),
        sa.Column('seated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('credit_card_on_file', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('no_show_fee', sa.Float(), nullable=True),
        sa.Column('no_show_charged', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('special_requests', sa.Text(), nullable=True),
        sa.Column('occasion', sa.String(length=100), nullable=True),
        sa.Column('dietary_restrictions', sa.JSON(), nullable=True),
        sa.Column('is_vip', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('vip_notes', sa.Text(), nullable=True),
        sa.Column('internal_notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('confirmation_code')
    )
    op.create_index('ix_reservations_id', 'reservations', ['id'], unique=False)
    op.create_index('ix_reservations_location_id', 'reservations', ['location_id'], unique=False)
    op.create_index('ix_reservations_reservation_date', 'reservations', ['reservation_date'], unique=False)

    # Create waitlist table
    waitliststatus = pgEnum('WAITING', 'NOTIFIED', 'SEATED', 'LEFT', 'CANCELLED',
                            name='waitliststatus', create_type=False)

    op.create_table('waitlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('guest_name', sa.String(length=200), nullable=False),
        sa.Column('guest_phone', sa.String(length=50), nullable=True),
        sa.Column('customer_id', sa.Integer(), nullable=True),
        sa.Column('party_size', sa.Integer(), nullable=False),
        sa.Column('seating_preference', sa.String(length=100), nullable=True),
        sa.Column('added_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('estimated_wait_minutes', sa.Integer(), nullable=True),
        sa.Column('quoted_wait_minutes', sa.Integer(), nullable=True),
        sa.Column('actual_wait_minutes', sa.Integer(), nullable=True),
        sa.Column('status', waitliststatus, nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('sms_confirmation_sent', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('sms_ready_sent', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('sms_ready_sent_at', sa.DateTime(), nullable=True),
        sa.Column('table_ids', sa.JSON(), nullable=True),
        sa.Column('seated_at', sa.DateTime(), nullable=True),
        sa.Column('left_at', sa.DateTime(), nullable=True),
        sa.Column('left_reason', sa.String(length=200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_waitlist_id', 'waitlist', ['id'], unique=False)
    op.create_index('ix_waitlist_location_id', 'waitlist', ['location_id'], unique=False)
    op.create_index('ix_waitlist_status', 'waitlist', ['status'], unique=False)

    # Create shifts table (depends on staff_users)
    op.create_table('shifts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('shift_type', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.Column('break_minutes', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'scheduled'")),
        sa.Column('position', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staff_users.id'], ),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_shifts_id', 'shifts', ['id'], unique=False)
    op.create_index('ix_shifts_staff_id', 'shifts', ['staff_id'], unique=False)
    op.create_index('ix_shifts_date', 'shifts', ['date'], unique=False)

    # Create time_clock_entries table (depends on staff_users)
    op.create_table('time_clock_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('clock_in', sa.DateTime(), nullable=False),
        sa.Column('clock_out', sa.DateTime(), nullable=True),
        sa.Column('break_start', sa.DateTime(), nullable=True),
        sa.Column('break_end', sa.DateTime(), nullable=True),
        sa.Column('total_hours', sa.Float(), nullable=True),
        sa.Column('break_hours', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'clocked_in'")),
        sa.Column('clock_in_method', sa.String(length=50), nullable=False, server_default=sa.text("'pin'")),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staff_users.id'], ),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_time_clock_entries_id', 'time_clock_entries', ['id'], unique=False)
    op.create_index('ix_time_clock_entries_staff_id', 'time_clock_entries', ['staff_id'], unique=False)

    # Create tip_pools table
    op.create_table('tip_pools',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('shift', sa.String(length=50), nullable=False),
        sa.Column('total_tips_cash', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_tips_card', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_tips', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('participants_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('distribution_method', sa.String(length=50), nullable=False, server_default=sa.text("'equal'")),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'open'")),
        sa.Column('distributed_at', sa.DateTime(), nullable=True),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tip_pools_id', 'tip_pools', ['id'], unique=False)
    op.create_index('ix_tip_pools_date', 'tip_pools', ['date'], unique=False)

    # Create tip_distributions table (depends on tip_pools and staff_users)
    op.create_table('tip_distributions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pool_id', sa.Integer(), nullable=False),
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('hours_worked', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('points', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('share_percentage', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('amount', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_paid', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['pool_id'], ['tip_pools.id'], ),
        sa.ForeignKeyConstraint(['staff_id'], ['staff_users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tip_distributions_id', 'tip_distributions', ['id'], unique=False)

    # Create time_off_requests table (depends on staff_users)
    op.create_table('time_off_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False, server_default=sa.text("'vacation'")),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'pending'")),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staff_users.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_time_off_requests_id', 'time_off_requests', ['id'], unique=False)
    op.create_index('ix_time_off_requests_staff_id', 'time_off_requests', ['staff_id'], unique=False)

    # Create staff_performance_metrics table (depends on staff_users)
    op.create_table('staff_performance_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('period', sa.String(length=50), nullable=False),
        sa.Column('period_date', sa.Date(), nullable=False),
        sa.Column('sales_amount', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('orders_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('avg_ticket', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('items_sold', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('tips_received', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('customer_rating', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('reviews_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('hours_worked', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('sales_per_hour', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('late_arrivals', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('absences', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('upsell_rate', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('table_turnover', sa.Float(), nullable=False, server_default=sa.text('0')),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staff_users.id'], ),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_staff_performance_metrics_id', 'staff_performance_metrics', ['id'], unique=False)
    op.create_index('ix_staff_performance_metrics_staff_id', 'staff_performance_metrics', ['staff_id'], unique=False)

    # Create table_assignments table (depends on staff_users)
    op.create_table('table_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('table_id', sa.Integer(), nullable=True),
        sa.Column('area', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('location_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staff_users.id'], ),
        sa.ForeignKeyConstraint(['table_id'], ['tables.id'], ),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_table_assignments_id', 'table_assignments', ['id'], unique=False)
    op.create_index('ix_table_assignments_staff_id', 'table_assignments', ['staff_id'], unique=False)


def downgrade() -> None:
    op.drop_table('table_assignments')
    op.drop_table('staff_performance_metrics')
    op.drop_table('time_off_requests')
    op.drop_table('tip_distributions')
    op.drop_table('tip_pools')
    op.drop_table('time_clock_entries')
    op.drop_table('shifts')
    op.drop_table('waitlist')
    op.drop_table('reservations')
    op.drop_table('reservation_settings')
    op.drop_table('staff_users')

    op.execute("DROP TYPE IF EXISTS waitliststatus")
    op.execute("DROP TYPE IF EXISTS bookingsource")
    op.execute("DROP TYPE IF EXISTS reservationstatus")
