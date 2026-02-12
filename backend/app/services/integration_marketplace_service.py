"""
Integration Marketplace Service
Provides 100+ pre-built integrations across all categories
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

# Pre-defined integration catalog (100+ integrations)
INTEGRATION_CATALOG = [
    # ==================== ACCOUNTING (15) ====================
    {"slug": "quickbooks_online", "name": "QuickBooks Online", "category": "accounting", "logo": "/integrations/quickbooks.png", "auth_type": "oauth2", "features": ["sync_sales", "sync_expenses", "sync_invoices", "bank_reconciliation"], "regions": ["US", "CA", "UK", "AU"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "xero", "name": "Xero", "category": "accounting", "logo": "/integrations/xero.png", "auth_type": "oauth2", "features": ["sync_sales", "sync_expenses", "sync_invoices"], "regions": ["global"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "sage_intacct", "name": "Sage Intacct", "category": "accounting", "logo": "/integrations/sage.png", "auth_type": "api_key", "features": ["sync_sales", "sync_expenses", "gl_posting"], "regions": ["US", "UK"], "setup_complexity": "medium"},
    {"slug": "freshbooks", "name": "FreshBooks", "category": "accounting", "logo": "/integrations/freshbooks.png", "auth_type": "oauth2", "features": ["sync_invoices", "sync_expenses"], "regions": ["global"], "setup_complexity": "easy"},
    {"slug": "wave", "name": "Wave Accounting", "category": "accounting", "logo": "/integrations/wave.png", "auth_type": "oauth2", "features": ["sync_sales", "sync_expenses"], "regions": ["US", "CA"], "setup_complexity": "easy"},
    {"slug": "zoho_books", "name": "Zoho Books", "category": "accounting", "logo": "/integrations/zoho.png", "auth_type": "oauth2", "features": ["sync_sales", "sync_invoices"], "regions": ["global"], "setup_complexity": "easy"},
    {"slug": "netsuite", "name": "Oracle NetSuite", "category": "accounting", "logo": "/integrations/netsuite.png", "auth_type": "oauth2", "features": ["full_erp", "sync_sales", "inventory"], "regions": ["global"], "is_popular": True, "setup_complexity": "complex"},
    {"slug": "microsoft_dynamics", "name": "Microsoft Dynamics 365", "category": "accounting", "logo": "/integrations/dynamics.png", "auth_type": "oauth2", "features": ["full_erp", "sync_sales"], "regions": ["global"], "setup_complexity": "complex"},
    {"slug": "sap_business_one", "name": "SAP Business One", "category": "accounting", "logo": "/integrations/sap.png", "auth_type": "api_key", "features": ["full_erp", "sync_sales"], "regions": ["global"], "setup_complexity": "complex"},
    {"slug": "myob", "name": "MYOB", "category": "accounting", "logo": "/integrations/myob.png", "auth_type": "oauth2", "features": ["sync_sales", "sync_expenses"], "regions": ["AU", "NZ"], "setup_complexity": "easy"},
    {"slug": "restaurant365", "name": "Restaurant365", "category": "accounting", "logo": "/integrations/r365.png", "auth_type": "api_key", "features": ["full_restaurant_accounting", "inventory", "scheduling"], "regions": ["US"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "marginedge", "name": "MarginEdge", "category": "accounting", "logo": "/integrations/marginedge.png", "auth_type": "api_key", "features": ["invoice_processing", "food_cost"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "plate_iq", "name": "Plate IQ", "category": "accounting", "logo": "/integrations/plateiq.png", "auth_type": "api_key", "features": ["invoice_ocr", "ap_automation"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "yellow_dog", "name": "Yellow Dog Inventory", "category": "accounting", "logo": "/integrations/yellowdog.png", "auth_type": "api_key", "features": ["inventory_management"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "compeat", "name": "Compeat", "category": "accounting", "logo": "/integrations/compeat.png", "auth_type": "api_key", "features": ["restaurant_accounting", "inventory"], "regions": ["US"], "setup_complexity": "medium"},

    # ==================== PAYMENTS (15) ====================
    {"slug": "stripe", "name": "Stripe", "category": "payment", "logo": "/integrations/stripe.png", "auth_type": "api_key", "features": ["card_processing", "apple_pay", "google_pay"], "regions": ["global"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "square", "name": "Square Payments", "category": "payment", "logo": "/integrations/square.png", "auth_type": "oauth2", "features": ["card_processing", "invoicing"], "regions": ["US", "CA", "UK", "AU", "JP"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "adyen", "name": "Adyen", "category": "payment", "logo": "/integrations/adyen.png", "auth_type": "api_key", "features": ["card_processing", "terminal"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "worldpay", "name": "Worldpay", "category": "payment", "logo": "/integrations/worldpay.png", "auth_type": "api_key", "features": ["card_processing"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "paypal", "name": "PayPal", "category": "payment", "logo": "/integrations/paypal.png", "auth_type": "oauth2", "features": ["online_payments", "qr_payments"], "regions": ["global"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "clover_connect", "name": "Clover Connect", "category": "payment", "logo": "/integrations/clover.png", "auth_type": "api_key", "features": ["card_processing"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "heartland", "name": "Heartland Payment Systems", "category": "payment", "logo": "/integrations/heartland.png", "auth_type": "api_key", "features": ["card_processing", "payroll"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "shift4", "name": "Shift4 Payments", "category": "payment", "logo": "/integrations/shift4.png", "auth_type": "api_key", "features": ["card_processing"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "borica", "name": "Borica", "category": "payment", "logo": "/integrations/borica.png", "auth_type": "api_key", "features": ["card_processing"], "regions": ["BG"], "setup_complexity": "medium"},
    {"slug": "epay", "name": "ePay.bg", "category": "payment", "logo": "/integrations/epay.png", "auth_type": "api_key", "features": ["online_payments"], "regions": ["BG"], "setup_complexity": "easy"},
    {"slug": "sumup", "name": "SumUp", "category": "payment", "logo": "/integrations/sumup.png", "auth_type": "api_key", "features": ["card_processing", "mobile_payments"], "regions": ["EU"], "setup_complexity": "easy"},
    {"slug": "zettle", "name": "Zettle by PayPal", "category": "payment", "logo": "/integrations/zettle.png", "auth_type": "oauth2", "features": ["card_processing"], "regions": ["EU", "US"], "setup_complexity": "easy"},
    {"slug": "tyro", "name": "Tyro", "category": "payment", "logo": "/integrations/tyro.png", "auth_type": "api_key", "features": ["card_processing"], "regions": ["AU"], "setup_complexity": "medium"},
    {"slug": "moneris", "name": "Moneris", "category": "payment", "logo": "/integrations/moneris.png", "auth_type": "api_key", "features": ["card_processing"], "regions": ["CA"], "setup_complexity": "medium"},
    {"slug": "payu", "name": "PayU", "category": "payment", "logo": "/integrations/payu.png", "auth_type": "api_key", "features": ["online_payments"], "regions": ["EU", "LATAM", "ASIA"], "setup_complexity": "easy"},

    # ==================== DELIVERY AGGREGATORS (12) ====================
    {"slug": "ubereats", "name": "Uber Eats", "category": "delivery", "logo": "/integrations/ubereats.png", "auth_type": "oauth2", "features": ["order_sync", "menu_sync", "driver_tracking"], "regions": ["global"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "doordash", "name": "DoorDash", "category": "delivery", "logo": "/integrations/doordash.png", "auth_type": "oauth2", "features": ["order_sync", "menu_sync", "drive"], "regions": ["US", "CA", "AU"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "grubhub", "name": "Grubhub", "category": "delivery", "logo": "/integrations/grubhub.png", "auth_type": "api_key", "features": ["order_sync", "menu_sync"], "regions": ["US"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "deliveroo", "name": "Deliveroo", "category": "delivery", "logo": "/integrations/deliveroo.png", "auth_type": "api_key", "features": ["order_sync", "menu_sync"], "regions": ["UK", "EU", "AU", "ASIA"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "just_eat", "name": "Just Eat", "category": "delivery", "logo": "/integrations/justeat.png", "auth_type": "api_key", "features": ["order_sync", "menu_sync"], "regions": ["UK", "EU"], "setup_complexity": "medium"},
    {"slug": "skip_the_dishes", "name": "Skip The Dishes", "category": "delivery", "logo": "/integrations/skip.png", "auth_type": "api_key", "features": ["order_sync"], "regions": ["CA"], "setup_complexity": "medium"},
    {"slug": "postmates", "name": "Postmates", "category": "delivery", "logo": "/integrations/postmates.png", "auth_type": "api_key", "features": ["order_sync", "delivery"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "glovo", "name": "Glovo", "category": "delivery", "logo": "/integrations/glovo.png", "auth_type": "api_key", "features": ["order_sync", "menu_sync"], "regions": ["EU", "LATAM", "AFRICA"], "setup_complexity": "medium"},
    {"slug": "foodpanda", "name": "Foodpanda", "category": "delivery", "logo": "/integrations/foodpanda.png", "auth_type": "api_key", "features": ["order_sync"], "regions": ["ASIA", "EU"], "setup_complexity": "medium"},
    {"slug": "wolt", "name": "Wolt", "category": "delivery", "logo": "/integrations/wolt.png", "auth_type": "api_key", "features": ["order_sync", "menu_sync"], "regions": ["EU", "ASIA"], "setup_complexity": "medium"},
    {"slug": "deliverect", "name": "Deliverect", "category": "delivery", "logo": "/integrations/deliverect.png", "auth_type": "api_key", "features": ["aggregator_hub", "menu_management"], "regions": ["global"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "otter", "name": "Otter (Cloudkitchens)", "category": "delivery", "logo": "/integrations/otter.png", "auth_type": "api_key", "features": ["aggregator_hub"], "regions": ["global"], "setup_complexity": "easy"},

    # ==================== RESERVATIONS (10) ====================
    {"slug": "opentable", "name": "OpenTable", "category": "reservation", "logo": "/integrations/opentable.png", "auth_type": "api_key", "features": ["reservations", "guest_data", "reviews"], "regions": ["global"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "resy", "name": "Resy", "category": "reservation", "logo": "/integrations/resy.png", "auth_type": "api_key", "features": ["reservations", "guest_data"], "regions": ["US", "UK"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "yelp_reservations", "name": "Yelp Reservations", "category": "reservation", "logo": "/integrations/yelp.png", "auth_type": "api_key", "features": ["reservations", "reviews"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "sevenrooms", "name": "SevenRooms", "category": "reservation", "logo": "/integrations/sevenrooms.png", "auth_type": "api_key", "features": ["reservations", "crm", "marketing"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "tock", "name": "Tock", "category": "reservation", "logo": "/integrations/tock.png", "auth_type": "api_key", "features": ["reservations", "ticketing", "experiences"], "regions": ["US", "UK"], "setup_complexity": "medium"},
    {"slug": "eat_app", "name": "Eat App", "category": "reservation", "logo": "/integrations/eatapp.png", "auth_type": "api_key", "features": ["reservations", "table_management"], "regions": ["global"], "setup_complexity": "easy"},
    {"slug": "quandoo", "name": "Quandoo", "category": "reservation", "logo": "/integrations/quandoo.png", "auth_type": "api_key", "features": ["reservations"], "regions": ["EU", "AU", "ASIA"], "setup_complexity": "easy"},
    {"slug": "the_fork", "name": "TheFork", "category": "reservation", "logo": "/integrations/thefork.png", "auth_type": "api_key", "features": ["reservations", "reviews"], "regions": ["EU", "LATAM", "AU"], "setup_complexity": "easy"},
    {"slug": "tablein", "name": "Tablein", "category": "reservation", "logo": "/integrations/tablein.png", "auth_type": "api_key", "features": ["reservations", "table_management"], "regions": ["EU"], "setup_complexity": "easy"},
    {"slug": "google_reserve", "name": "Google Reserve", "category": "reservation", "logo": "/integrations/google.png", "auth_type": "oauth2", "features": ["reservations", "google_maps"], "regions": ["global"], "is_popular": True, "setup_complexity": "medium"},

    # ==================== LOYALTY & MARKETING (10) ====================
    {"slug": "mailchimp", "name": "Mailchimp", "category": "marketing", "logo": "/integrations/mailchimp.png", "auth_type": "oauth2", "features": ["email_marketing", "automation", "analytics"], "regions": ["global"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "klaviyo", "name": "Klaviyo", "category": "marketing", "logo": "/integrations/klaviyo.png", "auth_type": "api_key", "features": ["email_marketing", "sms", "automation"], "regions": ["global"], "setup_complexity": "easy"},
    {"slug": "fishbowl", "name": "Fishbowl", "category": "marketing", "logo": "/integrations/fishbowl.png", "auth_type": "api_key", "features": ["guest_database", "email_marketing"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "punchh", "name": "Punchh (PAR)", "category": "loyalty", "logo": "/integrations/punchh.png", "auth_type": "api_key", "features": ["loyalty_program", "marketing", "offers"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "paytronix", "name": "Paytronix", "category": "loyalty", "logo": "/integrations/paytronix.png", "auth_type": "api_key", "features": ["loyalty_program", "gift_cards"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "como", "name": "Como", "category": "loyalty", "logo": "/integrations/como.png", "auth_type": "api_key", "features": ["loyalty_program", "crm"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "thanx", "name": "Thanx", "category": "loyalty", "logo": "/integrations/thanx.png", "auth_type": "api_key", "features": ["loyalty_program", "mobile_ordering"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "twilio", "name": "Twilio", "category": "communication", "logo": "/integrations/twilio.png", "auth_type": "api_key", "features": ["sms", "voice", "whatsapp"], "regions": ["global"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "sendgrid", "name": "SendGrid", "category": "communication", "logo": "/integrations/sendgrid.png", "auth_type": "api_key", "features": ["email_delivery", "templates"], "regions": ["global"], "setup_complexity": "easy"},
    {"slug": "birdeye", "name": "Birdeye", "category": "marketing", "logo": "/integrations/birdeye.png", "auth_type": "api_key", "features": ["reviews", "reputation"], "regions": ["US"], "setup_complexity": "easy"},

    # ==================== HR & PAYROLL (10) ====================
    {"slug": "adp", "name": "ADP", "category": "hr_payroll", "logo": "/integrations/adp.png", "auth_type": "oauth2", "features": ["payroll", "hr", "time_tracking"], "regions": ["global"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "gusto", "name": "Gusto", "category": "hr_payroll", "logo": "/integrations/gusto.png", "auth_type": "oauth2", "features": ["payroll", "hr", "benefits"], "regions": ["US"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "paychex", "name": "Paychex", "category": "hr_payroll", "logo": "/integrations/paychex.png", "auth_type": "api_key", "features": ["payroll", "hr"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "7shifts", "name": "7shifts", "category": "hr_payroll", "logo": "/integrations/7shifts.png", "auth_type": "api_key", "features": ["scheduling", "time_tracking", "communication"], "regions": ["US", "CA"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "hotschedules", "name": "HotSchedules (Fourth)", "category": "hr_payroll", "logo": "/integrations/hotschedules.png", "auth_type": "api_key", "features": ["scheduling", "labor_management"], "regions": ["US"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "deputy", "name": "Deputy", "category": "hr_payroll", "logo": "/integrations/deputy.png", "auth_type": "oauth2", "features": ["scheduling", "time_tracking", "communication"], "regions": ["global"], "setup_complexity": "easy"},
    {"slug": "homebase", "name": "Homebase", "category": "hr_payroll", "logo": "/integrations/homebase.png", "auth_type": "api_key", "features": ["scheduling", "time_tracking", "payroll"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "when_i_work", "name": "When I Work", "category": "hr_payroll", "logo": "/integrations/wheniwork.png", "auth_type": "api_key", "features": ["scheduling", "time_tracking"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "planday", "name": "Planday", "category": "hr_payroll", "logo": "/integrations/planday.png", "auth_type": "api_key", "features": ["scheduling", "time_tracking"], "regions": ["EU"], "setup_complexity": "easy"},
    {"slug": "sling", "name": "Sling", "category": "hr_payroll", "logo": "/integrations/sling.png", "auth_type": "api_key", "features": ["scheduling", "communication", "time_tracking"], "regions": ["global"], "setup_complexity": "easy"},

    # ==================== HOTEL PMS (10) ====================
    {"slug": "oracle_opera", "name": "Oracle Opera PMS", "category": "hotel_pms", "logo": "/integrations/opera.png", "auth_type": "api_key", "features": ["room_charge", "guest_sync", "reservations"], "regions": ["global"], "is_popular": True, "setup_complexity": "complex"},
    {"slug": "mews", "name": "Mews", "category": "hotel_pms", "logo": "/integrations/mews.png", "auth_type": "oauth2", "features": ["room_charge", "guest_sync", "reservations"], "regions": ["global"], "is_popular": True, "setup_complexity": "medium"},
    {"slug": "cloudbeds", "name": "Cloudbeds", "category": "hotel_pms", "logo": "/integrations/cloudbeds.png", "auth_type": "api_key", "features": ["room_charge", "guest_sync"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "protel", "name": "Protel", "category": "hotel_pms", "logo": "/integrations/protel.png", "auth_type": "api_key", "features": ["room_charge", "guest_sync"], "regions": ["EU"], "setup_complexity": "medium"},
    {"slug": "clock_pms", "name": "Clock PMS", "category": "hotel_pms", "logo": "/integrations/clock.png", "auth_type": "api_key", "features": ["room_charge", "guest_sync"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "stayntouch", "name": "StayNTouch", "category": "hotel_pms", "logo": "/integrations/stayntouch.png", "auth_type": "api_key", "features": ["room_charge", "guest_sync", "mobile_checkin"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "apaleo", "name": "Apaleo", "category": "hotel_pms", "logo": "/integrations/apaleo.png", "auth_type": "oauth2", "features": ["room_charge", "guest_sync"], "regions": ["EU"], "setup_complexity": "easy"},
    {"slug": "guestline", "name": "Guestline", "category": "hotel_pms", "logo": "/integrations/guestline.png", "auth_type": "api_key", "features": ["room_charge", "guest_sync"], "regions": ["UK", "EU"], "setup_complexity": "medium"},
    {"slug": "infor_hms", "name": "Infor HMS", "category": "hotel_pms", "logo": "/integrations/infor.png", "auth_type": "api_key", "features": ["room_charge", "guest_sync"], "regions": ["global"], "setup_complexity": "complex"},
    {"slug": "roommaster", "name": "RoomMaster", "category": "hotel_pms", "logo": "/integrations/roommaster.png", "auth_type": "api_key", "features": ["room_charge", "guest_sync"], "regions": ["global"], "setup_complexity": "medium"},

    # ==================== INVENTORY & SUPPLY CHAIN (8) ====================
    {"slug": "bluecart", "name": "BlueCart", "category": "inventory", "logo": "/integrations/bluecart.png", "auth_type": "api_key", "features": ["ordering", "supplier_management"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "choco", "name": "Choco", "category": "inventory", "logo": "/integrations/choco.png", "auth_type": "api_key", "features": ["ordering", "communication"], "regions": ["EU", "US"], "setup_complexity": "easy"},
    {"slug": "marketman", "name": "MarketMan", "category": "inventory", "logo": "/integrations/marketman.png", "auth_type": "api_key", "features": ["inventory_management", "recipes", "ordering"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "craftable", "name": "Craftable", "category": "inventory", "logo": "/integrations/craftable.png", "auth_type": "api_key", "features": ["inventory_management", "recipes", "cost_tracking"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "bevspot", "name": "BevSpot", "category": "inventory", "logo": "/integrations/bevspot.png", "auth_type": "api_key", "features": ["bar_inventory", "ordering"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "partender", "name": "Partender", "category": "inventory", "logo": "/integrations/partender.png", "auth_type": "api_key", "features": ["bar_inventory"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "sourcery", "name": "Sourcery", "category": "inventory", "logo": "/integrations/sourcery.png", "auth_type": "api_key", "features": ["ap_automation", "invoice_processing"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "sysco_shop", "name": "Sysco Shop", "category": "inventory", "logo": "/integrations/sysco.png", "auth_type": "api_key", "features": ["ordering", "product_catalog"], "regions": ["US"], "setup_complexity": "easy"},

    # ==================== ANALYTICS (5) ====================
    {"slug": "avero", "name": "Avero", "category": "analytics", "logo": "/integrations/avero.png", "auth_type": "api_key", "features": ["sales_analytics", "labor_analytics"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "ctuit", "name": "Ctuit (Compeat)", "category": "analytics", "logo": "/integrations/ctuit.png", "auth_type": "api_key", "features": ["analytics", "reporting"], "regions": ["US"], "setup_complexity": "medium"},
    {"slug": "datassential", "name": "Datassential", "category": "analytics", "logo": "/integrations/datassential.png", "auth_type": "api_key", "features": ["menu_analytics", "trends"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "google_analytics", "name": "Google Analytics 4", "category": "analytics", "logo": "/integrations/ga4.png", "auth_type": "oauth2", "features": ["web_analytics", "conversion_tracking"], "regions": ["global"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "mixpanel", "name": "Mixpanel", "category": "analytics", "logo": "/integrations/mixpanel.png", "auth_type": "api_key", "features": ["product_analytics", "user_tracking"], "regions": ["global"], "setup_complexity": "easy"},

    # ==================== E-COMMERCE (5) ====================
    {"slug": "shopify", "name": "Shopify", "category": "e_commerce", "logo": "/integrations/shopify.png", "auth_type": "oauth2", "features": ["online_store", "inventory_sync", "orders"], "regions": ["global"], "is_popular": True, "setup_complexity": "easy"},
    {"slug": "woocommerce", "name": "WooCommerce", "category": "e_commerce", "logo": "/integrations/woocommerce.png", "auth_type": "api_key", "features": ["online_store", "inventory_sync"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "bigcommerce", "name": "BigCommerce", "category": "e_commerce", "logo": "/integrations/bigcommerce.png", "auth_type": "oauth2", "features": ["online_store", "orders"], "regions": ["global"], "setup_complexity": "medium"},
    {"slug": "square_online", "name": "Square Online", "category": "e_commerce", "logo": "/integrations/square.png", "auth_type": "oauth2", "features": ["online_store", "orders"], "regions": ["US"], "setup_complexity": "easy"},
    {"slug": "bentobox", "name": "BentoBox", "category": "e_commerce", "logo": "/integrations/bentobox.png", "auth_type": "api_key", "features": ["website", "online_ordering"], "regions": ["US"], "setup_complexity": "easy"},
]


class IntegrationMarketplaceService:
    """Service for managing integration marketplace"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_integrations(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        region: Optional[str] = None,
        popular_only: bool = False,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get all available integrations with filtering"""
        integrations = INTEGRATION_CATALOG.copy()

        # Apply filters
        if category:
            integrations = [i for i in integrations if i["category"] == category]

        if search:
            search_lower = search.lower()
            integrations = [
                i for i in integrations
                if search_lower in i["name"].lower() or search_lower in i.get("description", "").lower()
            ]

        if region:
            integrations = [
                i for i in integrations
                if "global" in i.get("regions", []) or region in i.get("regions", [])
            ]

        if popular_only:
            integrations = [i for i in integrations if i.get("is_popular", False)]

        # Sort by popularity
        integrations.sort(key=lambda x: (not x.get("is_popular", False), x["name"]))

        return {
            "integrations": integrations[:limit],
            "total": len(integrations),
            "categories": self.get_categories()
        }

    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all integration categories with counts"""
        category_counts = {}
        for integration in INTEGRATION_CATALOG:
            cat = integration["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        categories = [
            {"slug": "accounting", "name": "Accounting & Finance", "icon": "calculator", "count": category_counts.get("accounting", 0)},
            {"slug": "payment", "name": "Payment Processing", "icon": "credit-card", "count": category_counts.get("payment", 0)},
            {"slug": "delivery", "name": "Delivery & Aggregators", "icon": "truck", "count": category_counts.get("delivery", 0)},
            {"slug": "reservation", "name": "Reservations", "icon": "calendar", "count": category_counts.get("reservation", 0)},
            {"slug": "loyalty", "name": "Loyalty Programs", "icon": "gift", "count": category_counts.get("loyalty", 0)},
            {"slug": "marketing", "name": "Marketing & Email", "icon": "mail", "count": category_counts.get("marketing", 0)},
            {"slug": "communication", "name": "Communication", "icon": "message-circle", "count": category_counts.get("communication", 0)},
            {"slug": "hr_payroll", "name": "HR & Payroll", "icon": "users", "count": category_counts.get("hr_payroll", 0)},
            {"slug": "hotel_pms", "name": "Hotel PMS", "icon": "building", "count": category_counts.get("hotel_pms", 0)},
            {"slug": "inventory", "name": "Inventory & Supply Chain", "icon": "package", "count": category_counts.get("inventory", 0)},
            {"slug": "analytics", "name": "Analytics", "icon": "bar-chart", "count": category_counts.get("analytics", 0)},
            {"slug": "e_commerce", "name": "E-Commerce", "icon": "shopping-cart", "count": category_counts.get("e_commerce", 0)},
        ]
        return categories

    def get_integration_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get integration details by slug"""
        for integration in INTEGRATION_CATALOG:
            if integration["slug"] == slug:
                return integration
        return None

    def get_popular_integrations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most popular integrations"""
        popular = [i for i in INTEGRATION_CATALOG if i.get("is_popular", False)]
        return popular[:limit]

    def get_integrations_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all integrations in a category"""
        return [i for i in INTEGRATION_CATALOG if i["category"] == category]

    def search_integrations(self, query: str) -> List[Dict[str, Any]]:
        """Search integrations by name or features"""
        query_lower = query.lower()
        results = []
        for integration in INTEGRATION_CATALOG:
            if (query_lower in integration["name"].lower() or
                query_lower in integration.get("description", "").lower() or
                any(query_lower in f.lower() for f in integration.get("features", []))):
                results.append(integration)
        return results

    def connect_integration(
        self,
        venue_id: int,
        slug: str,
        credentials: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Connect venue to an integration"""
        from app.models.enterprise_integrations_models import VenueIntegration, IntegrationMarketplace, IntegrationStatus

        # Find the integration
        integration_info = self.get_integration_by_slug(slug)
        if not integration_info:
            return {"success": False, "error": "Integration not found"}

        # Check if marketplace entry exists, create if not
        marketplace_entry = self.db.query(IntegrationMarketplace).filter(
            IntegrationMarketplace.slug == slug
        ).first()

        if not marketplace_entry:
            marketplace_entry = IntegrationMarketplace(
                slug=slug,
                name=integration_info["name"],
                category=integration_info["category"],
                auth_type=integration_info.get("auth_type"),
                features=integration_info.get("features", []),
                supported_regions=integration_info.get("regions", []),
                is_popular=integration_info.get("is_popular", False),
                setup_complexity=integration_info.get("setup_complexity", "medium")
            )
            self.db.add(marketplace_entry)
            self.db.flush()

        # Check for existing connection
        existing = self.db.query(VenueIntegration).filter(
            VenueIntegration.venue_id == venue_id,
            VenueIntegration.integration_id == marketplace_entry.id
        ).first()

        if existing:
            # Update existing
            existing.credentials = credentials
            existing.settings = settings
            existing.status = IntegrationStatus.CONNECTED
            existing.connected_at = datetime.utcnow()
            self.db.commit()
            return {"success": True, "message": "Integration reconnected", "integration_id": existing.id}

        # Create new connection
        venue_integration = VenueIntegration(
            venue_id=venue_id,
            integration_id=marketplace_entry.id,
            credentials=credentials,
            settings=settings,
            status=IntegrationStatus.CONNECTED,
            connected_at=datetime.utcnow()
        )
        self.db.add(venue_integration)
        self.db.commit()

        return {
            "success": True,
            "message": f"Connected to {integration_info['name']}",
            "integration_id": venue_integration.id
        }

    def disconnect_integration(self, venue_id: int, slug: str) -> Dict[str, Any]:
        """Disconnect venue from an integration"""
        from app.models.enterprise_integrations_models import VenueIntegration, IntegrationMarketplace, IntegrationStatus

        marketplace_entry = self.db.query(IntegrationMarketplace).filter(
            IntegrationMarketplace.slug == slug
        ).first()

        if not marketplace_entry:
            return {"success": False, "error": "Integration not found"}

        venue_integration = self.db.query(VenueIntegration).filter(
            VenueIntegration.venue_id == venue_id,
            VenueIntegration.integration_id == marketplace_entry.id
        ).first()

        if not venue_integration:
            return {"success": False, "error": "Integration not connected"}

        venue_integration.status = IntegrationStatus.AVAILABLE
        venue_integration.is_active = False
        venue_integration.disconnected_at = datetime.utcnow()
        venue_integration.credentials = None
        venue_integration.oauth_tokens = None

        self.db.commit()

        return {"success": True, "message": "Integration disconnected"}

    def get_connected_integrations(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get all connected integrations for a venue"""
        from app.models.enterprise_integrations_models import VenueIntegration, IntegrationMarketplace, IntegrationStatus

        connections = self.db.query(VenueIntegration).filter(
            VenueIntegration.venue_id == venue_id,
            VenueIntegration.status == IntegrationStatus.CONNECTED
        ).all()

        result = []
        for conn in connections:
            marketplace = self.db.query(IntegrationMarketplace).filter(
                IntegrationMarketplace.id == conn.integration_id
            ).first()

            if marketplace:
                result.append({
                    "id": conn.id,
                    "slug": marketplace.slug,
                    "name": marketplace.name,
                    "category": marketplace.category,
                    "status": conn.status.value,
                    "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                    "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None,
                    "total_syncs": conn.total_syncs,
                    "successful_syncs": conn.successful_syncs
                })

        return result

    def get_integration_stats(self, venue_id: int) -> Dict[str, Any]:
        """Get integration statistics for a venue"""
        from app.models.enterprise_integrations_models import VenueIntegration, IntegrationStatus

        total_connected = self.db.query(VenueIntegration).filter(
            VenueIntegration.venue_id == venue_id,
            VenueIntegration.status == IntegrationStatus.CONNECTED
        ).count()

        total_available = len(INTEGRATION_CATALOG)

        connections = self.db.query(VenueIntegration).filter(
            VenueIntegration.venue_id == venue_id,
            VenueIntegration.status == IntegrationStatus.CONNECTED
        ).all()

        total_syncs = sum(c.total_syncs or 0 for c in connections)
        successful_syncs = sum(c.successful_syncs or 0 for c in connections)
        failed_syncs = sum(c.failed_syncs or 0 for c in connections)

        return {
            "total_available": total_available,
            "total_connected": total_connected,
            "total_syncs": total_syncs,
            "successful_syncs": successful_syncs,
            "failed_syncs": failed_syncs,
            "sync_success_rate": round(successful_syncs / total_syncs * 100, 1) if total_syncs > 0 else 0,
            "categories_count": len(self.get_categories())
        }
