"""Advanced Analytics models - Lightspeed/SpotOn style."""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class MenuQuadrant(str, Enum):
    """Menu engineering quadrant classification."""
    STAR = "star"           # High popularity, high profit - Greatest Hits
    PUZZLE = "puzzle"       # Low popularity, high profit - Hidden Gems
    PLOW_HORSE = "plow_horse"  # High popularity, low profit - One-Hit Wonders
    DOG = "dog"             # Low popularity, low profit - Underperformers


class MenuAnalysis(Base):
    """Menu engineering analysis results."""
    __tablename__ = "menu_analysis"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    analysis_period_start = Column(DateTime, nullable=False)
    analysis_period_end = Column(DateTime, nullable=False)

    # Sales metrics
    quantity_sold = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    total_profit = Column(Float, default=0.0)

    # Calculated metrics
    food_cost_percent = Column(Float, nullable=True)
    profit_margin_percent = Column(Float, nullable=True)
    contribution_margin = Column(Float, nullable=True)  # Profit per item
    popularity_index = Column(Float, nullable=True)     # % of total sales
    profitability_index = Column(Float, nullable=True)  # vs average margin

    # Quadrant classification
    quadrant = Column(SQLEnum(MenuQuadrant), nullable=True)

    # Recommendations
    recommended_action = Column(String(100), nullable=True)
    # "increase_price", "promote", "remove", "reduce_cost", "keep"
    recommended_price = Column(Float, nullable=True)
    recommendation_reason = Column(Text, nullable=True)

    # Trends
    sales_trend = Column(String(20), nullable=True)  # up, down, stable
    sales_trend_percent = Column(Float, nullable=True)

    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ServerPerformance(Base):
    """Server/staff performance metrics."""
    __tablename__ = "server_performance"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Order metrics
    total_orders = Column(Integer, default=0)
    total_covers = Column(Integer, default=0)  # Guests served
    total_revenue = Column(Float, default=0.0)
    total_tips = Column(Float, default=0.0)

    # Averages
    avg_ticket_size = Column(Float, nullable=True)
    avg_tip_percent = Column(Float, nullable=True)
    avg_covers_per_order = Column(Float, nullable=True)

    # Upselling metrics
    appetizer_attach_rate = Column(Float, nullable=True)  # % orders with appetizer
    dessert_attach_rate = Column(Float, nullable=True)
    drink_attach_rate = Column(Float, nullable=True)
    side_attach_rate = Column(Float, nullable=True)

    # Speed metrics
    avg_table_turn_minutes = Column(Float, nullable=True)
    avg_order_to_serve_minutes = Column(Float, nullable=True)

    # Comparison to average
    vs_avg_ticket = Column(Float, nullable=True)  # % above/below average
    vs_avg_tips = Column(Float, nullable=True)
    vs_avg_upsell = Column(Float, nullable=True)

    # Ranking
    rank_by_revenue = Column(Integer, nullable=True)
    rank_by_tips = Column(Integer, nullable=True)
    rank_by_upsell = Column(Integer, nullable=True)

    # Coaching suggestions
    coaching_notes = Column(JSON, nullable=True)
    # ["Improve dessert suggestions", "Strong appetizer sales"]

    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SalesForecast(Base):
    """AI-powered sales and demand forecasting."""
    __tablename__ = "sales_forecasts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # Null for total sales
    forecast_date = Column(DateTime, nullable=False)

    # Forecast values
    forecasted_quantity = Column(Integer, nullable=True)
    forecasted_revenue = Column(Float, nullable=True)
    forecasted_covers = Column(Integer, nullable=True)

    # Confidence
    confidence_level = Column(Float, nullable=True)  # 0-1
    lower_bound = Column(Float, nullable=True)
    upper_bound = Column(Float, nullable=True)

    # Factors considered
    factors = Column(JSON, nullable=True)
    # {"day_of_week": 0.3, "weather": 0.1, "events": 0.2, "historical": 0.4}

    # Actual values (filled in later)
    actual_quantity = Column(Integer, nullable=True)
    actual_revenue = Column(Float, nullable=True)
    forecast_accuracy = Column(Float, nullable=True)  # % accuracy

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class DailyMetrics(Base):
    """Daily business metrics snapshot."""
    __tablename__ = "daily_metrics"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    date = Column(DateTime, nullable=False)

    # Revenue
    total_revenue = Column(Float, default=0.0)
    food_revenue = Column(Float, default=0.0)
    beverage_revenue = Column(Float, default=0.0)
    alcohol_revenue = Column(Float, default=0.0)

    # Orders
    total_orders = Column(Integer, default=0)
    dine_in_orders = Column(Integer, default=0)
    takeout_orders = Column(Integer, default=0)
    delivery_orders = Column(Integer, default=0)

    # Covers
    total_covers = Column(Integer, default=0)
    avg_party_size = Column(Float, nullable=True)

    # Averages
    avg_ticket = Column(Float, nullable=True)
    avg_tip_percent = Column(Float, nullable=True)

    # Tips
    total_tips = Column(Float, default=0.0)
    cash_tips = Column(Float, default=0.0)
    card_tips = Column(Float, default=0.0)

    # Labor
    labor_cost = Column(Float, nullable=True)
    labor_hours = Column(Float, nullable=True)
    labor_percent = Column(Float, nullable=True)

    # Costs
    food_cost = Column(Float, nullable=True)
    food_cost_percent = Column(Float, nullable=True)
    beverage_cost = Column(Float, nullable=True)
    beverage_cost_percent = Column(Float, nullable=True)

    # Profit
    gross_profit = Column(Float, nullable=True)
    net_profit = Column(Float, nullable=True)

    # Comparisons
    vs_last_week = Column(Float, nullable=True)  # % change
    vs_last_month = Column(Float, nullable=True)
    vs_last_year = Column(Float, nullable=True)

    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ConversationalQuery(Base):
    """Log conversational AI analytics queries."""
    __tablename__ = "conversational_queries"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)

    # Query
    query_text = Column(Text, nullable=False)
    query_intent = Column(String(100), nullable=True)  # sales_inquiry, comparison, forecast
    extracted_entities = Column(JSON, nullable=True)
    # {"date_range": "last_week", "metric": "revenue", "product": "pizza"}

    # Response
    response_text = Column(Text, nullable=True)
    response_data = Column(JSON, nullable=True)  # Structured data returned
    sql_generated = Column(Text, nullable=True)  # For debugging

    # Follow-up context
    conversation_id = Column(String(100), nullable=True)  # Group related queries
    parent_query_id = Column(Integer, ForeignKey("conversational_queries.id"), nullable=True)

    # Performance
    processing_time_ms = Column(Integer, nullable=True)
    was_helpful = Column(Boolean, nullable=True)  # User feedback

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Benchmark(Base):
    """Industry benchmarking data."""
    __tablename__ = "benchmarks"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)

    # Category for comparison
    restaurant_type = Column(String(100), nullable=True)  # casual_dining, fine_dining, qsr
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    # Your metrics
    your_avg_ticket = Column(Float, nullable=True)
    your_covers_per_day = Column(Float, nullable=True)
    your_revenue_per_sqft = Column(Float, nullable=True)
    your_labor_percent = Column(Float, nullable=True)
    your_food_cost_percent = Column(Float, nullable=True)
    your_tip_percent = Column(Float, nullable=True)

    # Industry benchmarks
    benchmark_avg_ticket = Column(Float, nullable=True)
    benchmark_covers_per_day = Column(Float, nullable=True)
    benchmark_revenue_per_sqft = Column(Float, nullable=True)
    benchmark_labor_percent = Column(Float, nullable=True)
    benchmark_food_cost_percent = Column(Float, nullable=True)
    benchmark_tip_percent = Column(Float, nullable=True)

    # Percentile ranking
    percentile_avg_ticket = Column(Integer, nullable=True)  # 1-100
    percentile_covers = Column(Integer, nullable=True)
    percentile_revenue = Column(Integer, nullable=True)

    # Recommendations
    improvement_areas = Column(JSON, nullable=True)
    # ["labor_efficiency", "avg_ticket"]

    calculated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class BottleWeight(Base):
    """Bottle weight database for scale integration - WISK style."""
    __tablename__ = "bottle_weights"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)

    # Identification
    barcode = Column(String(100), nullable=True, index=True)
    product_name = Column(String(300), nullable=False)
    brand = Column(String(200), nullable=True)

    # Weights in grams
    full_weight = Column(Float, nullable=False)
    empty_weight = Column(Float, nullable=False)
    volume_ml = Column(Integer, nullable=True)

    # Density for calculation
    alcohol_category = Column(String(100), nullable=True)  # vodka, whiskey, rum
    density = Column(Float, nullable=True)  # g/ml

    # Verification
    is_verified = Column(Boolean, default=False)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_count = Column(Integer, default=0)

    # Source
    source = Column(String(100), nullable=True)  # manual, crowdsourced, imported

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ScaleReading(Base):
    """Bluetooth scale readings for inventory."""
    __tablename__ = "scale_readings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("inventory_sessions.id"), nullable=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    bottle_weight_id = Column(Integer, ForeignKey("bottle_weights.id"), nullable=True)

    # Reading
    weight_grams = Column(Float, nullable=False)
    calculated_remaining_ml = Column(Float, nullable=True)
    calculated_remaining_percent = Column(Float, nullable=True)

    # Method
    reading_method = Column(String(50), nullable=False)  # scale, visual, manual

    # Device info
    scale_device_id = Column(String(100), nullable=True)
    scale_device_name = Column(String(200), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
