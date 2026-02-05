"""Realign advanced features table schemas with models.

The original migration (005) created tables with different column schemas
than the current models in advanced_features.py. This migration drops and
recreates the affected tables to match the model definitions.

Tables affected:
- vendor_scorecards
- menu_experiments
- allergen_profiles
- equipment_sensors
- sustainability_metrics
- labor_compliance_rules
- labor_compliance_violations
- prep_lists
- prep_list_items
- delivery_providers
- delivery_dispatches
- supply_chain_traces
- table_turn_metrics
- cross_sell_rules
- cross_sell_impressions
- kitchen_stations
- dynamic_pricing_rules

Revision ID: 019
Revises: 018
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop tables that depend on others first (FK constraints)
    for t in [
        'cross_sell_impressions', 'delivery_dispatches',
        'labor_compliance_violations', 'prep_list_items',
        'station_load_metrics',
    ]:
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")

    # Drop main tables
    for t in [
        'vendor_scorecards', 'menu_experiments', 'allergen_profiles',
        'equipment_sensors', 'sustainability_metrics', 'labor_compliance_rules',
        'prep_lists', 'delivery_providers', 'supply_chain_traces',
        'table_turn_metrics', 'cross_sell_rules', 'kitchen_stations',
        'dynamic_pricing_rules',
    ]:
        op.execute(f"DROP TABLE IF EXISTS {t} CASCADE")

    # ================================================================
    # Recreate vendor_scorecards
    # ================================================================
    op.create_table(
        "vendor_scorecards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("supplier_id", sa.Integer(), nullable=False, index=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("defect_rate", sa.Float(), nullable=False),
        sa.Column("on_time_delivery_rate", sa.Float(), nullable=False),
        sa.Column("fill_rate", sa.Float(), nullable=False),
        sa.Column("avg_lead_time_days", sa.Float(), nullable=False),
        sa.Column("price_competitiveness", sa.Float(), nullable=False),
        sa.Column("price_stability", sa.Float(), nullable=False),
        sa.Column("responsiveness_score", sa.Float(), nullable=False),
        sa.Column("issue_resolution_time_hours", sa.Float(), nullable=True),
        sa.Column("food_safety_score", sa.Float(), nullable=True),
        sa.Column("certifications_valid", sa.Boolean(), server_default="true"),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate menu_experiments
    # ================================================================
    op.create_table(
        "menu_experiments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("experiment_type", sa.String(50), nullable=False),
        sa.Column("control_variant", sa.JSON(), nullable=False),
        sa.Column("test_variants", sa.JSON(), nullable=False),
        sa.Column("traffic_split", sa.JSON(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("winner_variant", sa.String(50), nullable=True),
        sa.Column("statistical_significance", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate allergen_profiles
    # ================================================================
    op.create_table(
        "allergen_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column("contains_gluten", sa.Boolean(), server_default="false"),
        sa.Column("contains_dairy", sa.Boolean(), server_default="false"),
        sa.Column("contains_eggs", sa.Boolean(), server_default="false"),
        sa.Column("contains_peanuts", sa.Boolean(), server_default="false"),
        sa.Column("contains_tree_nuts", sa.Boolean(), server_default="false"),
        sa.Column("contains_soy", sa.Boolean(), server_default="false"),
        sa.Column("contains_fish", sa.Boolean(), server_default="false"),
        sa.Column("contains_shellfish", sa.Boolean(), server_default="false"),
        sa.Column("contains_sesame", sa.Boolean(), server_default="false"),
        sa.Column("may_contain", sa.JSON(), nullable=True),
        sa.Column("prepared_on_shared_equipment", sa.Boolean(), server_default="false"),
        sa.Column("other_allergens", sa.JSON(), nullable=True),
        sa.Column("dietary_flags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate equipment_sensors
    # ================================================================
    op.create_table(
        "equipment_sensors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=False, index=True),
        sa.Column("equipment_name", sa.String(255), nullable=False),
        sa.Column("equipment_type", sa.String(100), nullable=False),
        sa.Column("sensor_id", sa.String(100), unique=True, nullable=False),
        sa.Column("sensor_type", sa.String(50), nullable=False),
        sa.Column("min_threshold", sa.Float(), nullable=True),
        sa.Column("max_threshold", sa.Float(), nullable=True),
        sa.Column("last_maintenance", sa.Date(), nullable=True),
        sa.Column("maintenance_interval_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate sensor_readings (depends on equipment_sensors)
    # ================================================================
    op.execute("DROP TABLE IF EXISTS sensor_readings CASCADE")
    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sensor_id", sa.Integer(), sa.ForeignKey("equipment_sensors.id"), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now(), index=True),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("is_alert", sa.Boolean(), server_default="false"),
        sa.Column("alert_type", sa.String(50), nullable=True),
    )

    # ================================================================
    # Recreate sustainability_metrics
    # ================================================================
    op.create_table(
        "sustainability_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=False, index=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("carbon_kg", sa.Numeric(12, 3), server_default="0"),
        sa.Column("carbon_per_cover", sa.Numeric(10, 4), nullable=True),
        sa.Column("food_waste_kg", sa.Numeric(10, 3), server_default="0"),
        sa.Column("food_donated_kg", sa.Numeric(10, 3), server_default="0"),
        sa.Column("food_composted_kg", sa.Numeric(10, 3), server_default="0"),
        sa.Column("landfill_kg", sa.Numeric(10, 3), server_default="0"),
        sa.Column("energy_kwh", sa.Numeric(10, 2), nullable=True),
        sa.Column("water_liters", sa.Numeric(10, 2), nullable=True),
        sa.Column("single_use_plastic_items", sa.Integer(), server_default="0"),
        sa.Column("recyclable_packaging_percent", sa.Float(), nullable=True),
        sa.Column("local_sourcing_percent", sa.Float(), nullable=True),
        sa.Column("organic_percent", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate labor_compliance_rules
    # ================================================================
    op.create_table(
        "labor_compliance_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("jurisdiction", sa.String(100), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("penalty_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Recreate labor_compliance_violations
    op.create_table(
        "labor_compliance_violations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("labor_compliance_rules.id"), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("violation_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("penalty_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("resolved", sa.Boolean(), server_default="false"),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate prep_lists
    # ================================================================
    op.create_table(
        "prep_lists",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=False, index=True),
        sa.Column("prep_date", sa.Date(), nullable=False),
        sa.Column("station", sa.String(100), nullable=True),
        sa.Column("generated_from", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("forecast_covers", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("assigned_to_id", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Recreate prep_list_items
    op.create_table(
        "prep_list_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("prep_list_id", sa.Integer(), sa.ForeignKey("prep_lists.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("required_quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("current_stock", sa.Numeric(10, 2), nullable=False),
        sa.Column("to_prep_quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("actual_prepped", sa.Numeric(10, 2), nullable=True),
        sa.Column("completed", sa.Boolean(), server_default="false"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate delivery_providers
    # ================================================================
    op.create_table(
        "delivery_providers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=False, index=True),
        sa.Column("provider_name", sa.String(50), nullable=False),
        sa.Column("api_key", sa.String(255), nullable=True),
        sa.Column("api_secret", sa.String(255), nullable=True),
        sa.Column("merchant_id", sa.String(100), nullable=True),
        sa.Column("base_fee", sa.Numeric(10, 2), server_default="0"),
        sa.Column("per_mile_fee", sa.Numeric(10, 2), server_default="0"),
        sa.Column("commission_percent", sa.Float(), nullable=True),
        sa.Column("avg_delivery_time_minutes", sa.Float(), nullable=True),
        sa.Column("reliability_score", sa.Float(), nullable=True),
        sa.Column("priority_rank", sa.Integer(), server_default="1"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Recreate delivery_dispatches
    op.create_table(
        "delivery_dispatches",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False, index=True),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("selected_provider_id", sa.Integer(), sa.ForeignKey("delivery_providers.id"), nullable=False),
        sa.Column("dispatch_reason", sa.String(100), nullable=False),
        sa.Column("provider_quotes", sa.JSON(), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("driver_assigned_at", sa.DateTime(), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("quoted_fee", sa.Numeric(10, 2), nullable=False),
        sa.Column("actual_fee", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate supply_chain_traces
    # ================================================================
    op.create_table(
        "supply_chain_traces",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("inventory_batches.id"), nullable=True),
        sa.Column("trace_id", sa.String(100), unique=True, nullable=False),
        sa.Column("farm_name", sa.String(255), nullable=True),
        sa.Column("farm_location", sa.String(255), nullable=True),
        sa.Column("harvest_date", sa.Date(), nullable=True),
        sa.Column("processor_name", sa.String(255), nullable=True),
        sa.Column("processing_date", sa.Date(), nullable=True),
        sa.Column("distributor_name", sa.String(255), nullable=True),
        sa.Column("ship_date", sa.Date(), nullable=True),
        sa.Column("received_date", sa.Date(), nullable=True),
        sa.Column("certifications", sa.JSON(), nullable=True),
        sa.Column("blockchain_hash", sa.String(100), nullable=True),
        sa.Column("blockchain_verified", sa.Boolean(), server_default="false"),
        sa.Column("qr_code_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate table_turn_metrics
    # ================================================================
    op.create_table(
        "table_turn_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=False, index=True),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("seated_at", sa.DateTime(), nullable=False),
        sa.Column("party_size", sa.Integer(), nullable=False),
        sa.Column("order_placed_at", sa.DateTime(), nullable=True),
        sa.Column("food_delivered_at", sa.DateTime(), nullable=True),
        sa.Column("check_requested_at", sa.DateTime(), nullable=True),
        sa.Column("check_paid_at", sa.DateTime(), nullable=True),
        sa.Column("table_cleared_at", sa.DateTime(), nullable=True),
        sa.Column("time_to_order", sa.Integer(), nullable=True),
        sa.Column("time_to_food", sa.Integer(), nullable=True),
        sa.Column("dining_time", sa.Integer(), nullable=True),
        sa.Column("total_turn_time", sa.Integer(), nullable=True),
        sa.Column("check_total", sa.Numeric(10, 2), nullable=True),
        sa.Column("revenue_per_minute", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate cross_sell_rules
    # ================================================================
    op.create_table(
        "cross_sell_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("trigger_product_ids", sa.JSON(), nullable=True),
        sa.Column("trigger_category_ids", sa.JSON(), nullable=True),
        sa.Column("trigger_cart_minimum", sa.Numeric(10, 2), nullable=True),
        sa.Column("recommend_product_ids", sa.JSON(), nullable=False),
        sa.Column("recommendation_message", sa.String(500), nullable=True),
        sa.Column("display_position", sa.String(50), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="1"),
        sa.Column("impressions", sa.Integer(), server_default="0"),
        sa.Column("conversions", sa.Integer(), server_default="0"),
        sa.Column("revenue_generated", sa.Numeric(12, 2), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Recreate cross_sell_impressions
    op.create_table(
        "cross_sell_impressions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("cross_sell_rules.id"), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("shown_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("converted", sa.Boolean(), server_default="false"),
        sa.Column("converted_at", sa.DateTime(), nullable=True),
        sa.Column("recommended_product_id", sa.Integer(), nullable=False),
        sa.Column("added_product_id", sa.Integer(), nullable=True),
        sa.Column("revenue", sa.Numeric(10, 2), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate kitchen_stations
    # ================================================================
    op.create_table(
        "kitchen_stations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("station_type", sa.String(50), nullable=False),
        sa.Column("max_concurrent_items", sa.Integer(), server_default="10"),
        sa.Column("avg_item_time_seconds", sa.Integer(), server_default="300"),
        sa.Column("equipment_ids", sa.JSON(), nullable=True),
        sa.Column("min_staff", sa.Integer(), server_default="1"),
        sa.Column("max_staff", sa.Integer(), server_default="3"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # Recreate station_load_metrics (FK to kitchen_stations)
    op.create_table(
        "station_load_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("station_id", sa.Integer(), sa.ForeignKey("kitchen_stations.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("items_in_queue", sa.Integer(), server_default="0"),
        sa.Column("items_in_progress", sa.Integer(), server_default="0"),
        sa.Column("avg_wait_time_seconds", sa.Integer(), nullable=True),
        sa.Column("avg_cook_time_seconds", sa.Integer(), nullable=True),
        sa.Column("load_percent", sa.Float(), server_default="0"),
        sa.Column("is_overloaded", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # Recreate dynamic_pricing_rules
    # ================================================================
    op.create_table(
        "dynamic_pricing_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("trigger_conditions", sa.JSON(), nullable=False),
        sa.Column("adjustment_type", sa.String(20), nullable=False),
        sa.Column("adjustment_value", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_adjustment_percent", sa.Float(), nullable=True),
        sa.Column("applies_to", sa.String(50), nullable=False),
        sa.Column("item_ids", sa.JSON(), nullable=True),
        sa.Column("category_ids", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    # This migration is a schema realignment; downgrade is not practical
    # as original schemas are from migration 005
    pass
