"""
Branded Mobile App Builder Service
Create custom branded iOS and Android apps for restaurants
Like Toast's Branded Mobile App feature
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session


# Available features for mobile apps
MOBILE_APP_FEATURES = [
    {
        "slug": "online_ordering",
        "name": "Online Ordering",
        "description": "Allow customers to browse menu and place orders",
        "category": "ordering",
        "is_premium": False,
        "config_schema": {
            "allow_scheduled_orders": {"type": "boolean", "default": True},
            "allow_asap_orders": {"type": "boolean", "default": True},
            "order_types": {"type": "array", "default": ["pickup", "delivery", "dine_in"]}
        }
    },
    {
        "slug": "loyalty_program",
        "name": "Loyalty Program",
        "description": "Integrated loyalty points and rewards",
        "category": "loyalty",
        "is_premium": False,
        "config_schema": {
            "show_points_balance": {"type": "boolean", "default": True},
            "show_rewards": {"type": "boolean", "default": True},
            "show_tier_progress": {"type": "boolean", "default": True}
        }
    },
    {
        "slug": "push_notifications",
        "name": "Push Notifications",
        "description": "Send targeted notifications to customers",
        "category": "marketing",
        "is_premium": False,
        "config_schema": {
            "order_status_updates": {"type": "boolean", "default": True},
            "promotional_messages": {"type": "boolean", "default": True},
            "loyalty_alerts": {"type": "boolean", "default": True}
        }
    },
    {
        "slug": "order_tracking",
        "name": "Order Tracking",
        "description": "Real-time order status tracking",
        "category": "ordering",
        "is_premium": False,
        "config_schema": {
            "show_prep_time": {"type": "boolean", "default": True},
            "show_driver_location": {"type": "boolean", "default": True}
        }
    },
    {
        "slug": "table_reservations",
        "name": "Table Reservations",
        "description": "Allow customers to make reservations",
        "category": "reservations",
        "is_premium": False,
        "config_schema": {
            "allow_special_requests": {"type": "boolean", "default": True},
            "require_deposit": {"type": "boolean", "default": False}
        }
    },
    {
        "slug": "gift_cards",
        "name": "Gift Cards",
        "description": "Purchase and redeem digital gift cards",
        "category": "payments",
        "is_premium": False,
        "config_schema": {
            "allow_purchase": {"type": "boolean", "default": True},
            "allow_redemption": {"type": "boolean", "default": True},
            "custom_amounts": {"type": "boolean", "default": True}
        }
    },
    {
        "slug": "saved_payment_methods",
        "name": "Saved Payment Methods",
        "description": "Save cards for faster checkout",
        "category": "payments",
        "is_premium": False,
        "config_schema": {
            "apple_pay": {"type": "boolean", "default": True},
            "google_pay": {"type": "boolean", "default": True},
            "save_cards": {"type": "boolean", "default": True}
        }
    },
    {
        "slug": "order_history",
        "name": "Order History",
        "description": "View past orders and reorder favorites",
        "category": "account",
        "is_premium": False,
        "config_schema": {
            "show_receipts": {"type": "boolean", "default": True},
            "allow_reorder": {"type": "boolean", "default": True}
        }
    },
    {
        "slug": "favorites",
        "name": "Favorites",
        "description": "Save favorite menu items",
        "category": "ordering",
        "is_premium": False,
        "config_schema": {}
    },
    {
        "slug": "qr_code_scanner",
        "name": "QR Code Scanner",
        "description": "Scan QR codes for table ordering and promotions",
        "category": "ordering",
        "is_premium": False,
        "config_schema": {}
    },
    {
        "slug": "social_sharing",
        "name": "Social Sharing",
        "description": "Share orders and experiences on social media",
        "category": "social",
        "is_premium": False,
        "config_schema": {
            "facebook": {"type": "boolean", "default": True},
            "instagram": {"type": "boolean", "default": True},
            "twitter": {"type": "boolean", "default": True}
        }
    },
    {
        "slug": "referral_program",
        "name": "Referral Program",
        "description": "Refer friends and earn rewards",
        "category": "loyalty",
        "is_premium": True,
        "config_schema": {
            "referrer_reward": {"type": "number", "default": 5},
            "referee_reward": {"type": "number", "default": 5}
        }
    },
    {
        "slug": "in_app_chat",
        "name": "In-App Chat",
        "description": "Chat with restaurant for support",
        "category": "support",
        "is_premium": True,
        "config_schema": {}
    },
    {
        "slug": "ar_menu",
        "name": "AR Menu Preview",
        "description": "View dishes in augmented reality",
        "category": "ordering",
        "is_premium": True,
        "config_schema": {}
    },
    {
        "slug": "allergen_filter",
        "name": "Allergen Filter",
        "description": "Filter menu by dietary restrictions and allergies",
        "category": "ordering",
        "is_premium": False,
        "config_schema": {}
    },
    {
        "slug": "nutritional_info",
        "name": "Nutritional Information",
        "description": "Display calories and nutritional data",
        "category": "ordering",
        "is_premium": False,
        "config_schema": {}
    },
    {
        "slug": "multi_location",
        "name": "Multi-Location Support",
        "description": "Support for multiple restaurant locations",
        "category": "locations",
        "is_premium": False,
        "config_schema": {
            "show_map": {"type": "boolean", "default": True},
            "show_distance": {"type": "boolean", "default": True}
        }
    },
    {
        "slug": "catering",
        "name": "Catering Orders",
        "description": "Place large catering orders",
        "category": "ordering",
        "is_premium": True,
        "config_schema": {
            "minimum_order": {"type": "number", "default": 100},
            "advance_notice_hours": {"type": "number", "default": 24}
        }
    }
]


class MobileAppBuilderService:
    """Service for creating branded mobile apps"""

    def __init__(self, db: Session):
        self.db = db

    def create_app(
        self,
        venue_id: int,
        app_name: str,
        created_by: int,
        app_description: Optional[str] = None,
        primary_color: str = "#FF6B35",
        secondary_color: str = "#004E89"
    ) -> Dict[str, Any]:
        """Create a new branded mobile app"""
        from app.models.enterprise_integrations_models import BrandedMobileApp, MobileAppStatus

        # Check for existing app
        existing = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if existing:
            return {
                "success": False,
                "error": "App already exists for this venue",
                "app_id": existing.id
            }

        app = BrandedMobileApp(
            venue_id=venue_id,
            app_name=app_name,
            app_description=app_description,
            status=MobileAppStatus.DRAFT,
            primary_color=primary_color,
            secondary_color=secondary_color,
            accent_color="#FFC107",
            background_color="#FFFFFF",
            text_color="#333333",
            features=[
                "online_ordering",
                "loyalty_program",
                "push_notifications",
                "order_tracking",
                "order_history",
                "favorites"
            ],
            created_by=created_by
        )
        self.db.add(app)
        self.db.commit()

        return {
            "success": True,
            "app_id": app.id,
            "message": "App created successfully"
        }

    def get_app(self, venue_id: int) -> Optional[Dict[str, Any]]:
        """Get app configuration for a venue"""
        from app.models.enterprise_integrations_models import BrandedMobileApp

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return None

        return {
            "id": app.id,
            "app_name": app.app_name,
            "app_description": app.app_description,
            "bundle_id": app.bundle_id,
            "package_name": app.package_name,
            "status": app.status.value,
            "platforms": app.platforms.value if app.platforms else "both",
            "branding": {
                "primary_color": app.primary_color,
                "secondary_color": app.secondary_color,
                "accent_color": app.accent_color,
                "background_color": app.background_color,
                "text_color": app.text_color,
                "app_icon_url": app.app_icon_url,
                "splash_screen_url": app.splash_screen_url,
                "logo_url": app.logo_url,
                "header_image_url": app.header_image_url
            },
            "features": app.features or [],
            "store_urls": {
                "ios": app.ios_app_store_url,
                "android": app.android_play_store_url
            },
            "versions": {
                "ios": app.current_ios_version,
                "android": app.current_android_version
            },
            "analytics": {
                "total_downloads": app.total_downloads,
                "ios_downloads": app.ios_downloads,
                "android_downloads": app.android_downloads,
                "active_users": app.active_users
            },
            "push_enabled": app.push_enabled,
            "published_at": app.published_at.isoformat() if app.published_at else None,
            "last_build_at": app.last_build_at.isoformat() if app.last_build_at else None,
            "created_at": app.created_at.isoformat()
        }

    def update_branding(
        self,
        venue_id: int,
        branding: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update app branding (colors, logos, etc.)"""
        from app.models.enterprise_integrations_models import BrandedMobileApp

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return {"success": False, "error": "App not found"}

        # Update branding fields
        if "primary_color" in branding:
            app.primary_color = branding["primary_color"]
        if "secondary_color" in branding:
            app.secondary_color = branding["secondary_color"]
        if "accent_color" in branding:
            app.accent_color = branding["accent_color"]
        if "background_color" in branding:
            app.background_color = branding["background_color"]
        if "text_color" in branding:
            app.text_color = branding["text_color"]
        if "app_icon_url" in branding:
            app.app_icon_url = branding["app_icon_url"]
        if "splash_screen_url" in branding:
            app.splash_screen_url = branding["splash_screen_url"]
        if "logo_url" in branding:
            app.logo_url = branding["logo_url"]
        if "header_image_url" in branding:
            app.header_image_url = branding["header_image_url"]

        self.db.commit()

        return {"success": True, "message": "Branding updated"}

    def update_features(
        self,
        venue_id: int,
        features: List[str]
    ) -> Dict[str, Any]:
        """Update enabled features"""
        from app.models.enterprise_integrations_models import BrandedMobileApp

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return {"success": False, "error": "App not found"}

        # Validate features
        valid_features = [f["slug"] for f in MOBILE_APP_FEATURES]
        invalid = [f for f in features if f not in valid_features]
        if invalid:
            return {"success": False, "error": f"Invalid features: {invalid}"}

        app.features = features
        self.db.commit()

        return {"success": True, "message": "Features updated", "enabled_features": features}

    def get_available_features(self) -> List[Dict[str, Any]]:
        """Get all available features"""
        return MOBILE_APP_FEATURES

    def start_build(
        self,
        venue_id: int,
        platform: str,
        version: str,
        release_notes: str,
        created_by: int
    ) -> Dict[str, Any]:
        """Start a new app build"""
        from app.models.enterprise_integrations_models import (
            BrandedMobileApp, MobileAppBuild, MobileAppStatus, MobileAppPlatform
        )

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return {"success": False, "error": "App not found"}

        # Validate required fields
        if not app.app_icon_url:
            return {"success": False, "error": "App icon is required"}

        # Get latest build number
        latest_build = self.db.query(MobileAppBuild).filter(
            MobileAppBuild.app_id == app.id,
            MobileAppBuild.platform == MobileAppPlatform(platform)
        ).order_by(MobileAppBuild.build_number.desc()).first()

        build_number = (latest_build.build_number + 1) if latest_build else 1

        # Create build record
        build = MobileAppBuild(
            app_id=app.id,
            version=version,
            build_number=build_number,
            platform=MobileAppPlatform(platform),
            status="queued",
            release_notes=release_notes,
            queued_at=datetime.utcnow(),
            created_by=created_by
        )
        self.db.add(build)

        # Update app status
        app.status = MobileAppStatus.BUILDING
        app.last_build_at = datetime.utcnow()

        self.db.commit()

        # In production, this would trigger actual build pipeline
        # For now, simulate build completion
        self._simulate_build(build.id)

        return {
            "success": True,
            "build_id": build.id,
            "build_number": build_number,
            "platform": platform,
            "version": version,
            "status": "queued",
            "message": "Build started"
        }

    def _simulate_build(self, build_id: int):
        """Simulate build completion (for demo purposes)"""
        from app.models.enterprise_integrations_models import MobileAppBuild, BrandedMobileApp, MobileAppStatus

        build = self.db.query(MobileAppBuild).filter(MobileAppBuild.id == build_id).first()
        if not build:
            return

        # Simulate build process
        build.status = "completed"
        build.started_at = datetime.utcnow()
        build.completed_at = datetime.utcnow()
        build.build_duration_seconds = 180  # 3 minutes
        build.build_url = f"https://builds.v99pos.com/{build.app_id}/{build.platform.value}/{build.version}/app"
        build.build_size_mb = 45.2

        # Update app
        app = self.db.query(BrandedMobileApp).filter(BrandedMobileApp.id == build.app_id).first()
        if app:
            if build.platform.value == "ios":
                app.current_ios_version = build.version
            else:
                app.current_android_version = build.version
            app.status = MobileAppStatus.REVIEW

        self.db.commit()

    def get_builds(self, venue_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Get build history"""
        from app.models.enterprise_integrations_models import BrandedMobileApp, MobileAppBuild

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return []

        builds = self.db.query(MobileAppBuild).filter(
            MobileAppBuild.app_id == app.id
        ).order_by(MobileAppBuild.created_at.desc()).limit(limit).all()

        return [
            {
                "id": b.id,
                "version": b.version,
                "build_number": b.build_number,
                "platform": b.platform.value,
                "status": b.status,
                "build_url": b.build_url,
                "build_size_mb": b.build_size_mb,
                "release_notes": b.release_notes,
                "is_released": b.is_released,
                "queued_at": b.queued_at.isoformat() if b.queued_at else None,
                "completed_at": b.completed_at.isoformat() if b.completed_at else None,
                "build_duration_seconds": b.build_duration_seconds
            }
            for b in builds
        ]

    def publish_app(self, venue_id: int, build_id: int) -> Dict[str, Any]:
        """Publish an app build"""
        from app.models.enterprise_integrations_models import BrandedMobileApp, MobileAppBuild, MobileAppStatus

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return {"success": False, "error": "App not found"}

        build = self.db.query(MobileAppBuild).filter(
            MobileAppBuild.id == build_id,
            MobileAppBuild.app_id == app.id
        ).first()

        if not build:
            return {"success": False, "error": "Build not found"}

        if build.status != "completed":
            return {"success": False, "error": "Build not completed"}

        # Mark as released
        build.is_released = True
        build.released_at = datetime.utcnow()

        # Update app status
        app.status = MobileAppStatus.PUBLISHED
        app.published_at = datetime.utcnow()

        # Set store URLs (in production, these would be actual store links)
        if build.platform.value == "ios":
            app.ios_app_store_url = f"https://apps.apple.com/app/{app.bundle_id}"
        else:
            app.android_play_store_url = f"https://play.google.com/store/apps/details?id={app.package_name}"

        self.db.commit()

        return {
            "success": True,
            "message": "App published successfully",
            "store_url": app.ios_app_store_url if build.platform.value == "ios" else app.android_play_store_url
        }

    def create_push_campaign(
        self,
        venue_id: int,
        name: str,
        title: str,
        body: str,
        created_by: int,
        target_audience: str = "all",
        scheduled_at: Optional[datetime] = None,
        image_url: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a push notification campaign"""
        from app.models.enterprise_integrations_models import BrandedMobileApp, MobileAppPushCampaign

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return {"success": False, "error": "App not found"}

        if not app.push_enabled:
            return {"success": False, "error": "Push notifications not enabled"}

        campaign = MobileAppPushCampaign(
            app_id=app.id,
            venue_id=venue_id,
            name=name,
            title=title,
            body=body,
            image_url=image_url,
            action_url=action_url,
            target_audience=target_audience,
            send_type="immediate" if not scheduled_at else "scheduled",
            scheduled_at=scheduled_at,
            status="draft" if scheduled_at else "sending",
            created_by=created_by
        )
        self.db.add(campaign)
        self.db.commit()

        # If immediate, trigger send
        if not scheduled_at:
            self._send_push_campaign(campaign.id)

        return {
            "success": True,
            "campaign_id": campaign.id,
            "status": campaign.status,
            "message": "Campaign created"
        }

    def _send_push_campaign(self, campaign_id: int):
        """Send push notification campaign"""
        from app.models.enterprise_integrations_models import MobileAppPushCampaign

        campaign = self.db.query(MobileAppPushCampaign).filter(
            MobileAppPushCampaign.id == campaign_id
        ).first()

        if not campaign:
            return

        # In production, this would integrate with FCM/APNS
        # Simulate sending
        campaign.status = "sent"
        campaign.sent_at = datetime.utcnow()
        campaign.completed_at = datetime.utcnow()
        campaign.total_sent = 1000  # Simulated
        campaign.total_delivered = 950

        self.db.commit()

    def get_push_campaigns(self, venue_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get push notification campaigns"""
        from app.models.enterprise_integrations_models import MobileAppPushCampaign

        campaigns = self.db.query(MobileAppPushCampaign).filter(
            MobileAppPushCampaign.venue_id == venue_id
        ).order_by(MobileAppPushCampaign.created_at.desc()).limit(limit).all()

        return [
            {
                "id": c.id,
                "name": c.name,
                "title": c.title,
                "body": c.body,
                "status": c.status,
                "target_audience": c.target_audience,
                "total_sent": c.total_sent,
                "total_delivered": c.total_delivered,
                "total_opened": c.total_opened,
                "total_clicked": c.total_clicked,
                "open_rate": round(c.total_opened / c.total_delivered * 100, 1) if c.total_delivered else 0,
                "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
                "sent_at": c.sent_at.isoformat() if c.sent_at else None,
                "created_at": c.created_at.isoformat()
            }
            for c in campaigns
        ]

    def get_app_analytics(self, venue_id: int) -> Dict[str, Any]:
        """Get app analytics and statistics"""
        from app.models.enterprise_integrations_models import BrandedMobileApp, MobileAppPushCampaign

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return {"error": "App not found"}

        # Get campaign stats
        campaigns = self.db.query(MobileAppPushCampaign).filter(
            MobileAppPushCampaign.venue_id == venue_id
        ).all()

        total_push_sent = sum(c.total_sent or 0 for c in campaigns)
        total_push_opened = sum(c.total_opened or 0 for c in campaigns)

        return {
            "downloads": {
                "total": app.total_downloads,
                "ios": app.ios_downloads,
                "android": app.android_downloads
            },
            "active_users": app.active_users,
            "push_notifications": {
                "total_campaigns": len(campaigns),
                "total_sent": total_push_sent,
                "total_opened": total_push_opened,
                "average_open_rate": round(total_push_opened / total_push_sent * 100, 1) if total_push_sent else 0
            },
            "versions": {
                "ios": app.current_ios_version,
                "android": app.current_android_version
            },
            "status": app.status.value,
            "published_at": app.published_at.isoformat() if app.published_at else None
        }

    def add_custom_screen(
        self,
        venue_id: int,
        slug: str,
        title: str,
        screen_type: str,
        content: Dict[str, Any],
        show_in_menu: bool = True
    ) -> Dict[str, Any]:
        """Add a custom screen to the app"""
        from app.models.enterprise_integrations_models import BrandedMobileApp, MobileAppScreen

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return {"success": False, "error": "App not found"}

        # Check for duplicate slug
        existing = self.db.query(MobileAppScreen).filter(
            MobileAppScreen.app_id == app.id,
            MobileAppScreen.slug == slug
        ).first()

        if existing:
            return {"success": False, "error": "Screen with this slug already exists"}

        screen = MobileAppScreen(
            app_id=app.id,
            slug=slug,
            title=title,
            screen_type=screen_type,
            content=content,
            show_in_menu=show_in_menu
        )
        self.db.add(screen)
        self.db.commit()

        return {
            "success": True,
            "screen_id": screen.id,
            "message": "Custom screen added"
        }

    def get_custom_screens(self, venue_id: int) -> List[Dict[str, Any]]:
        """Get custom screens for an app"""
        from app.models.enterprise_integrations_models import BrandedMobileApp, MobileAppScreen

        app = self.db.query(BrandedMobileApp).filter(
            BrandedMobileApp.venue_id == venue_id
        ).first()

        if not app:
            return []

        screens = self.db.query(MobileAppScreen).filter(
            MobileAppScreen.app_id == app.id
        ).order_by(MobileAppScreen.menu_order).all()

        return [
            {
                "id": s.id,
                "slug": s.slug,
                "title": s.title,
                "screen_type": s.screen_type,
                "content": s.content,
                "show_in_menu": s.show_in_menu,
                "menu_order": s.menu_order,
                "is_active": s.is_active
            }
            for s in screens
        ]
