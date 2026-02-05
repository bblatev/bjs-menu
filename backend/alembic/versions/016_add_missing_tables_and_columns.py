"""Add all missing tables and columns for endpoints returning 500.

Creates: integrations, gl_codes, waiter_calls, throttle_rules,
         loyalty_programs, customer_segments, marketing_campaigns,
         campaign_recipients, automated_triggers, menu_recommendations,
         customer_loyalty, delivery_integrations, delivery_orders,
         delivery_order_items, menu_syncs, item_availability,
         delivery_platform_mappings, price_history, price_alerts,
         ap_approval_workflows, hotel_guests, offline_queue, ocr_jobs,
         kegs, tanks, rfid_tags, inventory_count_sessions

Alters: customers (add missing CRM columns),
        gift_cards (add missing columns for new model),
        gift_card_transactions (add gift_card_id, performed_by_id, notes),
        gift_card_programs (add missing columns),
        waste_tracking_entries (fix enum)

Revision ID: 016
Revises: 015
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade():
    # ================================================================
    # 1. CREATE MISSING TABLES
    # ================================================================

    # --- integrations ---
    op.create_table(
        "integrations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("integration_id", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), server_default="disconnected", nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("connected_at", sa.DateTime(), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- gl_codes ---
    op.create_table(
        "gl_codes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("auto_assign_keywords", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- waiter_calls ---
    op.create_table(
        "waiter_calls",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("table_number", sa.String(50), nullable=False),
        sa.Column("call_type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_by", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- throttle_rules ---
    op.create_table(
        "throttle_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("max_orders_per_hour", sa.Integer(), server_default="60", nullable=False),
        sa.Column("max_items_per_order", sa.Integer(), server_default="25", nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("applies_to", sa.String(50), server_default="all", nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- hotel_guests ---
    op.create_table(
        "hotel_guests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("room_number", sa.String(50), nullable=False),
        sa.Column("guest_name", sa.String(255), nullable=False),
        sa.Column("check_in", sa.DateTime(), nullable=False),
        sa.Column("check_out", sa.DateTime(), nullable=False),
        sa.Column("vip_status", sa.String(50), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- offline_queue ---
    op.create_table(
        "offline_queue",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("item_type", sa.String(50), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- ocr_jobs ---
    op.create_table(
        "ocr_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- kegs ---
    op.create_table(
        "kegs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("size_liters", sa.Float(), server_default="50.0", nullable=False),
        sa.Column("remaining_liters", sa.Float(), server_default="50.0", nullable=False),
        sa.Column("status", sa.String(50), server_default="full", nullable=False),
        sa.Column("tap_number", sa.Integer(), nullable=True),
        sa.Column("tapped_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("location", sa.String(100), server_default="Bar", nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- tanks ---
    op.create_table(
        "tanks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("capacity_liters", sa.Float(), nullable=False),
        sa.Column("current_level_liters", sa.Float(), nullable=False),
        sa.Column("status", sa.String(50), server_default="ok", nullable=False),
        sa.Column("last_refill", sa.DateTime(), nullable=True),
        sa.Column("sensor_id", sa.String(100), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- rfid_tags ---
    op.create_table(
        "rfid_tags",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tag_id", sa.String(100), unique=True, nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("quantity", sa.Float(), server_default="0", nullable=False),
        sa.Column("unit", sa.String(50), server_default="units", nullable=False),
        sa.Column("zone", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        sa.Column("last_seen", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("location", sa.String(100), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- inventory_count_sessions ---
    op.create_table(
        "inventory_count_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("zone", sa.String(100), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("tags_scanned", sa.Integer(), server_default="0", nullable=False),
        sa.Column("discrepancies", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(50), server_default="in_progress", nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- marketing_campaigns ---
    op.create_table(
        "marketing_campaigns",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("campaign_type", sa.String(50), server_default="email"),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("trigger_type", sa.String(50), server_default="manual"),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("subject_line", sa.String(500), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("ai_generated", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("target_segment", sa.String(100), nullable=True),
        sa.Column("target_criteria", sa.JSON(), nullable=True),
        sa.Column("exclude_recent_contacts", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("exclude_days", sa.Integer(), server_default="7"),
        sa.Column("offer_type", sa.String(50), nullable=True),
        sa.Column("offer_value", sa.Float(), nullable=True),
        sa.Column("offer_code", sa.String(50), nullable=True),
        sa.Column("offer_expires_at", sa.DateTime(), nullable=True),
        sa.Column("total_sent", sa.Integer(), server_default="0"),
        sa.Column("total_delivered", sa.Integer(), server_default="0"),
        sa.Column("total_opened", sa.Integer(), server_default="0"),
        sa.Column("total_clicked", sa.Integer(), server_default="0"),
        sa.Column("total_converted", sa.Integer(), server_default="0"),
        sa.Column("total_revenue", sa.Float(), server_default="0.0"),
        sa.Column("total_unsubscribed", sa.Integer(), server_default="0"),
        sa.Column("campaign_cost", sa.Float(), server_default="0.0"),
        sa.Column("roi", sa.Float(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- campaign_recipients ---
    op.create_table(
        "campaign_recipients",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("campaign_id", sa.Integer(), sa.ForeignKey("marketing_campaigns.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
        sa.Column("converted_at", sa.DateTime(), nullable=True),
        sa.Column("unsubscribed_at", sa.DateTime(), nullable=True),
        sa.Column("conversion_order_id", sa.Integer(), nullable=True),
        sa.Column("conversion_amount", sa.Float(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # --- customer_segments ---
    op.create_table(
        "customer_segments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("criteria", sa.JSON(), nullable=True),
        sa.Column("customer_count", sa.Integer(), server_default="0"),
        sa.Column("avg_spend", sa.Float(), nullable=True),
        sa.Column("total_revenue", sa.Float(), nullable=True),
        sa.Column("last_calculated_at", sa.DateTime(), nullable=True),
        sa.Column("is_dynamic", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- automated_triggers ---
    op.create_table(
        "automated_triggers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("trigger_type", sa.String(50), nullable=False),
        sa.Column("days_threshold", sa.Integer(), nullable=True),
        sa.Column("amount_threshold", sa.Float(), nullable=True),
        sa.Column("campaign_template_id", sa.Integer(), nullable=True),
        sa.Column("reward_points", sa.Integer(), nullable=True),
        sa.Column("discount_percent", sa.Float(), nullable=True),
        sa.Column("discount_amount", sa.Float(), nullable=True),
        sa.Column("send_time", sa.String(10), nullable=True),
        sa.Column("send_days_before", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("total_triggered", sa.Integer(), server_default="0"),
        sa.Column("total_converted", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- menu_recommendations ---
    op.create_table(
        "menu_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.String(100), nullable=True),
        sa.Column("day_of_week", sa.Integer(), nullable=True),
        sa.Column("hour_of_day", sa.Integer(), nullable=True),
        sa.Column("is_weekend", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("recommended_items", sa.JSON(), nullable=True),
        sa.Column("items_shown", sa.JSON(), nullable=True),
        sa.Column("items_ordered", sa.JSON(), nullable=True),
        sa.Column("conversion_rate", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- loyalty_programs ---
    op.create_table(
        "loyalty_programs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("program_type", sa.String(50), server_default="points"),
        sa.Column("points_per_dollar", sa.Float(), server_default="1.0"),
        sa.Column("points_per_visit", sa.Integer(), server_default="10"),
        sa.Column("points_to_dollar", sa.Float(), server_default="0.01"),
        sa.Column("min_redemption", sa.Integer(), server_default="100"),
        sa.Column("tiers", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- customer_loyalty ---
    op.create_table(
        "customer_loyalty",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("program_id", sa.Integer(), nullable=True),
        sa.Column("current_points", sa.Integer(), server_default="0"),
        sa.Column("lifetime_points", sa.Integer(), server_default="0"),
        sa.Column("redeemed_points", sa.Integer(), server_default="0"),
        sa.Column("total_visits", sa.Integer(), server_default="0"),
        sa.Column("total_spend", sa.Float(), server_default="0.0"),
        sa.Column("current_tier", sa.String(50), nullable=True),
        sa.Column("first_visit_at", sa.DateTime(), nullable=True),
        sa.Column("last_visit_at", sa.DateTime(), nullable=True),
        sa.Column("birthday", sa.DateTime(), nullable=True),
        sa.Column("anniversary", sa.DateTime(), nullable=True),
        sa.Column("favorite_items", sa.JSON(), nullable=True),
        sa.Column("dietary_preferences", sa.JSON(), nullable=True),
        sa.Column("communication_preferences", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- delivery_integrations ---
    op.create_table(
        "delivery_integrations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("api_key", sa.String(500), nullable=True),
        sa.Column("api_secret", sa.String(500), nullable=True),
        sa.Column("store_id", sa.String(200), nullable=True),
        sa.Column("merchant_id", sa.String(200), nullable=True),
        sa.Column("webhook_url", sa.String(500), nullable=True),
        sa.Column("webhook_secret", sa.String(200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("is_menu_synced", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("last_menu_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_order_received_at", sa.DateTime(), nullable=True),
        sa.Column("auto_accept_orders", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("auto_confirm_ready", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("prep_time_minutes", sa.Integer(), server_default="20"),
        sa.Column("sync_inventory", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("commission_percent", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- delivery_orders ---
    op.create_table(
        "delivery_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("delivery_integrations.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("platform_order_id", sa.String(200), nullable=False),
        sa.Column("platform_display_id", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), server_default="received"),
        sa.Column("status_updated_at", sa.DateTime(), nullable=True),
        sa.Column("received_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("ready_at", sa.DateTime(), nullable=True),
        sa.Column("picked_up_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("estimated_pickup_at", sa.DateTime(), nullable=True),
        sa.Column("estimated_delivery_at", sa.DateTime(), nullable=True),
        sa.Column("estimated_prep_minutes", sa.Integer(), nullable=True),
        sa.Column("customer_name", sa.String(200), nullable=True),
        sa.Column("customer_phone", sa.String(50), nullable=True),
        sa.Column("delivery_address", sa.Text(), nullable=True),
        sa.Column("delivery_instructions", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Float(), server_default="0.0"),
        sa.Column("tax", sa.Float(), server_default="0.0"),
        sa.Column("delivery_fee", sa.Float(), server_default="0.0"),
        sa.Column("tip", sa.Float(), server_default="0.0"),
        sa.Column("total", sa.Float(), server_default="0.0"),
        sa.Column("platform_fee", sa.Float(), server_default="0.0"),
        sa.Column("net_payout", sa.Float(), server_default="0.0"),
        sa.Column("special_instructions", sa.Text(), nullable=True),
        sa.Column("is_scheduled", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("scheduled_for", sa.DateTime(), nullable=True),
        sa.Column("pos_order_id", sa.Integer(), nullable=True),
        sa.Column("sent_to_kds", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("kds_ticket_id", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- delivery_order_items ---
    op.create_table(
        "delivery_order_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("delivery_orders.id"), nullable=False),
        sa.Column("platform_item_id", sa.String(200), nullable=True),
        sa.Column("item_name", sa.String(300), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1"),
        sa.Column("unit_price", sa.Float(), server_default="0.0"),
        sa.Column("total_price", sa.Float(), server_default="0.0"),
        sa.Column("modifiers", sa.JSON(), nullable=True),
        sa.Column("special_instructions", sa.Text(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
    )

    # --- menu_syncs ---
    op.create_table(
        "menu_syncs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("delivery_integrations.id"), nullable=False),
        sa.Column("sync_type", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("success", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("items_synced", sa.Integer(), server_default="0"),
        sa.Column("items_failed", sa.Integer(), server_default="0"),
        sa.Column("availability_changes", sa.Integer(), server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("error_details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- item_availability ---
    op.create_table(
        "item_availability",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("is_available", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("unavailable_reason", sa.String(200), nullable=True),
        sa.Column("unavailable_until", sa.DateTime(), nullable=True),
        sa.Column("platforms_synced", sa.JSON(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- delivery_platform_mappings ---
    op.create_table(
        "delivery_platform_mappings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("integration_id", sa.Integer(), sa.ForeignKey("delivery_integrations.id"), nullable=False),
        sa.Column("platform_item_id", sa.String(200), nullable=False),
        sa.Column("platform_item_name", sa.String(300), nullable=True),
        sa.Column("platform_price", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- price_history ---
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("unit_of_measure", sa.String(50), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("source_invoice_id", sa.Integer(), nullable=True),
    )

    # --- price_alerts ---
    op.create_table(
        "price_alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("supplier_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sa.String(50), nullable=False),
        sa.Column("threshold_percent", sa.Float(), nullable=True),
        sa.Column("threshold_amount", sa.Float(), nullable=True),
        sa.Column("max_price", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.Column("trigger_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # --- ap_approval_workflows ---
    op.create_table(
        "ap_approval_workflows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("min_amount", sa.Float(), server_default="0.0"),
        sa.Column("max_amount", sa.Float(), nullable=True),
        sa.Column("approver_ids", sa.JSON(), nullable=True),
        sa.Column("requires_all_approvers", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("auto_approve_known_vendors", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("auto_approve_below_amount", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )

    # ================================================================
    # 2. ADD MISSING COLUMNS TO customers TABLE
    # ================================================================

    op.add_column("customers", sa.Column("total_orders", sa.Integer(), server_default="0", nullable=False))
    op.add_column("customers", sa.Column("total_spent", sa.Float(), server_default="0.0", nullable=False))
    op.add_column("customers", sa.Column("average_order", sa.Float(), server_default="0.0", nullable=False))
    op.add_column("customers", sa.Column("first_visit", sa.DateTime(), nullable=True))
    op.add_column("customers", sa.Column("last_visit", sa.DateTime(), nullable=True))
    op.add_column("customers", sa.Column("visit_frequency", sa.Float(), server_default="0.0", nullable=False))
    op.add_column("customers", sa.Column("lifetime_value", sa.Float(), server_default="0.0", nullable=False))
    op.add_column("customers", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column("customers", sa.Column("spend_trend", sa.String(20), server_default="stable", nullable=True))
    op.add_column("customers", sa.Column("rfm_recency", sa.Integer(), server_default="0", nullable=False))
    op.add_column("customers", sa.Column("rfm_frequency", sa.Integer(), server_default="0", nullable=False))
    op.add_column("customers", sa.Column("rfm_monetary", sa.Integer(), server_default="0", nullable=False))
    op.add_column("customers", sa.Column("birthday", sa.DateTime(), nullable=True))
    op.add_column("customers", sa.Column("anniversary", sa.DateTime(), nullable=True))
    op.add_column("customers", sa.Column("acquisition_source", sa.String(50), server_default="direct", nullable=True))
    op.add_column("customers", sa.Column("allergies", sa.JSON(), nullable=True))
    op.add_column("customers", sa.Column("preferences", sa.Text(), nullable=True))
    op.add_column("customers", sa.Column("favorite_items", sa.JSON(), nullable=True))
    op.add_column("customers", sa.Column("avg_party_size", sa.Float(), nullable=True))
    op.add_column("customers", sa.Column("preferred_time", sa.String(50), nullable=True))
    op.add_column("customers", sa.Column("marketing_consent", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("customers", sa.Column("communication_preference", sa.String(20), server_default="email", nullable=True))

    # ================================================================
    # 3. ADD MISSING COLUMNS TO gift_cards TABLE
    # ================================================================

    op.add_column("gift_cards", sa.Column("pin", sa.String(10), nullable=True))
    op.add_column("gift_cards", sa.Column("bonus_balance", sa.Numeric(10, 2), server_default="0"))
    op.add_column("gift_cards", sa.Column("purchaser_name", sa.String(255), nullable=True))
    op.add_column("gift_cards", sa.Column("recipient_message", sa.Text(), nullable=True))
    op.add_column("gift_cards", sa.Column("delivery_method", sa.String(20), server_default="email", nullable=True))
    op.add_column("gift_cards", sa.Column("delivered_at", sa.DateTime(), nullable=True))
    op.add_column("gift_cards", sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")))
    op.add_column("gift_cards", sa.Column("purchase_order_id", sa.Integer(), nullable=True))
    op.add_column("gift_cards", sa.Column("purchase_location_id", sa.Integer(), nullable=True))
    op.add_column("gift_cards", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()))

    # ================================================================
    # 4. ADD MISSING COLUMNS TO gift_card_transactions TABLE
    # ================================================================

    op.add_column("gift_card_transactions", sa.Column("gift_card_id", sa.Integer(), nullable=True))
    op.add_column("gift_card_transactions", sa.Column("performed_by_id", sa.Integer(), nullable=True))
    op.add_column("gift_card_transactions", sa.Column("notes", sa.Text(), nullable=True))

    # Copy card_id to gift_card_id for existing records
    op.execute("UPDATE gift_card_transactions SET gift_card_id = card_id WHERE gift_card_id IS NULL")

    # ================================================================
    # 5. ADD MISSING COLUMNS TO gift_card_programs TABLE
    # ================================================================

    op.add_column("gift_card_programs", sa.Column("denominations", sa.JSON(), nullable=True))
    op.add_column("gift_card_programs", sa.Column("custom_amount_allowed", sa.Boolean(), server_default=sa.text("true")))
    op.add_column("gift_card_programs", sa.Column("bonus_enabled", sa.Boolean(), server_default=sa.text("false")))
    op.add_column("gift_card_programs", sa.Column("bonus_rules", sa.JSON(), nullable=True))
    op.add_column("gift_card_programs", sa.Column("expiration_months", sa.Integer(), nullable=True))
    op.add_column("gift_card_programs", sa.Column("dormancy_fee_enabled", sa.Boolean(), server_default=sa.text("false")))
    op.add_column("gift_card_programs", sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()))

    # ================================================================
    # 6. FIX waste_category ENUM - add missing 'trim_waste' value
    # ================================================================
    op.execute("ALTER TYPE waste_category ADD VALUE IF NOT EXISTS 'trim_waste'")


def downgrade():
    # Drop new tables (reverse order of creation due to foreign keys)
    tables_to_drop = [
        "ap_approval_workflows", "price_alerts", "price_history",
        "delivery_platform_mappings", "item_availability", "menu_syncs",
        "delivery_order_items", "delivery_orders", "delivery_integrations",
        "customer_loyalty", "loyalty_programs", "menu_recommendations",
        "automated_triggers", "customer_segments", "campaign_recipients",
        "marketing_campaigns", "inventory_count_sessions", "rfid_tags",
        "tanks", "kegs", "ocr_jobs", "offline_queue", "hotel_guests",
        "throttle_rules", "waiter_calls", "gl_codes", "integrations",
    ]
    for table in tables_to_drop:
        op.drop_table(table)

    # Drop columns added to customers
    customer_cols = [
        "total_orders", "total_spent", "average_order", "first_visit",
        "last_visit", "visit_frequency", "lifetime_value", "tags",
        "spend_trend", "rfm_recency", "rfm_frequency", "rfm_monetary",
        "birthday", "anniversary", "acquisition_source", "allergies",
        "preferences", "favorite_items", "avg_party_size", "preferred_time",
        "marketing_consent", "communication_preference",
    ]
    for col in customer_cols:
        op.drop_column("customers", col)

    # Drop columns added to gift_cards
    gc_cols = [
        "pin", "bonus_balance", "purchaser_name", "recipient_message",
        "delivery_method", "delivered_at", "is_active",
        "purchase_order_id", "purchase_location_id", "updated_at",
    ]
    for col in gc_cols:
        op.drop_column("gift_cards", col)

    # Drop columns added to gift_card_transactions
    op.drop_column("gift_card_transactions", "gift_card_id")
    op.drop_column("gift_card_transactions", "performed_by_id")
    op.drop_column("gift_card_transactions", "notes")

    # Drop columns added to gift_card_programs
    gcp_cols = [
        "denominations", "custom_amount_allowed", "bonus_enabled",
        "bonus_rules", "expiration_months", "dormancy_fee_enabled", "updated_at",
    ]
    for col in gcp_cols:
        op.drop_column("gift_card_programs", col)
