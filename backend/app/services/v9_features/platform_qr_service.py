"""
Platform & QR Self-Service Stub
================================
Service stub for V9 platform features (feature flags, white-label) and
QR self-service features (pay-at-table, scan-to-reorder, kiosk).
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any


class PlatformService:
    """Service for platform features including feature flags and white-label config.

    Note: Methods are called as class methods in the route files.
    """

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def create_feature_flag(db, venue_id: int, feature_key: str, feature_name: str,
                            description: str, enabled: bool = False,
                            rollout_percentage: int = 0,
                            conditions: dict = None) -> dict:
        """Create a feature flag."""
        return {
            "id": 1,
            "venue_id": venue_id,
            "feature_key": feature_key,
            "feature_name": feature_name,
            "enabled": enabled,
            "rollout_percentage": rollout_percentage,
        }

    @staticmethod
    def check_feature(db, venue_id: int, feature_key: str,
                      user_id: int = None, context: dict = None) -> dict:
        """Check if a feature is enabled for a user/context."""
        return {"enabled": False, "reason": "Feature not found"}

    @staticmethod
    def update_feature_flag(db, flag_id: int, updates: dict) -> dict:
        """Update a feature flag."""
        return {"flag_id": flag_id, "updated": True}

    @staticmethod
    def get_feature_flags(db, venue_id: int) -> list:
        """Get all feature flags for a venue."""
        return []

    @staticmethod
    def set_white_label_config(db, venue_id: int, brand_name: str,
                               logo_url: str = None, primary_color: str = "#2563eb",
                               secondary_color: str = "#1e40af",
                               accent_color: str = "#f59e0b",
                               font_family: str = "Inter",
                               custom_css: str = None,
                               custom_domain: str = None,
                               email_from_name: str = None,
                               email_from_address: str = None) -> dict:
        """Set white-label configuration."""
        return {
            "id": 1,
            "venue_id": venue_id,
            "brand_name": brand_name,
            "primary_color": primary_color,
        }

    @staticmethod
    def get_white_label_config(db, venue_id: int) -> Optional[dict]:
        """Get white-label configuration."""
        return None


class QRSelfServiceService:
    """Service for QR-based self-service features.

    Note: Methods are called as class methods in the route files.
    """

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def create_qr_payment_session(db, venue_id: int, order_id: int,
                                   table_number: str, total_amount: Decimal,
                                   tip_suggestions: list = None) -> dict:
        """Create a QR payment session."""
        import uuid
        return {
            "id": 1,
            "venue_id": venue_id,
            "order_id": order_id,
            "table_number": table_number,
            "total_amount": float(total_amount),
            "session_code": uuid.uuid4().hex[:8].upper(),
            "status": "active",
        }

    @staticmethod
    def get_payment_session(db, session_code: str) -> Optional[dict]:
        """Get payment session by code."""
        return None

    @staticmethod
    def configure_split_payment(db, session_id: int, split_type: str,
                                split_count: int) -> dict:
        """Configure split payment for a session."""
        return {
            "session_id": session_id,
            "split_type": split_type,
            "split_count": split_count,
        }

    @staticmethod
    def record_payment(db, session_id: int, amount: Decimal, tip_amount: Decimal,
                       payment_method: str, payer_name: str = None,
                       transaction_id: str = None) -> dict:
        """Record a payment in a QR session."""
        return {
            "id": 1,
            "session_id": session_id,
            "amount": float(amount),
            "tip_amount": float(tip_amount),
            "payment_method": payment_method,
            "status": "completed",
        }

    @staticmethod
    def create_reorder_session(db, venue_id: int, guest_id: int,
                               original_order_id: int,
                               table_number: str) -> dict:
        """Create a scan-to-reorder session."""
        import uuid
        return {
            "id": 1,
            "venue_id": venue_id,
            "guest_id": guest_id,
            "original_order_id": original_order_id,
            "session_code": uuid.uuid4().hex[:8].upper(),
            "status": "active",
        }

    @staticmethod
    def get_reorder_items(db, session_code: str) -> Optional[dict]:
        """Get items from original order for reordering."""
        return None

    @staticmethod
    def confirm_reorder(db, session_id: int, selected_item_ids: list,
                        modifications: dict = None) -> dict:
        """Confirm reorder with selected items."""
        return {
            "session_id": session_id,
            "new_order_id": None,
            "items_count": len(selected_item_ids),
            "status": "confirmed",
        }

    @staticmethod
    def generate_table_qr(venue_id: int, table_number: str,
                          qr_type: str = "menu") -> dict:
        """Generate QR code data for a table."""
        return {
            "venue_id": venue_id,
            "table_number": table_number,
            "qr_type": qr_type,
            "qr_url": f"/qr/{venue_id}/{table_number}/{qr_type}",
            "qr_data": "",
        }

    @staticmethod
    def get_kiosk_menu(db, venue_id: int) -> dict:
        """Get menu formatted for self-service kiosk."""
        return {
            "venue_id": venue_id,
            "categories": [],
            "items": [],
        }

    @staticmethod
    def submit_kiosk_order(db, venue_id: int, items: list, payment_method: str,
                           guest_name: str = None,
                           special_instructions: str = None) -> dict:
        """Submit order from self-service kiosk."""
        return {
            "order_id": None,
            "venue_id": venue_id,
            "items_count": len(items),
            "status": "submitted",
        }
