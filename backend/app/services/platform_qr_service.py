"""
Platform Features & QR/Self-Service - Sections V and Z
Feature flags, white-label, QR payments, and self-service
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid
import random


class PlatformService:
    """Service for platform features, feature flags, and white-label configuration."""
    
    # ==================== FEATURE FLAGS ====================
    
    @staticmethod
    def create_feature_flag(
        db: Session,
        venue_id: int,
        feature_key: str,
        feature_name: str,
        description: str,
        enabled: bool = False,
        rollout_percentage: int = 0,
        conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a feature flag."""
        from app.models.advanced_features_v9 import FeatureFlag
        
        # Check if flag already exists
        existing = db.query(FeatureFlag).filter(
            FeatureFlag.venue_id == venue_id,
            FeatureFlag.feature_key == feature_key
        ).first()
        
        if existing:
            raise ValueError(f"Feature flag '{feature_key}' already exists")
        
        flag = FeatureFlag(
            venue_id=venue_id,
            feature_key=feature_key,
            feature_name=feature_name,
            description=description,
            enabled=enabled,
            rollout_percentage=rollout_percentage,
            conditions=conditions or {}
        )
        db.add(flag)
        db.commit()
        db.refresh(flag)
        
        return {
            "id": flag.id,
            "feature_key": feature_key,
            "feature_name": feature_name,
            "enabled": enabled,
            "rollout_percentage": rollout_percentage,
            "message": "Feature flag created"
        }
    
    @staticmethod
    def check_feature(
        db: Session,
        venue_id: int,
        feature_key: str,
        user_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check if a feature is enabled for a user/context."""
        from app.models.advanced_features_v9 import FeatureFlag
        
        flag = db.query(FeatureFlag).filter(
            FeatureFlag.venue_id == venue_id,
            FeatureFlag.feature_key == feature_key
        ).first()
        
        if not flag:
            return {"enabled": False, "reason": "Feature flag not found"}
        
        if not flag.enabled:
            return {"enabled": False, "reason": "Feature globally disabled"}
        
        # Check rollout percentage
        if flag.rollout_percentage < 100:
            # Use user_id for consistent rollout
            if user_id:
                # Deterministic hash-based rollout
                hash_value = hash(f"{feature_key}:{user_id}") % 100
                if hash_value >= flag.rollout_percentage:
                    return {"enabled": False, "reason": "Not in rollout group"}
            else:
                # Random for non-user contexts
                if random.randint(0, 99) >= flag.rollout_percentage:
                    return {"enabled": False, "reason": "Not in rollout group"}
        
        # Check conditions
        if flag.conditions and context:
            for key, expected in flag.conditions.items():
                if context.get(key) != expected:
                    return {"enabled": False, "reason": f"Condition not met: {key}"}
        
        return {"enabled": True, "reason": "All conditions met"}
    
    @staticmethod
    def update_feature_flag(
        db: Session,
        flag_id: int,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update a feature flag."""
        from app.models.advanced_features_v9 import FeatureFlag
        
        flag = db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()
        if not flag:
            raise ValueError(f"Feature flag {flag_id} not found")
        
        for key, value in updates.items():
            if hasattr(flag, key):
                setattr(flag, key, value)
        
        flag.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(flag)
        
        return {
            "id": flag.id,
            "feature_key": flag.feature_key,
            "enabled": flag.enabled,
            "rollout_percentage": flag.rollout_percentage,
            "message": "Feature flag updated"
        }
    
    @staticmethod
    def get_feature_flags(
        db: Session,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Get all feature flags for a venue."""
        from app.models.advanced_features_v9 import FeatureFlag
        
        flags = db.query(FeatureFlag).filter(
            FeatureFlag.venue_id == venue_id
        ).all()
        
        return [{
            "id": f.id,
            "feature_key": f.feature_key,
            "feature_name": f.feature_name,
            "description": f.description,
            "enabled": f.enabled,
            "rollout_percentage": f.rollout_percentage,
            "conditions": f.conditions
        } for f in flags]
    
    # ==================== WHITE-LABEL CONFIGURATION ====================
    
    @staticmethod
    def set_white_label_config(
        db: Session,
        venue_id: int,
        brand_name: str,
        logo_url: Optional[str] = None,
        primary_color: str = "#2563eb",
        secondary_color: str = "#1e40af",
        accent_color: str = "#f59e0b",
        font_family: str = "Inter",
        custom_css: Optional[str] = None,
        custom_domain: Optional[str] = None,
        email_from_name: Optional[str] = None,
        email_from_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """Set white-label configuration."""
        from app.models.advanced_features_v9 import WhiteLabelConfig
        
        config = db.query(WhiteLabelConfig).filter(
            WhiteLabelConfig.venue_id == venue_id
        ).first()
        
        if not config:
            config = WhiteLabelConfig(
                venue_id=venue_id,
                brand_name=brand_name,
                logo_url=logo_url,
                primary_color=primary_color,
                secondary_color=secondary_color,
                accent_color=accent_color,
                font_family=font_family,
                custom_css=custom_css,
                custom_domain=custom_domain,
                email_from_name=email_from_name,
                email_from_address=email_from_address
            )
            db.add(config)
        else:
            config.brand_name = brand_name
            config.logo_url = logo_url
            config.primary_color = primary_color
            config.secondary_color = secondary_color
            config.accent_color = accent_color
            config.font_family = font_family
            config.custom_css = custom_css
            config.custom_domain = custom_domain
            config.email_from_name = email_from_name
            config.email_from_address = email_from_address
            config.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(config)
        
        return {
            "id": config.id,
            "brand_name": config.brand_name,
            "colors": {
                "primary": config.primary_color,
                "secondary": config.secondary_color,
                "accent": config.accent_color
            },
            "custom_domain": config.custom_domain,
            "message": "White-label configuration saved"
        }
    
    @staticmethod
    def get_white_label_config(
        db: Session,
        venue_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get white-label configuration."""
        from app.models.advanced_features_v9 import WhiteLabelConfig
        
        config = db.query(WhiteLabelConfig).filter(
            WhiteLabelConfig.venue_id == venue_id
        ).first()
        
        if not config:
            return None
        
        return {
            "id": config.id,
            "brand_name": config.brand_name,
            "logo_url": config.logo_url,
            "colors": {
                "primary": config.primary_color,
                "secondary": config.secondary_color,
                "accent": config.accent_color
            },
            "font_family": config.font_family,
            "custom_css": config.custom_css,
            "custom_domain": config.custom_domain,
            "email": {
                "from_name": config.email_from_name,
                "from_address": config.email_from_address
            }
        }


class QRSelfServiceService:
    """Service for QR payments, scan-to-reorder, and self-service features."""
    
    # ==================== QR PAY-AT-TABLE ====================
    
    @staticmethod
    def create_qr_payment_session(
        db: Session,
        venue_id: int,
        order_id: int,
        table_id: int,
        total_amount: Decimal,
        tip_suggestions: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """Create a QR payment session."""
        from app.models.advanced_features_v9 import QRPaymentSession
        from app.models import Order, OrderItem

        session_id = str(uuid.uuid4())

        # Get order items for snapshot
        order_items = db.query(OrderItem).filter(
            OrderItem.order_id == order_id
        ).all()

        items_json = []
        for item in order_items:
            items_json.append({
                "order_item_id": item.id,
                "menu_item_id": item.menu_item_id,
                "quantity": item.quantity,
                "price": float(item.price) if item.price else 0
            })

        session = QRPaymentSession(
            session_id=session_id,
            venue_id=venue_id,
            order_id=order_id,
            table_id=table_id,
            bill_total=float(total_amount),
            items_json=items_json,
            suggested_tips=tip_suggestions or [15, 18, 20, 25],
            status="pending",
            is_split_payment=False,
            split_type=None,
            number_of_splits=None,
            amount_paid=0.0,
            payments=[],
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # Generate QR URL (use short code for easier scanning)
        short_code = session_id[:8].upper()
        qr_url = f"https://pay.bjsbar.bg/{short_code}"

        return {
            "id": session.id,
            "session_id": session_id,
            "order_id": order_id,
            "table_id": table_id,
            "total_amount": float(total_amount),
            "tip_suggestions": session.suggested_tips,
            "qr_url": qr_url,
            "status": "pending",
            "expires_at": session.expires_at.isoformat()
        }
    
    @staticmethod
    def get_payment_session(
        db: Session,
        session_id_or_code: str
    ) -> Optional[Dict[str, Any]]:
        """Get payment session by code."""
        from app.models.advanced_features_v9 import QRPaymentSession

        # Try to find by session_id or by short code prefix (case-insensitive)
        session = db.query(QRPaymentSession).filter(
            or_(
                QRPaymentSession.session_id == session_id_or_code,
                QRPaymentSession.session_id.ilike(f"{session_id_or_code.lower()}%")
            ),
            QRPaymentSession.status.in_(["pending", "partial"])
        ).first()

        if not session:
            return None

        # Check if expired
        if session.expires_at and session.expires_at < datetime.utcnow():
            session.status = "expired"
            db.commit()
            return None

        remaining = session.bill_total - session.amount_paid

        return {
            "id": session.id,
            "session_id": session.session_id,
            "order_id": session.order_id,
            "table_id": session.table_id,
            "total_amount": float(session.bill_total),
            "paid_amount": float(session.amount_paid),
            "remaining_amount": float(remaining),
            "tip_suggestions": session.suggested_tips,
            "tip_amount": float(session.tip_amount),
            "is_split_payment": session.is_split_payment,
            "split_type": session.split_type,
            "number_of_splits": session.number_of_splits,
            "payments": session.payments,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None
        }
    
    @staticmethod
    def configure_split_payment(
        db: Session,
        session_id: int,
        split_type: str,  # "equal", "by_item", "custom"
        number_of_splits: int
    ) -> Dict[str, Any]:
        """Configure split payment for a session."""
        from app.models.advanced_features_v9 import QRPaymentSession

        session = db.query(QRPaymentSession).filter(
            QRPaymentSession.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        session.is_split_payment = True
        session.split_type = split_type
        session.number_of_splits = number_of_splits

        db.commit()

        split_amount = session.bill_total / number_of_splits if split_type == "equal" else None

        return {
            "session_id": session_id,
            "split_type": split_type,
            "number_of_splits": number_of_splits,
            "amount_per_person": float(split_amount) if split_amount else None,
            "total_amount": float(session.bill_total)
        }
    
    @staticmethod
    def record_payment(
        db: Session,
        session_id: int,
        amount: Decimal,
        tip_amount: Decimal,
        payment_method: str,
        payer_name: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a payment in a QR session."""
        from app.models.advanced_features_v9 import QRPaymentSession

        session = db.query(QRPaymentSession).filter(
            QRPaymentSession.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status not in ["pending", "partial"]:
            raise ValueError(f"Session is not active (status: {session.status})")

        # Check expiration
        if session.expires_at and session.expires_at < datetime.utcnow():
            session.status = "expired"
            db.commit()
            raise ValueError("Session has expired")

        payment = {
            "id": str(uuid.uuid4()),
            "amount": float(amount),
            "tip_amount": float(tip_amount),
            "total": float(amount + tip_amount),
            "payment_method": payment_method,
            "payer_name": payer_name,
            "transaction_id": transaction_id,
            "paid_at": datetime.utcnow().isoformat()
        }

        current_payments = session.payments or []
        current_payments.append(payment)
        session.payments = current_payments

        # Update totals
        session.amount_paid = float(session.amount_paid or 0) + float(amount)
        session.tip_amount = float(session.tip_amount or 0) + float(tip_amount)

        # Check if fully paid
        remaining = session.bill_total - session.amount_paid
        if remaining <= 0:
            session.status = "completed"
            session.completed_at = datetime.utcnow()
        elif session.amount_paid > 0:
            session.status = "partial"

        db.commit()

        return {
            "payment_id": payment["id"],
            "amount": float(amount),
            "tip": float(tip_amount),
            "session_status": session.status,
            "paid_amount": float(session.amount_paid),
            "remaining": float(max(0, remaining))
        }
    
    # ==================== SCAN-TO-REORDER ====================
    
    @staticmethod
    def create_reorder_session(
        db: Session,
        venue_id: int,
        customer_id: int,
        reference_order_id: int,
        table_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Create a scan-to-reorder session."""
        from app.models.advanced_features_v9 import ReorderSession
        from app.models import Order, OrderItem

        session_id = str(uuid.uuid4())

        # Get reference order items to create snapshot
        order_items = db.query(OrderItem).filter(
            OrderItem.order_id == reference_order_id
        ).all()

        reference_items = []
        for item in order_items:
            reference_items.append({
                "order_item_id": item.id,
                "menu_item_id": item.menu_item_id,
                "quantity": item.quantity,
                "price": float(item.price) if item.price else 0,
                "notes": getattr(item, 'notes', None)
            })

        session = ReorderSession(
            session_id=session_id,
            venue_id=venue_id,
            customer_id=customer_id,
            reference_order_id=reference_order_id,
            reference_items=reference_items,
            table_id=table_id,
            status="pending",
            new_order_id=None,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        return {
            "id": session.id,
            "session_id": session_id,
            "reference_order_id": reference_order_id,
            "qr_url": f"https://reorder.bjsbar.bg/{session_id[:8].upper()}",
            "status": "pending",
            "expires_at": session.expires_at.isoformat()
        }
    
    @staticmethod
    def get_reorder_items(
        db: Session,
        session_id_or_code: str
    ) -> Optional[Dict[str, Any]]:
        """Get items from original order for reordering."""
        from app.models.advanced_features_v9 import ReorderSession
        from app.models import Order, OrderItem, MenuItem

        # Try to find by session_id or by short code prefix (case-insensitive)
        session = db.query(ReorderSession).filter(
            or_(
                ReorderSession.session_id == session_id_or_code,
                ReorderSession.session_id.ilike(f"{session_id_or_code.lower()}%")
            ),
            ReorderSession.status.in_(["pending", "modified"])
        ).first()

        if not session:
            return None

        # Check if expired
        if session.expires_at and session.expires_at < datetime.utcnow():
            session.status = "expired"
            db.commit()
            return None

        # Fetch actual order items from reference order
        original_order = db.query(Order).filter(
            Order.id == session.reference_order_id
        ).first()

        items = []
        # Use stored reference_items snapshot for consistency
        if session.reference_items:
            for ref_item in session.reference_items:
                menu_item = db.query(MenuItem).filter(
                    MenuItem.id == ref_item.get("menu_item_id")
                ).first()
                items.append({
                    "menu_item_id": ref_item.get("menu_item_id"),
                    "name": menu_item.name if menu_item else "Item",
                    "quantity": ref_item.get("quantity", 1),
                    "price": ref_item.get("price", 0),
                    "notes": ref_item.get("notes"),
                    "available": menu_item.is_active if menu_item else False
                })

        return {
            "session_id": session.session_id,
            "reference_order_id": session.reference_order_id,
            "table_id": session.table_id,
            "original_order_date": original_order.created_at.isoformat() if original_order else None,
            "items": items,
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
            "message": "Select items to reorder"
        }
    
    @staticmethod
    def confirm_reorder(
        db: Session,
        session_id: int,
        selected_menu_item_ids: List[int],
        modifications: Optional[Dict[int, str]] = None
    ) -> Dict[str, Any]:
        """Confirm reorder with selected items."""
        from app.models.advanced_features_v9 import ReorderSession
        from app.models import Order, OrderItem, MenuItem

        session = db.query(ReorderSession).filter(
            ReorderSession.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        if session.status not in ["pending", "modified"]:
            raise ValueError(f"Session is not active (status: {session.status})")

        # Check expiration
        if session.expires_at and session.expires_at < datetime.utcnow():
            session.status = "expired"
            db.commit()
            raise ValueError("Session has expired")

        # Get selected items from reference_items snapshot
        if not session.reference_items:
            raise ValueError("No items in session")

        selected_items = [
            item for item in session.reference_items
            if item.get("menu_item_id") in selected_menu_item_ids
        ]

        if not selected_items:
            raise ValueError("No valid items selected for reorder")

        # Create new order
        new_order = Order(
            venue_id=session.venue_id,
            customer_id=session.customer_id,
            table_id=session.table_id,
            status="pending",
            order_type="dine_in",
            source="reorder_qr",
            notes=f"Reorder from order #{session.reference_order_id}"
        )
        db.add(new_order)
        db.flush()

        # Copy selected items to new order
        total = 0
        items_created = []
        for ref_item in selected_items:
            menu_item_id = ref_item.get("menu_item_id")
            quantity = ref_item.get("quantity", 1)

            # Get current menu item price
            menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
            current_price = float(menu_item.price) if menu_item and menu_item.price else ref_item.get("price", 0)

            # Apply modifications if any
            item_notes = modifications.get(menu_item_id) if modifications else ref_item.get("notes")

            new_item = OrderItem(
                order_id=new_order.id,
                menu_item_id=menu_item_id,
                quantity=quantity,
                price=current_price,
                notes=item_notes
            )
            db.add(new_item)
            total += current_price * quantity
            items_created.append({
                "menu_item_id": menu_item_id,
                "name": menu_item.name if menu_item else "Item",
                "quantity": quantity,
                "price": current_price
            })

        new_order.total = total

        # Update session
        session.status = "ordered"
        session.new_order_id = new_order.id

        db.commit()

        return {
            "session_id": session_id,
            "new_order_id": new_order.id,
            "items_ordered": len(items_created),
            "items": items_created,
            "total": round(total, 2),
            "status": "order_placed",
            "message": "Your order has been placed!"
        }
    
    # ==================== TABLE QR CODES ====================
    
    @staticmethod
    def generate_table_qr(
        venue_id: int,
        table_number: str,
        qr_type: str = "menu"  # "menu", "order", "payment", "feedback"
    ) -> Dict[str, Any]:
        """Generate QR code data for a table."""
        
        base_urls = {
            "menu": f"https://menu.bjsbar.bg/{venue_id}/{table_number}",
            "order": f"https://order.bjsbar.bg/{venue_id}/{table_number}",
            "payment": f"https://pay.bjsbar.bg/{venue_id}/{table_number}",
            "feedback": f"https://feedback.bjsbar.bg/{venue_id}/{table_number}"
        }
        
        url = base_urls.get(qr_type, base_urls["menu"])
        
        return {
            "venue_id": venue_id,
            "table_number": table_number,
            "qr_type": qr_type,
            "url": url,
            "generated_at": datetime.utcnow().isoformat()
        }
    
    # ==================== SELF-SERVICE KIOSK ====================

    @staticmethod
    def get_kiosk_menu(
        db: Session,
        venue_id: int
    ) -> Dict[str, Any]:
        """Get menu formatted for self-service kiosk."""
        from app.models import MenuItem, MenuCategory

        # Get active categories
        categories = db.query(MenuCategory).filter(
            MenuCategory.venue_id == venue_id,
            MenuCategory.is_active == True
        ).order_by(MenuCategory.sort_order).all()

        category_list = []
        items_by_category = {}

        for cat in categories:
            category_list.append({
                "id": cat.id,
                "name": cat.name,
                "description": getattr(cat, 'description', None),
                "image_url": getattr(cat, 'image_url', None)
            })
            items_by_category[cat.id] = []

        # Get active menu items
        items = db.query(MenuItem).filter(
            MenuItem.venue_id == venue_id,
            MenuItem.is_active == True
        ).order_by(MenuItem.sort_order).all()

        all_items = []
        upsell_suggestions = []

        for item in items:
            item_data = {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "price": float(item.price) if item.price else 0,
                "image_url": getattr(item, 'image_url', None),
                "category_id": item.category_id,
                "allergens": getattr(item, 'allergens', []),
                "dietary_tags": getattr(item, 'dietary_tags', []),
                "is_popular": getattr(item, 'is_popular', False),
                "is_new": getattr(item, 'is_new', False),
                "prep_time_minutes": getattr(item, 'prep_time', None),
                "calories": getattr(item, 'calories', None),
                "modifiers": getattr(item, 'modifiers', [])
            }
            all_items.append(item_data)

            if item.category_id and item.category_id in items_by_category:
                items_by_category[item.category_id].append(item_data)

            # Add popular items to upsell
            if getattr(item, 'is_popular', False) and float(item.price or 0) < 15:
                upsell_suggestions.append({
                    "id": item.id,
                    "name": item.name,
                    "price": float(item.price) if item.price else 0,
                    "reason": "Popular choice"
                })

        # Get special offers/promotions
        special_offers = []
        for item in items:
            if getattr(item, 'discount_price', None) and item.discount_price < item.price:
                special_offers.append({
                    "id": item.id,
                    "name": item.name,
                    "original_price": float(item.price),
                    "offer_price": float(item.discount_price),
                    "discount_percent": round((1 - item.discount_price / item.price) * 100)
                })

        return {
            "venue_id": venue_id,
            "categories": category_list,
            "items": all_items,
            "items_by_category": items_by_category,
            "upsell_suggestions": upsell_suggestions[:5],
            "special_offers": special_offers[:5],
            "allergen_filters": ["gluten", "dairy", "nuts", "shellfish", "eggs", "soy", "fish"],
            "dietary_filters": ["vegetarian", "vegan", "halal", "kosher", "gluten-free"]
        }

    @staticmethod
    def submit_kiosk_order(
        db: Session,
        venue_id: int,
        items: List[Dict[str, Any]],
        payment_method: str,
        guest_name: Optional[str] = None,
        special_instructions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Submit order from self-service kiosk."""
        from app.models import Order, OrderItem, MenuItem
        import random
        import string

        # Generate order number
        order_number = f"K{datetime.utcnow().strftime('%H%M%S')}{random.choice(string.ascii_uppercase)}"

        # Create order
        new_order = Order(
            venue_id=venue_id,
            order_number=order_number,
            status="pending",
            order_type="kiosk",
            source="kiosk",
            notes=special_instructions,
            guest_name=guest_name if hasattr(Order, 'guest_name') else None
        )
        db.add(new_order)
        db.flush()

        # Add items
        total = 0
        items_created = []
        estimated_prep = 0

        for item_data in items:
            menu_item_id = item_data.get("menu_item_id")
            quantity = item_data.get("quantity", 1)
            modifiers = item_data.get("modifiers", [])

            menu_item = db.query(MenuItem).filter(MenuItem.id == menu_item_id).first()
            if not menu_item:
                continue

            item_price = float(menu_item.price) if menu_item.price else 0
            item_total = item_price * quantity

            order_item = OrderItem(
                order_id=new_order.id,
                menu_item_id=menu_item_id,
                quantity=quantity,
                price=item_price,
                notes=", ".join(modifiers) if modifiers else None
            )
            db.add(order_item)

            total += item_total
            estimated_prep = max(estimated_prep, getattr(menu_item, 'prep_time', 10) or 10)
            items_created.append({
                "menu_item_id": menu_item_id,
                "name": menu_item.name,
                "quantity": quantity,
                "price": item_price,
                "total": item_total
            })

        new_order.total = total
        db.commit()

        return {
            "order_id": new_order.id,
            "order_number": order_number,
            "items": items_created,
            "total": round(total, 2),
            "payment_method": payment_method,
            "status": "pending_payment" if payment_method != "cash" else "pending",
            "estimated_wait_minutes": estimated_prep + 5,
            "message": "Please proceed to payment" if payment_method != "cash" else "Your order is being prepared"
        }
