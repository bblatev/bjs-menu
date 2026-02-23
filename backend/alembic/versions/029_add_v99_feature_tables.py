"""Add V99 feature tables

Revision ID: v99_001
Revises: 028_schema_hardening
Create Date: 2026-02-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'v99_001'
down_revision = '028_schema_hardening'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IoT Sensors
    op.create_table('iot_sensors',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('device_type', sa.String(50), nullable=False),
        sa.Column('device_id', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('location', sa.String(200)),
        sa.Column('zone', sa.String(100)),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_reading_at', sa.DateTime(timezone=True)),
        sa.Column('last_reading_value', sa.Float()),
        sa.Column('min_threshold', sa.Float()),
        sa.Column('max_threshold', sa.Float()),
        sa.Column('alert_enabled', sa.Boolean(), default=True),
        sa.Column('metadata', sa.JSON(), default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('iot_readings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sensor_id', sa.Integer(), sa.ForeignKey('iot_sensors.id'), nullable=False, index=True),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(20)),
        sa.Column('is_in_range', sa.Boolean(), default=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    op.create_table('iot_alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sensor_id', sa.Integer(), sa.ForeignKey('iot_sensors.id'), nullable=False, index=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), default='warning'),
        sa.Column('reading_value', sa.Float()),
        sa.Column('threshold_value', sa.Float()),
        sa.Column('message', sa.Text()),
        sa.Column('acknowledged', sa.Boolean(), default=False),
        sa.Column('acknowledged_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Digital Signage
    op.create_table('signage_content',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('content_type', sa.String(50), nullable=False),
        sa.Column('template', sa.String(100)),
        sa.Column('data', sa.JSON(), default=dict),
        sa.Column('duration_seconds', sa.Integer(), default=30),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('schedule_start', sa.DateTime(timezone=True)),
        sa.Column('schedule_end', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('digital_displays',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('location', sa.String(200)),
        sa.Column('display_type', sa.String(50), default='menu_board'),
        sa.Column('resolution', sa.String(20), default='1920x1080'),
        sa.Column('orientation', sa.String(20), default='landscape'),
        sa.Column('is_online', sa.Boolean(), default=False),
        sa.Column('last_heartbeat', sa.DateTime(timezone=True)),
        sa.Column('current_content_id', sa.Integer(), sa.ForeignKey('signage_content.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Pour Tracking
    op.create_table('pour_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('staff_id', sa.Integer(), sa.ForeignKey('users.id'), index=True),
        sa.Column('product_id', sa.Integer(), index=True),
        sa.Column('product_name', sa.String(200)),
        sa.Column('expected_ml', sa.Float(), nullable=False),
        sa.Column('actual_ml', sa.Float(), nullable=False),
        sa.Column('variance_ml', sa.Float()),
        sa.Column('variance_pct', sa.Float()),
        sa.Column('pour_type', sa.String(30), default='standard'),
        sa.Column('station', sa.String(100)),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # Staff Skills
    op.create_table('staff_skills',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('staff_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('skill_name', sa.String(100), nullable=False),
        sa.Column('skill_category', sa.String(50)),
        sa.Column('proficiency_level', sa.Integer(), default=1),
        sa.Column('certified', sa.Boolean(), default=False),
        sa.Column('certified_date', sa.Date()),
        sa.Column('expiry_date', sa.Date()),
        sa.Column('assessed_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('notes', sa.Text()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Geo-Fencing
    op.create_table('geo_fences',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('radius_meters', sa.Integer(), default=100),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('geo_clock_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('staff_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('event_type', sa.String(20), nullable=False),
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('distance_meters', sa.Float()),
        sa.Column('within_fence', sa.Boolean()),
        sa.Column('override_reason', sa.Text()),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Shelf Life
    op.create_table('shelf_life_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('product_id', sa.Integer(), index=True),
        sa.Column('product_name', sa.String(200), nullable=False),
        sa.Column('batch_id', sa.String(100)),
        sa.Column('received_date', sa.Date(), nullable=False),
        sa.Column('expiry_date', sa.Date(), nullable=False),
        sa.Column('quantity', sa.Float(), default=0),
        sa.Column('unit', sa.String(20)),
        sa.Column('storage_location', sa.String(100)),
        sa.Column('status', sa.String(30), default='fresh'),
        sa.Column('discarded_at', sa.DateTime(timezone=True)),
        sa.Column('discarded_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Social Posts
    op.create_table('social_posts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('venue_id', sa.Integer(), sa.ForeignKey('venues.id'), nullable=False, index=True),
        sa.Column('platform', sa.String(30), nullable=False),
        sa.Column('content_type', sa.String(50)),
        sa.Column('caption', sa.Text(), nullable=False),
        sa.Column('hashtags', sa.JSON(), default=list),
        sa.Column('image_url', sa.String(500)),
        sa.Column('scheduled_at', sa.DateTime(timezone=True)),
        sa.Column('published_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('engagement_likes', sa.Integer(), default=0),
        sa.Column('engagement_comments', sa.Integer(), default=0),
        sa.Column('engagement_shares', sa.Integer(), default=0),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Multi-Tenant
    op.create_table('tenants',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('slug', sa.String(100), unique=True, nullable=False),
        sa.Column('plan', sa.String(50), default='standard'),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('suspended_at', sa.DateTime(timezone=True)),
        sa.Column('suspension_reason', sa.Text()),
        sa.Column('max_venues', sa.Integer(), default=5),
        sa.Column('max_users', sa.Integer(), default=50),
        sa.Column('settings', sa.JSON(), default=dict),
        sa.Column('billing_email', sa.String(200)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table('tenant_usage',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('tenant_id', sa.Integer(), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('month', sa.Date(), nullable=False),
        sa.Column('orders_count', sa.Integer(), default=0),
        sa.Column('api_calls', sa.Integer(), default=0),
        sa.Column('storage_mb', sa.Float(), default=0),
        sa.Column('active_venues', sa.Integer(), default=0),
        sa.Column('active_users', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('tenant_usage')
    op.drop_table('tenants')
    op.drop_table('social_posts')
    op.drop_table('shelf_life_items')
    op.drop_table('geo_clock_events')
    op.drop_table('geo_fences')
    op.drop_table('staff_skills')
    op.drop_table('pour_records')
    op.drop_table('digital_displays')
    op.drop_table('signage_content')
    op.drop_table('iot_alerts')
    op.drop_table('iot_readings')
    op.drop_table('iot_sensors')
