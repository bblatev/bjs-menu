"""Add modifier_groups, modifier_options, menu_item_modifier_groups, combo_meals, combo_items tables.

Revision ID: 015
Revises: 014
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "modifier_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("min_selections", sa.Integer(), server_default="0"),
        sa.Column("max_selections", sa.Integer(), server_default="1"),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_modifier_groups_id", "modifier_groups", ["id"])

    op.create_table(
        "modifier_options",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("modifier_groups.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("price_adjustment", sa.Numeric(10, 2), server_default="0"),
        sa.Column("available", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_modifier_options_id", "modifier_options", ["id"])
    op.create_index("ix_modifier_options_group_id", "modifier_options", ["group_id"])

    op.create_table(
        "menu_item_modifier_groups",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=False),
        sa.Column("modifier_group_id", sa.Integer(), sa.ForeignKey("modifier_groups.id"), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )
    op.create_index("ix_menu_item_modifier_groups_id", "menu_item_modifier_groups", ["id"])

    op.create_table(
        "combo_meals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=True),
        sa.Column("available", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("featured", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index("ix_combo_meals_id", "combo_meals", ["id"])

    op.create_table(
        "combo_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("combo_id", sa.Integer(), sa.ForeignKey("combo_meals.id"), nullable=False),
        sa.Column("menu_item_id", sa.Integer(), sa.ForeignKey("menu_items.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1"),
        sa.Column("is_choice", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("choice_group", sa.String(100), nullable=True),
    )
    op.create_index("ix_combo_items_id", "combo_items", ["id"])
    op.create_index("ix_combo_items_combo_id", "combo_items", ["combo_id"])


def downgrade():
    op.drop_table("combo_items")
    op.drop_table("combo_meals")
    op.drop_table("menu_item_modifier_groups")
    op.drop_table("modifier_options")
    op.drop_table("modifier_groups")
