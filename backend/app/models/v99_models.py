"""V99 feature models — IoT, signage, pour tracking, skill matrix, geo-fencing, shelf life, social content."""

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Numeric, Boolean,
    ForeignKey, Text, JSON, Float,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


# ===================== IoT SENSORS =====================

class IoTSensor(Base):
    """Physical IoT sensor device."""
    __tablename__ = "iot_sensors"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    device_type = Column(String(50), nullable=False)  # temperature, scale, table_sensor, flow_meter
    device_id = Column(String(100), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    location = Column(String(200))  # e.g., "Walk-in Cooler A", "Bar Station 1"
    zone = Column(String(100))  # cooler, freezer, prep_area, hot_holding, cold_holding
    is_active = Column(Boolean, default=True)
    last_reading_at = Column(DateTime(timezone=True))
    last_reading_value = Column(Float)
    min_threshold = Column(Float)
    max_threshold = Column(Float)
    alert_enabled = Column(Boolean, default=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IoTReading(Base):
    """Time-series reading from an IoT sensor."""
    __tablename__ = "iot_readings"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("iot_sensors.id"), nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String(20))  # celsius, fahrenheit, kg, lb, ml, L
    is_in_range = Column(Boolean, default=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class IoTAlert(Base):
    """Alert triggered by out-of-range IoT reading."""
    __tablename__ = "iot_alerts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("iot_sensors.id"), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # temperature_high, temperature_low, offline
    severity = Column(String(20), default="warning")  # info, warning, critical
    reading_value = Column(Float)
    threshold_value = Column(Float)
    message = Column(Text)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(Integer, ForeignKey("users.id"))
    acknowledged_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ===================== DIGITAL SIGNAGE =====================

class DigitalDisplay(Base):
    """Digital signage display device."""
    __tablename__ = "digital_displays"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    location = Column(String(200))
    display_type = Column(String(50), default="menu_board")  # menu_board, promo, welcome, kds
    resolution = Column(String(20), default="1920x1080")
    orientation = Column(String(20), default="landscape")  # landscape, portrait
    is_online = Column(Boolean, default=False)
    last_heartbeat = Column(DateTime(timezone=True))
    current_content_id = Column(Integer, ForeignKey("signage_content.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SignageContent(Base):
    """Content template for digital signage."""
    __tablename__ = "signage_content"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    content_type = Column(String(50), nullable=False)  # menu, promotion, announcement, daily_special
    template = Column(String(100))  # template identifier
    data = Column(JSON, default=dict)  # dynamic content data
    duration_seconds = Column(Integer, default=30)
    is_active = Column(Boolean, default=True)
    schedule_start = Column(DateTime(timezone=True))
    schedule_end = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ===================== POUR TRACKING =====================

class PourRecord(Base):
    """Individual pour measurement record."""
    __tablename__ = "pour_records"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), index=True)
    product_id = Column(Integer, index=True)
    product_name = Column(String(200))
    expected_ml = Column(Float, nullable=False)
    actual_ml = Column(Float, nullable=False)
    variance_ml = Column(Float)  # actual - expected
    variance_pct = Column(Float)  # (actual - expected) / expected * 100
    pour_type = Column(String(30), default="standard")  # standard, double, shot, free_pour
    station = Column(String(100))
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


# ===================== SKILL MATRIX =====================

class StaffSkill(Base):
    """Staff skill proficiency assessment."""
    __tablename__ = "staff_skills"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    skill_name = Column(String(100), nullable=False)
    skill_category = Column(String(50))  # kitchen, bar, service, management, safety
    proficiency_level = Column(Integer, default=1)  # 1-5
    certified = Column(Boolean, default=False)
    certified_date = Column(Date)
    expiry_date = Column(Date)
    assessed_by = Column(Integer, ForeignKey("users.id"))
    notes = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ===================== GEO-FENCING =====================

class GeoFence(Base):
    """Geofence zone for clock-in validation."""
    __tablename__ = "geo_fences"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_meters = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class GeoClockEvent(Base):
    """Clock-in/out event with geo validation."""
    __tablename__ = "geo_clock_events"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)  # clock_in, clock_out
    latitude = Column(Float)
    longitude = Column(Float)
    distance_meters = Column(Float)
    within_fence = Column(Boolean)
    override_reason = Column(Text)
    approved_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ===================== SHELF LIFE TRACKING =====================

class ShelfLifeItem(Base):
    """Tracks shelf life and expiry for inventory items."""
    __tablename__ = "shelf_life_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    product_id = Column(Integer, index=True)
    product_name = Column(String(200), nullable=False)
    batch_id = Column(String(100))
    received_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    quantity = Column(Float, default=0)
    unit = Column(String(20))
    storage_location = Column(String(100))
    status = Column(String(30), default="fresh")  # fresh, use_soon, expiring, expired, discarded
    discarded_at = Column(DateTime(timezone=True))
    discarded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ===================== SOCIAL CONTENT =====================

class SocialPost(Base):
    """AI-generated social media content."""
    __tablename__ = "social_posts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    platform = Column(String(30), nullable=False)  # instagram, facebook, twitter, tiktok
    content_type = Column(String(50))  # daily_special, event, promotion, behind_scenes
    caption = Column(Text, nullable=False)
    hashtags = Column(JSON, default=list)
    image_url = Column(String(500))
    scheduled_at = Column(DateTime(timezone=True))
    published_at = Column(DateTime(timezone=True))
    status = Column(String(20), default="draft")  # draft, scheduled, published, failed
    engagement_likes = Column(Integer, default=0)
    engagement_comments = Column(Integer, default=0)
    engagement_shares = Column(Integer, default=0)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ===================== MULTI-TENANT =====================

class Tenant(Base):
    """Multi-tenant organization."""
    __tablename__ = "tenants"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), default="standard")  # starter, standard, premium, enterprise
    is_active = Column(Boolean, default=True)
    suspended_at = Column(DateTime(timezone=True))
    suspension_reason = Column(Text)
    max_venues = Column(Integer, default=5)
    max_users = Column(Integer, default=50)
    settings = Column(JSON, default=dict)
    billing_email = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TenantUsage(Base):
    """Monthly usage tracking per tenant."""
    __tablename__ = "tenant_usage"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    month = Column(Date, nullable=False)
    orders_count = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    storage_mb = Column(Float, default=0)
    active_venues = Column(Integer, default=0)
    active_users = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
