"""Add advanced competitor features tables

Revision ID: 005
Revises: 004
Create Date: 2025-01-22

Adds 25 feature areas to match top competitors:
- Waste tracking & forecasting
- Labor forecasting & compliance
- Order throttling & kitchen capacity
- WiFi marketing sessions
- Menu A/B experiments
- Dynamic/surge pricing
- Curbside pickup
- Delivery dispatch multi-provider
- Review sentiment analysis
- Gift cards
- Tip pooling
- Cross-sell recommendations
- Customer journey analytics
- Shelf life/expiration tracking
- Prep lists
- Kitchen load balancing
- Wait time prediction
- Allergen profiles
- Sustainability/ESG metrics
- IoT equipment monitoring
- Vendor scorecards
- Virtual brands/ghost kitchen
- Table turn optimization
- Order status notifications
- Supply chain traceability
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create waste_category enum
    waste_category = sa.Enum(
        'overproduction', 'spoilage', 'plate_waste', 'prep_waste',
        'expired', 'damaged', 'other',
        name='waste_category'
    )
    waste_category.create(op.get_bind(), checkfirst=True)

    # Create sentiment enum
    sentiment = sa.Enum('positive', 'neutral', 'negative', name='sentiment_type')
    sentiment.create(op.get_bind(), checkfirst=True)

    # 1. Waste Tracking
    op.create_table(
        'waste_tracking_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('category', waste_category, nullable=False),
        sa.Column('weight_kg', sa.Numeric(10, 3), nullable=False),
        sa.Column('cost_estimate', sa.Numeric(10, 2), nullable=True),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('recorded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('image_url', sa.String(500), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'waste_forecasts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.Column('predicted_kg', sa.Numeric(10, 3), nullable=False),
        sa.Column('predicted_cost', sa.Numeric(10, 2), nullable=True),
        sa.Column('confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 2. Labor Forecasting
    op.create_table(
        'labor_forecasts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('forecast_date', sa.Date(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(50), nullable=True),
        sa.Column('predicted_hours', sa.Numeric(6, 2), nullable=False),
        sa.Column('predicted_covers', sa.Integer(), nullable=True),
        sa.Column('predicted_revenue', sa.Numeric(10, 2), nullable=True),
        sa.Column('confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('factors_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'labor_compliance_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False),
        sa.Column('rule_name', sa.String(100), nullable=False),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('parameters_json', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'labor_compliance_violations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('labor_compliance_rules.id'), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column('violation_type', sa.String(50), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('violation_date', sa.Date(), nullable=False),
        sa.Column('resolved', sa.Boolean(), default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 3. Order Throttling / Kitchen Capacity
    op.create_table(
        'kitchen_capacity_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, unique=True),
        sa.Column('max_orders_per_15min', sa.Integer(), default=20),
        sa.Column('max_items_per_15min', sa.Integer(), default=100),
        sa.Column('auto_throttle_enabled', sa.Boolean(), default=True),
        sa.Column('throttle_threshold_percent', sa.Integer(), default=80),
        sa.Column('is_paused', sa.Boolean(), default=False),
        sa.Column('paused_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'throttle_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('load_percent', sa.Integer(), nullable=True),
        sa.Column('orders_affected', sa.Integer(), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 4. WiFi Marketing
    op.create_table(
        'wifi_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('mac_address', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True, index=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('marketing_opt_in', sa.Boolean(), default=False),
        sa.Column('visit_count', sa.Integer(), default=1),
        sa.Column('first_visit', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_visit', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('session_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 5. Menu Experiments
    op.create_table(
        'menu_experiments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('hypothesis', sa.String(500), nullable=True),
        sa.Column('menu_item_id', sa.Integer(), nullable=True),
        sa.Column('variable', sa.String(50), nullable=False),
        sa.Column('control_value', sa.String(200), nullable=True),
        sa.Column('test_value', sa.String(200), nullable=True),
        sa.Column('traffic_split', sa.Numeric(3, 2), default=0.5),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('control_orders', sa.Integer(), default=0),
        sa.Column('test_orders', sa.Integer(), default=0),
        sa.Column('control_revenue', sa.Numeric(10, 2), default=0),
        sa.Column('test_revenue', sa.Numeric(10, 2), default=0),
        sa.Column('winner', sa.String(20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 6. Dynamic Pricing
    op.create_table(
        'dynamic_pricing_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('menu_item_id', sa.Integer(), nullable=True),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('base_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('min_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('max_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('surge_multiplier_max', sa.Numeric(3, 2), default=1.5),
        sa.Column('demand_threshold_low', sa.Integer(), default=30),
        sa.Column('demand_threshold_high', sa.Integer(), default=80),
        sa.Column('time_based_rules_json', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'pricing_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('dynamic_pricing_rules.id'), nullable=True),
        sa.Column('original_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('adjusted_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('multiplier', sa.Numeric(3, 2), nullable=False),
        sa.Column('demand_level', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 7. Curbside Pickup
    op.create_table(
        'curbside_pickups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('order_id', sa.Integer(), nullable=False, index=True),
        sa.Column('customer_name', sa.String(100), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('vehicle_description', sa.String(200), nullable=True),
        sa.Column('parking_spot', sa.String(20), nullable=True),
        sa.Column('status', sa.String(30), default='pending'),
        sa.Column('scheduled_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('arrived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 8. Delivery Dispatch
    op.create_table(
        'delivery_providers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False),
        sa.Column('provider_name', sa.String(50), nullable=False),
        sa.Column('api_key_encrypted', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('priority', sa.Integer(), default=1),
        sa.Column('commission_percent', sa.Numeric(4, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'delivery_dispatches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('order_id', sa.Integer(), nullable=False, index=True),
        sa.Column('provider_id', sa.Integer(), sa.ForeignKey('delivery_providers.id'), nullable=True),
        sa.Column('provider_name', sa.String(50), nullable=True),
        sa.Column('external_delivery_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), default='pending'),
        sa.Column('pickup_address', sa.String(300), nullable=True),
        sa.Column('delivery_address', sa.String(300), nullable=True),
        sa.Column('quoted_fee', sa.Numeric(8, 2), nullable=True),
        sa.Column('actual_fee', sa.Numeric(8, 2), nullable=True),
        sa.Column('eta_minutes', sa.Integer(), nullable=True),
        sa.Column('driver_name', sa.String(100), nullable=True),
        sa.Column('driver_phone', sa.String(20), nullable=True),
        sa.Column('tracking_url', sa.String(500), nullable=True),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('picked_up_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 9. Sentiment Analysis
    op.create_table(
        'review_sentiments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('external_review_id', sa.String(100), nullable=True),
        sa.Column('review_text', sa.Text(), nullable=True),
        sa.Column('rating', sa.Integer(), nullable=True),
        sa.Column('sentiment', sentiment, nullable=True),
        sa.Column('sentiment_score', sa.Numeric(4, 3), nullable=True),
        sa.Column('key_phrases_json', sa.Text(), nullable=True),
        sa.Column('topics_json', sa.Text(), nullable=True),
        sa.Column('requires_response', sa.Boolean(), default=False),
        sa.Column('response_sent', sa.Boolean(), default=False),
        sa.Column('suggested_response', sa.Text(), nullable=True),
        sa.Column('review_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 10. Gift Cards
    op.create_table(
        'gift_card_programs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('card_prefix', sa.String(10), nullable=True),
        sa.Column('min_amount', sa.Numeric(10, 2), default=5),
        sa.Column('max_amount', sa.Numeric(10, 2), default=500),
        sa.Column('expiry_months', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'gift_cards',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('program_id', sa.Integer(), sa.ForeignKey('gift_card_programs.id'), nullable=True),
        sa.Column('card_number', sa.String(20), nullable=False, unique=True),
        sa.Column('pin_hash', sa.String(100), nullable=True),
        sa.Column('initial_balance', sa.Numeric(10, 2), nullable=False),
        sa.Column('current_balance', sa.Numeric(10, 2), nullable=False),
        sa.Column('purchaser_email', sa.String(255), nullable=True),
        sa.Column('recipient_email', sa.String(255), nullable=True),
        sa.Column('recipient_name', sa.String(100), nullable=True),
        sa.Column('message', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'gift_card_transactions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('card_id', sa.Integer(), sa.ForeignKey('gift_cards.id'), nullable=False, index=True),
        sa.Column('transaction_type', sa.String(20), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('balance_after', sa.Numeric(10, 2), nullable=False),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 11. Tip Pooling
    op.create_table(
        'tip_pool_configurations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('pool_type', sa.String(30), nullable=False),
        sa.Column('role_shares_json', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'tip_pool_distributions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('configuration_id', sa.Integer(), sa.ForeignKey('tip_pool_configurations.id'), nullable=False),
        sa.Column('distribution_date', sa.Date(), nullable=False),
        sa.Column('total_tips', sa.Numeric(10, 2), nullable=False),
        sa.Column('distributions_json', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 12. Cross-Sell
    op.create_table(
        'cross_sell_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('trigger_item_id', sa.Integer(), nullable=True),
        sa.Column('trigger_category', sa.String(100), nullable=True),
        sa.Column('recommend_item_id', sa.Integer(), nullable=True),
        sa.Column('recommend_category', sa.String(100), nullable=True),
        sa.Column('priority', sa.Integer(), default=1),
        sa.Column('conversion_rate', sa.Numeric(4, 3), default=0),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'cross_sell_impressions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('cross_sell_rules.id'), nullable=False, index=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('shown', sa.Boolean(), default=True),
        sa.Column('clicked', sa.Boolean(), default=False),
        sa.Column('converted', sa.Boolean(), default=False),
        sa.Column('revenue_attributed', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 13. Customer Journey
    op.create_table(
        'customer_journey_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(), nullable=True, index=True),
        sa.Column('session_id', sa.String(100), nullable=True, index=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=True),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('channel', sa.String(30), nullable=True),
        sa.Column('source', sa.String(100), nullable=True),
        sa.Column('properties_json', sa.Text(), nullable=True),
        sa.Column('revenue', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 14. Shelf Life / Expiration
    op.create_table(
        'product_shelf_life_configs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, unique=True),
        sa.Column('shelf_life_days', sa.Integer(), nullable=False),
        sa.Column('alert_days_before', sa.Integer(), default=3),
        sa.Column('requires_fifo', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'inventory_batches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('batch_number', sa.String(50), nullable=True),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False),
        sa.Column('received_date', sa.Date(), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 15. Prep Lists
    op.create_table(
        'prep_lists',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('prep_date', sa.Date(), nullable=False),
        sa.Column('station', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('forecast_covers', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'prep_list_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('prep_list_id', sa.Integer(), sa.ForeignKey('prep_lists.id'), nullable=False, index=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('item_name', sa.String(100), nullable=False),
        sa.Column('target_qty', sa.Numeric(10, 2), nullable=False),
        sa.Column('unit', sa.String(20), nullable=True),
        sa.Column('actual_qty', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('notes', sa.String(300), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 16. Kitchen Load Balancing
    op.create_table(
        'kitchen_stations',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('station_type', sa.String(30), nullable=True),
        sa.Column('max_concurrent_orders', sa.Integer(), default=5),
        sa.Column('avg_prep_time_minutes', sa.Integer(), default=10),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'kitchen_station_assignments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('station_id', sa.Integer(), sa.ForeignKey('kitchen_stations.id'), nullable=False, index=True),
        sa.Column('order_id', sa.Integer(), nullable=False, index=True),
        sa.Column('order_item_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), default='queued'),
        sa.Column('priority', sa.Integer(), default=1),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 17. Wait Time Prediction
    op.create_table(
        'wait_time_predictions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('order_id', sa.Integer(), nullable=True, index=True),
        sa.Column('party_size', sa.Integer(), nullable=True),
        sa.Column('order_items_count', sa.Integer(), nullable=True),
        sa.Column('current_queue_size', sa.Integer(), nullable=True),
        sa.Column('day_of_week', sa.Integer(), nullable=True),
        sa.Column('hour_of_day', sa.Integer(), nullable=True),
        sa.Column('predicted_minutes', sa.Integer(), nullable=False),
        sa.Column('actual_minutes', sa.Integer(), nullable=True),
        sa.Column('prediction_error', sa.Integer(), nullable=True),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 18. Allergens
    op.create_table(
        'allergen_profiles',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=True),
        sa.Column('menu_item_id', sa.Integer(), nullable=True),
        sa.Column('allergens_json', sa.Text(), nullable=True),
        sa.Column('may_contain_json', sa.Text(), nullable=True),
        sa.Column('dietary_flags_json', sa.Text(), nullable=True),
        sa.Column('cross_contact_risk', sa.Boolean(), default=False),
        sa.Column('verified', sa.Boolean(), default=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 19. Sustainability / ESG
    op.create_table(
        'sustainability_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('metric_date', sa.Date(), nullable=False),
        sa.Column('energy_kwh', sa.Numeric(10, 2), nullable=True),
        sa.Column('water_liters', sa.Numeric(10, 2), nullable=True),
        sa.Column('waste_kg', sa.Numeric(10, 2), nullable=True),
        sa.Column('recycled_kg', sa.Numeric(10, 2), nullable=True),
        sa.Column('composted_kg', sa.Numeric(10, 2), nullable=True),
        sa.Column('local_sourcing_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('carbon_kg', sa.Numeric(10, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 20. IoT Equipment Monitoring
    op.create_table(
        'equipment_sensors',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False),
        sa.Column('equipment_name', sa.String(100), nullable=False),
        sa.Column('equipment_type', sa.String(50), nullable=True),
        sa.Column('sensor_id', sa.String(50), nullable=False, unique=True),
        sa.Column('min_temp', sa.Numeric(5, 2), nullable=True),
        sa.Column('max_temp', sa.Numeric(5, 2), nullable=True),
        sa.Column('min_humidity', sa.Numeric(5, 2), nullable=True),
        sa.Column('max_humidity', sa.Numeric(5, 2), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_reading_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'sensor_readings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sensor_id', sa.Integer(), sa.ForeignKey('equipment_sensors.id'), nullable=False, index=True),
        sa.Column('temperature', sa.Numeric(5, 2), nullable=True),
        sa.Column('humidity', sa.Numeric(5, 2), nullable=True),
        sa.Column('door_open', sa.Boolean(), nullable=True),
        sa.Column('power_status', sa.Boolean(), nullable=True),
        sa.Column('is_alert', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'equipment_alerts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sensor_id', sa.Integer(), sa.ForeignKey('equipment_sensors.id'), nullable=False, index=True),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), default='warning'),
        sa.Column('message', sa.String(300), nullable=True),
        sa.Column('reading_value', sa.Numeric(6, 2), nullable=True),
        sa.Column('threshold_value', sa.Numeric(6, 2), nullable=True),
        sa.Column('acknowledged', sa.Boolean(), default=False),
        sa.Column('acknowledged_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved', sa.Boolean(), default=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 21. Vendor Scorecard
    op.create_table(
        'vendor_scorecards',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('supplier_id', sa.Integer(), sa.ForeignKey('suppliers.id'), nullable=False, index=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('on_time_delivery_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('order_accuracy_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('quality_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('price_competitiveness_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('communication_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('overall_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('total_orders', sa.Integer(), default=0),
        sa.Column('total_value', sa.Numeric(12, 2), default=0),
        sa.Column('issues_count', sa.Integer(), default=0),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 22. Virtual Brands
    op.create_table(
        'virtual_brands',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('parent_location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False),
        sa.Column('brand_name', sa.String(100), nullable=False),
        sa.Column('brand_slug', sa.String(50), nullable=False, unique=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cuisine_type', sa.String(50), nullable=True),
        sa.Column('menu_ids_json', sa.Text(), nullable=True),
        sa.Column('delivery_platforms_json', sa.Text(), nullable=True),
        sa.Column('operating_hours_json', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('total_orders', sa.Integer(), default=0),
        sa.Column('total_revenue', sa.Numeric(12, 2), default=0),
        sa.Column('avg_rating', sa.Numeric(3, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 23. Table Turn Optimization
    op.create_table(
        'table_turn_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('table_id', sa.Integer(), nullable=False, index=True),
        sa.Column('party_size', sa.Integer(), nullable=True),
        sa.Column('seated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('order_placed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('food_delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('check_requested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('check_paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('table_cleared_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_to_order', sa.Integer(), nullable=True),
        sa.Column('time_to_food', sa.Integer(), nullable=True),
        sa.Column('dining_time', sa.Integer(), nullable=True),
        sa.Column('total_turn_time', sa.Integer(), nullable=True),
        sa.Column('check_total', sa.Numeric(10, 2), nullable=True),
        sa.Column('revenue_per_minute', sa.Numeric(8, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'table_turn_forecasts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('location_id', sa.Integer(), sa.ForeignKey('locations.id'), nullable=False, index=True),
        sa.Column('table_id', sa.Integer(), nullable=False),
        sa.Column('current_party_seated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('predicted_available_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_available_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('prediction_error_minutes', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Numeric(3, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 24. Order Status Notifications
    op.create_table(
        'order_status_notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.Integer(), nullable=False, index=True),
        sa.Column('notification_type', sa.String(30), nullable=False),
        sa.Column('channel', sa.String(20), nullable=False),
        sa.Column('recipient', sa.String(100), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('tracking_url', sa.String(500), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed', sa.Boolean(), default=False),
        sa.Column('failure_reason', sa.String(300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 25. Supply Chain Traceability
    op.create_table(
        'supply_chain_traces',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('product_id', sa.Integer(), sa.ForeignKey('products.id'), nullable=False, index=True),
        sa.Column('batch_id', sa.Integer(), sa.ForeignKey('inventory_batches.id'), nullable=True),
        sa.Column('trace_id', sa.String(50), nullable=False, unique=True),
        sa.Column('farm_name', sa.String(200), nullable=True),
        sa.Column('farm_location', sa.String(300), nullable=True),
        sa.Column('harvest_date', sa.Date(), nullable=True),
        sa.Column('processor_name', sa.String(200), nullable=True),
        sa.Column('processing_date', sa.Date(), nullable=True),
        sa.Column('distributor_name', sa.String(200), nullable=True),
        sa.Column('ship_date', sa.Date(), nullable=True),
        sa.Column('received_date', sa.Date(), nullable=True),
        sa.Column('certifications_json', sa.Text(), nullable=True),
        sa.Column('blockchain_hash', sa.String(100), nullable=True),
        sa.Column('blockchain_verified', sa.Boolean(), default=False),
        sa.Column('qr_code_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    # Drop all tables in reverse order
    tables = [
        'supply_chain_traces',
        'order_status_notifications',
        'table_turn_forecasts',
        'table_turn_metrics',
        'virtual_brands',
        'vendor_scorecards',
        'equipment_alerts',
        'sensor_readings',
        'equipment_sensors',
        'sustainability_metrics',
        'allergen_profiles',
        'wait_time_predictions',
        'kitchen_station_assignments',
        'kitchen_stations',
        'prep_list_items',
        'prep_lists',
        'inventory_batches',
        'product_shelf_life_configs',
        'customer_journey_events',
        'cross_sell_impressions',
        'cross_sell_rules',
        'tip_pool_distributions',
        'tip_pool_configurations',
        'gift_card_transactions',
        'gift_cards',
        'gift_card_programs',
        'review_sentiments',
        'delivery_dispatches',
        'delivery_providers',
        'curbside_pickups',
        'pricing_events',
        'dynamic_pricing_rules',
        'menu_experiments',
        'wifi_sessions',
        'throttle_events',
        'kitchen_capacity_configs',
        'labor_compliance_violations',
        'labor_compliance_rules',
        'labor_forecasts',
        'waste_forecasts',
        'waste_tracking_entries',
    ]

    for table in tables:
        op.drop_table(table)

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS waste_category")
    op.execute("DROP TYPE IF EXISTS sentiment_type")
