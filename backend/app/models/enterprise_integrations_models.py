"""
Enterprise Integration Models - Competitive Feature Parity
Integration Marketplace, AI Invoice OCR, Mobile App Builder, Hotel PMS
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, Enum as SQLEnum, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.db.base import Base


# ==================== INTEGRATION MARKETPLACE ====================

class IntegrationCategory(str, enum.Enum):
    ACCOUNTING = "accounting"
    PAYMENT = "payment"
    DELIVERY = "delivery"
    RESERVATION = "reservation"
    LOYALTY = "loyalty"
    MARKETING = "marketing"
    HR_PAYROLL = "hr_payroll"
    INVENTORY = "inventory"
    ANALYTICS = "analytics"
    HOTEL_PMS = "hotel_pms"
    KITCHEN = "kitchen"
    HARDWARE = "hardware"
    E_COMMERCE = "e_commerce"
    CRM = "crm"
    COMMUNICATION = "communication"
    SOCIAL_MEDIA = "social_media"
    GOVERNMENT = "government"
    INSURANCE = "insurance"


class IntegrationStatus(str, enum.Enum):
    AVAILABLE = "available"
    CONNECTED = "connected"
    PENDING = "pending"
    ERROR = "error"
    DEPRECATED = "deprecated"


class IntegrationMarketplace(Base):
    """Master list of all available integrations (100+ partners)"""
    __tablename__ = "integration_marketplace"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    slug = Column(String(100), unique=True, nullable=False, index=True)  # quickbooks, xero, ubereats
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(SQLEnum(IntegrationCategory), nullable=False, index=True)

    # Branding
    logo_url = Column(String(500))
    website_url = Column(String(500))
    documentation_url = Column(String(500))

    # Features
    features = Column(JSON)  # List of features this integration provides
    supported_regions = Column(JSON)  # List of country codes
    supported_currencies = Column(JSON)

    # Technical
    auth_type = Column(String(50))  # oauth2, api_key, basic, webhook
    api_version = Column(String(50))
    webhook_support = Column(Boolean, default=False)
    realtime_sync = Column(Boolean, default=False)
    bidirectional_sync = Column(Boolean, default=False)

    # Setup
    setup_complexity = Column(String(20))  # easy, medium, complex
    setup_time_minutes = Column(Integer)
    requires_approval = Column(Boolean, default=False)

    # Pricing
    pricing_model = Column(String(50))  # free, paid, freemium, contact
    price_monthly = Column(Float)
    price_per_transaction = Column(Float)

    # Popularity
    total_installs = Column(Integer, default=0)
    average_rating = Column(Float, default=0)
    total_reviews = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_popular = Column(Boolean, default=False)
    is_new = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)
    is_beta = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class VenueIntegration(Base):
    """Venue-specific integration configurations"""
    __tablename__ = "venue_integrations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    integration_id = Column(Integer, ForeignKey("integration_marketplace.id"), nullable=False)

    # Status
    status = Column(SQLEnum(IntegrationStatus), default=IntegrationStatus.PENDING)
    is_active = Column(Boolean, default=True)

    # Authentication (encrypted)
    credentials = Column(JSON)  # Encrypted credentials storage
    oauth_tokens = Column(JSON)  # OAuth tokens if applicable
    token_expires_at = Column(DateTime)

    # Configuration
    settings = Column(JSON)  # Integration-specific settings
    field_mappings = Column(JSON)  # Field mapping configuration
    sync_settings = Column(JSON)  # Sync frequency, direction, etc.

    # Sync stats
    last_sync_at = Column(DateTime)
    next_sync_at = Column(DateTime)
    sync_frequency_minutes = Column(Integer, default=60)
    total_syncs = Column(Integer, default=0)
    successful_syncs = Column(Integer, default=0)
    failed_syncs = Column(Integer, default=0)

    # Error tracking
    last_error = Column(Text)
    last_error_at = Column(DateTime)
    consecutive_failures = Column(Integer, default=0)

    # Metadata
    connected_at = Column(DateTime)
    connected_by = Column(Integer, ForeignKey("staff_users.id"))
    disconnected_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="venue_integrations")
    marketplace_integration = relationship("IntegrationMarketplace", backref="venue_connections")


class IntegrationReview(Base):
    """User reviews for integrations"""
    __tablename__ = "integration_reviews"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integration_marketplace.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("staff_users.id"), nullable=False)

    rating = Column(Integer, nullable=False)  # 1-5
    title = Column(String(200))
    review_text = Column(Text)

    # Helpfulness
    helpful_count = Column(Integer, default=0)
    not_helpful_count = Column(Integer, default=0)

    # Moderation
    is_verified = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== AI INVOICE OCR ====================

class InvoiceOCRStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ERROR = "error"


class InvoiceOCRJob(Base):
    """AI-powered invoice OCR processing jobs"""
    __tablename__ = "invoice_ocr_jobs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # Source
    source_type = Column(String(50))  # upload, email, api
    original_filename = Column(String(500))
    file_url = Column(String(1000))
    file_type = Column(String(50))  # pdf, image, jpeg, png
    file_size_bytes = Column(Integer)

    # Processing
    status = Column(SQLEnum(InvoiceOCRStatus), default=InvoiceOCRStatus.PENDING)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    processing_time_ms = Column(Integer)

    # AI Extraction Results
    confidence_score = Column(Float)  # 0-1 overall confidence
    extracted_data = Column(JSON)  # Full extracted data

    # Key extracted fields
    vendor_name = Column(String(500))
    vendor_tax_id = Column(String(100))
    invoice_number = Column(String(100))
    invoice_date = Column(Date)
    due_date = Column(Date)
    currency = Column(String(10))
    subtotal = Column(Float)
    tax_amount = Column(Float)
    total_amount = Column(Float)

    # Line items
    line_items = Column(JSON)  # Array of extracted line items
    line_items_count = Column(Integer, default=0)

    # Matching
    matched_supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    matched_purchase_order_id = Column(Integer)
    auto_matched = Column(Boolean, default=False)
    match_confidence = Column(Float)

    # Review
    needs_manual_review = Column(Boolean, default=False)
    review_notes = Column(Text)
    reviewed_by = Column(Integer, ForeignKey("staff_users.id"))
    reviewed_at = Column(DateTime)

    # Linked invoice
    created_invoice_id = Column(Integer, ForeignKey("supplier_invoices.id"))

    # Errors
    error_message = Column(Text)
    warnings = Column(JSON)  # Non-fatal warnings

    # Language detection
    detected_language = Column(String(10))

    # Audit
    uploaded_by = Column(Integer, ForeignKey("staff_users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="invoice_ocr_jobs")


class InvoiceOCRLineItem(Base):
    """Individual line items extracted from invoices"""
    __tablename__ = "invoice_ocr_line_items"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    ocr_job_id = Column(Integer, ForeignKey("invoice_ocr_jobs.id"), nullable=False)

    # Extracted data
    line_number = Column(Integer)
    description = Column(Text)
    sku = Column(String(100))
    quantity = Column(Float)
    unit = Column(String(50))
    unit_price = Column(Float)
    total_price = Column(Float)
    tax_rate = Column(Float)

    # Matching
    matched_stock_item_id = Column(Integer, ForeignKey("stock_items.id"))
    match_confidence = Column(Float)
    auto_matched = Column(Boolean, default=False)

    # Confidence scores per field
    confidence_scores = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ocr_job = relationship("InvoiceOCRJob", backref="extracted_line_items")


class InvoiceOCRTemplate(Base):
    """Learned templates for supplier invoice formats"""
    __tablename__ = "invoice_ocr_templates"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))

    # Template info
    name = Column(String(200))
    description = Column(Text)

    # Field positions/rules
    template_rules = Column(JSON)  # AI-learned extraction rules
    field_positions = Column(JSON)  # Coordinate-based positions

    # Performance
    times_used = Column(Integer, default=0)
    average_confidence = Column(Float)
    success_rate = Column(Float)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== BRANDED MOBILE APP BUILDER ====================

class MobileAppStatus(str, enum.Enum):
    DRAFT = "draft"
    BUILDING = "building"
    REVIEW = "review"
    PUBLISHED = "published"
    SUSPENDED = "suspended"


class MobileAppPlatform(str, enum.Enum):
    IOS = "ios"
    ANDROID = "android"
    BOTH = "both"


class BrandedMobileApp(Base):
    """Branded mobile app configuration"""
    __tablename__ = "branded_mobile_apps"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # App identity
    app_name = Column(String(200), nullable=False)
    app_description = Column(Text)
    bundle_id = Column(String(200))  # com.restaurant.myapp
    package_name = Column(String(200))  # Android package name

    # Status
    status = Column(SQLEnum(MobileAppStatus), default=MobileAppStatus.DRAFT)
    platforms = Column(SQLEnum(MobileAppPlatform), default=MobileAppPlatform.BOTH)

    # Branding
    primary_color = Column(String(20))
    secondary_color = Column(String(20))
    accent_color = Column(String(20))
    background_color = Column(String(20))
    text_color = Column(String(20))

    # Assets
    app_icon_url = Column(String(500))
    splash_screen_url = Column(String(500))
    logo_url = Column(String(500))
    header_image_url = Column(String(500))

    # Features enabled
    features = Column(JSON)  # List of enabled features

    # Store listings
    ios_app_store_url = Column(String(500))
    android_play_store_url = Column(String(500))

    # Versions
    current_ios_version = Column(String(20))
    current_android_version = Column(String(20))
    min_ios_version = Column(String(20))
    min_android_version = Column(String(20))

    # Analytics
    total_downloads = Column(Integer, default=0)
    ios_downloads = Column(Integer, default=0)
    android_downloads = Column(Integer, default=0)
    active_users = Column(Integer, default=0)

    # Push notifications
    push_enabled = Column(Boolean, default=True)
    fcm_server_key = Column(Text)  # Firebase Cloud Messaging
    apns_key_id = Column(String(100))  # Apple Push Notification Service
    apns_team_id = Column(String(100))

    # Timestamps
    published_at = Column(DateTime)
    last_build_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    venue = relationship("Venue", backref="branded_mobile_apps")


class MobileAppFeature(Base):
    """Features available for mobile apps"""
    __tablename__ = "mobile_app_features"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)

    slug = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # ordering, loyalty, account, social

    # Configuration schema
    config_schema = Column(JSON)
    default_config = Column(JSON)

    # Requirements
    requires_features = Column(JSON)  # Dependencies on other features
    incompatible_with = Column(JSON)  # Mutually exclusive features

    # Availability
    is_premium = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class MobileAppBuild(Base):
    """Build history for mobile apps"""
    __tablename__ = "mobile_app_builds"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("branded_mobile_apps.id"), nullable=False)

    # Build info
    version = Column(String(20), nullable=False)
    build_number = Column(Integer, nullable=False)
    platform = Column(SQLEnum(MobileAppPlatform), nullable=False)

    # Status
    status = Column(String(50))  # queued, building, completed, failed

    # Output
    build_url = Column(String(500))  # Download URL for the build
    build_size_mb = Column(Float)

    # Timing
    queued_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    build_duration_seconds = Column(Integer)

    # Logs
    build_log = Column(Text)
    error_message = Column(Text)

    # Release
    release_notes = Column(Text)
    is_released = Column(Boolean, default=False)
    released_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    app = relationship("BrandedMobileApp", backref="builds")


class MobileAppScreen(Base):
    """Custom screens/pages for mobile app"""
    __tablename__ = "mobile_app_screens"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("branded_mobile_apps.id"), nullable=False)

    # Screen info
    slug = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    screen_type = Column(String(50))  # menu, about, contact, custom, promo

    # Content
    content = Column(JSON)  # Screen content/layout definition

    # Navigation
    show_in_menu = Column(Boolean, default=True)
    menu_order = Column(Integer, default=0)
    menu_icon = Column(String(100))

    # Visibility
    is_active = Column(Boolean, default=True)
    requires_login = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    app = relationship("BrandedMobileApp", backref="screens")


class MobileAppPushCampaign(Base):
    """Push notification campaigns"""
    __tablename__ = "mobile_app_push_campaigns"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(Integer, ForeignKey("branded_mobile_apps.id"), nullable=False)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    # Campaign info
    name = Column(String(200), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)

    # Rich content
    image_url = Column(String(500))
    action_url = Column(String(500))  # Deep link or URL
    action_type = Column(String(50))  # open_app, open_url, open_screen

    # Targeting
    target_audience = Column(String(50))  # all, segment, individual
    segment_criteria = Column(JSON)
    target_user_ids = Column(JSON)

    # Scheduling
    send_type = Column(String(50))  # immediate, scheduled, recurring
    scheduled_at = Column(DateTime)
    recurring_schedule = Column(JSON)  # Cron-like schedule

    # Status
    status = Column(String(50))  # draft, scheduled, sending, sent, cancelled

    # Stats
    total_sent = Column(Integer, default=0)
    total_delivered = Column(Integer, default=0)
    total_opened = Column(Integer, default=0)
    total_clicked = Column(Integer, default=0)

    # Timing
    sent_at = Column(DateTime)
    completed_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff_users.id"))

    # Relationships
    app = relationship("BrandedMobileApp", backref="push_campaigns")


# ==================== HOTEL PMS INTEGRATION ====================

class HotelPMSProvider(str, enum.Enum):
    OPERA = "opera"  # Oracle Opera
    MEWS = "mews"
    CLOUDBEDS = "cloudbeds"
    PROTEL = "protel"
    CLOCK = "clock"
    STAYNTOUCH = "stayntouch"
    APALEO = "apaleo"
    GUESTLINE = "guestline"
    INFOR = "infor"
    CUSTOM = "custom"


class RoomChargeStatus(str, enum.Enum):
    PENDING = "pending"
    POSTED = "posted"
    REJECTED = "rejected"
    VOID = "void"


class EnterpriseHotelPMSConnection(Base):
    """Hotel PMS integration configuration"""
    __tablename__ = "enterprise_hotel_pms_connections"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)

    # PMS Provider
    provider = Column(SQLEnum(HotelPMSProvider), nullable=False)
    provider_name = Column(String(200))  # Human-readable name

    # Connection
    api_endpoint = Column(String(500))
    api_version = Column(String(50))

    # Authentication (encrypted)
    credentials = Column(JSON)

    # Hotel info
    hotel_id = Column(String(100))
    hotel_name = Column(String(200))
    property_code = Column(String(50))

    # Status
    is_active = Column(Boolean, default=True)
    is_connected = Column(Boolean, default=False)
    connection_status = Column(String(50))
    last_health_check = Column(DateTime)

    # Feature flags
    room_charge_enabled = Column(Boolean, default=True)
    guest_sync_enabled = Column(Boolean, default=True)
    reservation_sync_enabled = Column(Boolean, default=False)

    # Mapping
    outlet_mapping = Column(JSON)  # Map POS outlets to PMS revenue centers
    payment_type_mapping = Column(JSON)  # Map payment types

    # Error tracking
    last_error = Column(Text)
    last_error_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="enterprise_pms_connections")


class EnterpriseHotelGuest(Base):
    """Synced hotel guest information"""
    __tablename__ = "enterprise_hotel_guests"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    pms_connection_id = Column(Integer, ForeignKey("enterprise_hotel_pms_connections.id"))

    # PMS Reference
    pms_guest_id = Column(String(100), index=True)
    pms_reservation_id = Column(String(100), index=True)

    # Guest info
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))

    # Room info
    room_number = Column(String(20))
    room_type = Column(String(100))

    # Stay info
    check_in_date = Column(Date)
    check_out_date = Column(Date)
    nights = Column(Integer)

    # Status
    is_checked_in = Column(Boolean, default=False)
    is_vip = Column(Boolean, default=False)
    vip_level = Column(String(20))

    # Credit
    room_charge_enabled = Column(Boolean, default=True)
    credit_limit = Column(Float)
    current_balance = Column(Float, default=0)

    # Preferences
    preferences = Column(JSON)
    notes = Column(Text)

    # Linked customer
    customer_id = Column(Integer, ForeignKey("customers.id"))

    # Sync
    last_synced_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="ent_hotel_guests")
    pms_connection = relationship("EnterpriseHotelPMSConnection", backref="ent_guests")


class EnterpriseRoomCharge(Base):
    """Charges posted to guest rooms"""
    __tablename__ = "enterprise_room_charges"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False, index=True)
    pms_connection_id = Column(Integer, ForeignKey("enterprise_hotel_pms_connections.id"))
    hotel_guest_id = Column(Integer, ForeignKey("enterprise_hotel_guests.id"))

    # Order reference
    order_id = Column(Integer, ForeignKey("orders.id"))

    # PMS Reference
    pms_posting_id = Column(String(100))
    pms_folio_id = Column(String(100))

    # Room info
    room_number = Column(String(20), nullable=False)
    guest_name = Column(String(200))

    # Charge details
    charge_type = Column(String(50))  # food, beverage, service
    description = Column(String(500))
    amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")

    # Revenue center
    revenue_center_code = Column(String(50))
    revenue_center_name = Column(String(200))

    # Status
    status = Column(SQLEnum(RoomChargeStatus), default=RoomChargeStatus.PENDING)

    # Timing
    charge_date = Column(DateTime, nullable=False)
    posted_at = Column(DateTime)

    # Errors
    rejection_reason = Column(Text)
    retry_count = Column(Integer, default=0)

    # Audit
    posted_by = Column(Integer, ForeignKey("staff_users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    venue = relationship("Venue", backref="ent_room_charges")
    hotel_guest = relationship("EnterpriseHotelGuest", backref="ent_room_charges")


class EnterpriseHotelReservationSync(Base):
    """Synced hotel reservations for restaurant reservations"""
    __tablename__ = "enterprise_hotel_reservation_syncs"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    pms_connection_id = Column(Integer, ForeignKey("enterprise_hotel_pms_connections.id"))

    # PMS Reference
    pms_reservation_id = Column(String(100))
    pms_guest_id = Column(String(100))

    # Restaurant reservation
    restaurant_reservation_id = Column(Integer, ForeignKey("reservations.id"))

    # Details
    guest_name = Column(String(200))
    room_number = Column(String(20))
    party_size = Column(Integer)
    reservation_date = Column(Date)
    reservation_time = Column(String(10))

    # Special requests
    special_requests = Column(Text)
    dining_preferences = Column(JSON)

    # Status
    sync_status = Column(String(50))
    last_synced_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EnterpriseHotelPackage(Base):
    """Hotel packages that include F&B credits"""
    __tablename__ = "enterprise_hotel_packages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    pms_connection_id = Column(Integer, ForeignKey("enterprise_hotel_pms_connections.id"))

    # Package info
    pms_package_code = Column(String(50))
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # F&B Credits
    fb_credit_amount = Column(Float)
    fb_credit_type = Column(String(50))  # per_night, per_stay, per_person
    applicable_outlets = Column(JSON)  # List of venue IDs or outlet codes

    # Rules
    is_transferable = Column(Boolean, default=False)
    expires_on_checkout = Column(Boolean, default=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EnterpriseGuestFBCredit(Base):
    """F&B credits for hotel guests"""
    __tablename__ = "enterprise_guest_fb_credits"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    hotel_guest_id = Column(Integer, ForeignKey("enterprise_hotel_guests.id"), nullable=False)
    hotel_package_id = Column(Integer, ForeignKey("enterprise_hotel_packages.id"))

    # Credit info
    credit_type = Column(String(50))  # package, complimentary, compensation
    original_amount = Column(Float, nullable=False)
    remaining_amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")

    # Validity
    valid_from = Column(Date)
    valid_until = Column(Date)

    # Status
    is_active = Column(Boolean, default=True)
    is_expired = Column(Boolean, default=False)

    # Usage tracking
    times_used = Column(Integer, default=0)
    total_used = Column(Float, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    hotel_guest = relationship("EnterpriseHotelGuest", backref="ent_fb_credits")
