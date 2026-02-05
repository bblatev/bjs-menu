"""Add missing advanced features tables and guest_history.

Creates tables used by advanced_features models and services that
were defined in code but never migrated to the database:
- guest_history (reservations)
- product_shelf_lives
- guest_wifi_sessions
- curbside_orders
- menu_experiment_results
- dynamic_price_adjustments
- station_load_metrics
- expiration_alerts
- allergen_alerts
- esg_reports
- predictive_maintenance
- customer_journey_funnels

Revision ID: 018
Revises: 017
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa


revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ================================================================
    # 1. guest_history (used by reservations)
    # ================================================================
    op.create_table(
        "guest_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("guest_phone", sa.String(50), nullable=True),
        sa.Column("guest_email", sa.String(255), nullable=True),
        sa.Column("total_visits", sa.Integer(), server_default="0"),
        sa.Column("total_spend", sa.Float(), server_default="0.0"),
        sa.Column("total_no_shows", sa.Integer(), server_default="0"),
        sa.Column("total_cancellations", sa.Integer(), server_default="0"),
        sa.Column("preferred_tables", sa.JSON(), nullable=True),
        sa.Column("preferred_servers", sa.JSON(), nullable=True),
        sa.Column("dietary_restrictions", sa.JSON(), nullable=True),
        sa.Column("favorite_items", sa.JSON(), nullable=True),
        sa.Column("is_vip", sa.Boolean(), server_default="false"),
        sa.Column("vip_notes", sa.Text(), nullable=True),
        sa.Column("is_blacklisted", sa.Boolean(), server_default="false"),
        sa.Column("blacklist_reason", sa.Text(), nullable=True),
        sa.Column("first_visit_at", sa.DateTime(), nullable=True),
        sa.Column("last_visit_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 2. product_shelf_lives
    # ================================================================
    op.create_table(
        "product_shelf_lives",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column("shelf_life_days", sa.Integer(), nullable=False),
        sa.Column("use_by_type", sa.String(20), nullable=False),
        sa.Column("storage_temp_min", sa.Float(), nullable=True),
        sa.Column("storage_temp_max", sa.Float(), nullable=True),
        sa.Column("requires_refrigeration", sa.Boolean(), server_default="false"),
        sa.Column("alert_days_before", sa.Integer(), server_default="3"),
        sa.Column("markdown_days_before", sa.Integer(), nullable=True),
        sa.Column("markdown_percent", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 3. guest_wifi_sessions
    # ================================================================
    op.create_table(
        "guest_wifi_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=False, index=True),
        sa.Column("mac_address", sa.String(17), nullable=False, index=True),
        sa.Column("device_type", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True, index=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("marketing_consent", sa.Boolean(), server_default="false"),
        sa.Column("consent_timestamp", sa.DateTime(), nullable=True),
        sa.Column("connected_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("disconnected_at", sa.DateTime(), nullable=True),
        sa.Column("session_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("visit_count", sa.Integer(), server_default="1"),
        sa.Column("last_visit", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 4. curbside_orders
    # ================================================================
    op.create_table(
        "curbside_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False, index=True),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("customer_phone", sa.String(20), nullable=False),
        sa.Column("vehicle_description", sa.String(255), nullable=True),
        sa.Column("vehicle_color", sa.String(50), nullable=True),
        sa.Column("vehicle_make", sa.String(100), nullable=True),
        sa.Column("parking_spot", sa.String(20), nullable=True),
        sa.Column("estimated_ready_time", sa.DateTime(), nullable=True),
        sa.Column("customer_arrived_at", sa.DateTime(), nullable=True),
        sa.Column("order_delivered_at", sa.DateTime(), nullable=True),
        sa.Column("arrival_notification_sent", sa.Boolean(), server_default="false"),
        sa.Column("ready_notification_sent", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 5. menu_experiment_results
    # ================================================================
    op.create_table(
        "menu_experiment_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("experiment_id", sa.Integer(), sa.ForeignKey("menu_experiments.id"), nullable=False),
        sa.Column("variant_name", sa.String(50), nullable=False),
        sa.Column("impressions", sa.Integer(), server_default="0"),
        sa.Column("clicks", sa.Integer(), server_default="0"),
        sa.Column("orders", sa.Integer(), server_default="0"),
        sa.Column("revenue", sa.Numeric(12, 2), server_default="0"),
        sa.Column("conversion_rate", sa.Float(), nullable=True),
        sa.Column("avg_order_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 6. dynamic_price_adjustments
    # ================================================================
    op.create_table(
        "dynamic_price_adjustments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("dynamic_pricing_rules.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("activated_at", sa.DateTime(), nullable=False),
        sa.Column("deactivated_at", sa.DateTime(), nullable=True),
        sa.Column("original_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("adjusted_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("trigger_value", sa.String(255), nullable=True),
        sa.Column("orders_during_surge", sa.Integer(), server_default="0"),
        sa.Column("additional_revenue", sa.Numeric(10, 2), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 7. station_load_metrics
    # ================================================================
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
    # 8. expiration_alerts
    # ================================================================
    op.create_table(
        "expiration_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("inventory_batches.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("days_until_expiry", sa.Integer(), nullable=False),
        sa.Column("quantity_affected", sa.Numeric(10, 2), nullable=False),
        sa.Column("value_at_risk", sa.Numeric(10, 2), nullable=False),
        sa.Column("action_taken", sa.String(50), nullable=True),
        sa.Column("action_date", sa.DateTime(), nullable=True),
        sa.Column("action_by_id", sa.Integer(), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 9. allergen_alerts
    # ================================================================
    op.create_table(
        "allergen_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False, index=True),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("allergens_flagged", sa.JSON(), nullable=False),
        sa.Column("alert_message", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), server_default="false"),
        sa.Column("acknowledged_by_id", sa.Integer(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("special_prep_required", sa.Boolean(), server_default="false"),
        sa.Column("prep_instructions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 10. esg_reports
    # ================================================================
    op.create_table(
        "esg_reports",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("report_period", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("total_carbon_kg", sa.Numeric(14, 3), nullable=False),
        sa.Column("total_waste_kg", sa.Numeric(14, 3), nullable=False),
        sa.Column("waste_diversion_rate", sa.Float(), nullable=False),
        sa.Column("carbon_target_kg", sa.Numeric(14, 3), nullable=True),
        sa.Column("waste_target_kg", sa.Numeric(14, 3), nullable=True),
        sa.Column("carbon_vs_target_percent", sa.Float(), nullable=True),
        sa.Column("waste_vs_target_percent", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 11. predictive_maintenance
    # ================================================================
    op.create_table(
        "predictive_maintenance",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sensor_id", sa.Integer(), sa.ForeignKey("equipment_sensors.id"), nullable=False),
        sa.Column("prediction_type", sa.String(50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("predicted_failure_date", sa.Date(), nullable=True),
        sa.Column("indicators", sa.JSON(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), server_default="false"),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 12. customer_journey_funnels
    # ================================================================
    op.create_table(
        "customer_journey_funnels",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("sessions", sa.Integer(), server_default="0"),
        sa.Column("menu_views", sa.Integer(), server_default="0"),
        sa.Column("item_views", sa.Integer(), server_default="0"),
        sa.Column("add_to_carts", sa.Integer(), server_default="0"),
        sa.Column("checkout_starts", sa.Integer(), server_default="0"),
        sa.Column("orders_placed", sa.Integer(), server_default="0"),
        sa.Column("menu_to_item_rate", sa.Float(), nullable=True),
        sa.Column("cart_rate", sa.Float(), nullable=True),
        sa.Column("checkout_rate", sa.Float(), nullable=True),
        sa.Column("conversion_rate", sa.Float(), nullable=True),
        sa.Column("total_revenue", sa.Numeric(12, 2), server_default="0"),
        sa.Column("avg_order_value", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("customer_journey_funnels")
    op.drop_table("predictive_maintenance")
    op.drop_table("esg_reports")
    op.drop_table("allergen_alerts")
    op.drop_table("expiration_alerts")
    op.drop_table("station_load_metrics")
    op.drop_table("dynamic_price_adjustments")
    op.drop_table("menu_experiment_results")
    op.drop_table("curbside_orders")
    op.drop_table("guest_wifi_sessions")
    op.drop_table("product_shelf_lives")
    op.drop_table("guest_history")
