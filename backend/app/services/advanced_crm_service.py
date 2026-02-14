"""
Advanced CRM & Loyalty Service - Section U
Guest preferences, CLV, churn prediction, and advanced loyalty features
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid
import json


class AdvancedCRMService:
    """Service for advanced CRM, guest preferences, and loyalty features."""
    
    # ==================== GUEST PREFERENCES ====================
    
    @staticmethod
    def set_guest_preferences(
        db: Session,
        customer_id: int,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set or update guest preferences.
        Categories: dietary, seating, service, communication, favorites
        """
        from app.models.advanced_features_v9 import GuestPreference

        pref = db.query(GuestPreference).filter(
            GuestPreference.customer_id == customer_id
        ).first()

        if not pref:
            pref = GuestPreference(
                customer_id=customer_id,
                dietary_restrictions=preferences.get("dietary_restrictions", []),
                allergies=preferences.get("allergies", []),
                favorite_items=preferences.get("favorite_items", []),
                disliked_items=preferences.get("disliked_items", []),
                preferred_seating=preferences.get("preferred_seating"),
                preferred_server_ids=preferences.get("preferred_server_ids", []),
                communication_preference=preferences.get("communication_preference", "email"),
                special_occasions=preferences.get("special_occasions", {}),
                notes=preferences.get("notes"),
                vip_status=preferences.get("vip_status", False),
                vip_tier=preferences.get("vip_tier")
            )
            db.add(pref)
        else:
            for key, value in preferences.items():
                if hasattr(pref, key):
                    setattr(pref, key, value)
            pref.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(pref)

        return {
            "customer_id": pref.customer_id,
            "dietary_restrictions": pref.dietary_restrictions,
            "allergies": pref.allergies,
            "favorite_items": pref.favorite_items,
            "disliked_items": pref.disliked_items,
            "preferred_seating": pref.preferred_seating,
            "preferred_server_ids": pref.preferred_server_ids,
            "communication_preference": pref.communication_preference,
            "special_occasions": pref.special_occasions,
            "notes": pref.notes,
            "vip_status": pref.vip_status,
            "vip_tier": pref.vip_tier,
            "updated_at": pref.updated_at.isoformat()
        }
    
    @staticmethod
    def get_guest_preferences(
        db: Session,
        customer_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get all preferences for a guest."""
        from app.models.advanced_features_v9 import GuestPreference

        pref = db.query(GuestPreference).filter(
            GuestPreference.customer_id == customer_id
        ).first()

        if not pref:
            return None

        return {
            "customer_id": pref.customer_id,
            "dietary_restrictions": pref.dietary_restrictions,
            "allergies": pref.allergies,
            "favorite_items": pref.favorite_items,
            "disliked_items": pref.disliked_items,
            "preferred_seating": pref.preferred_seating,
            "preferred_server_ids": pref.preferred_server_ids,
            "communication_preference": pref.communication_preference,
            "special_occasions": pref.special_occasions,
            "notes": pref.notes,
            "vip_status": pref.vip_status,
            "vip_tier": pref.vip_tier
        }
    
    @staticmethod
    def get_service_alerts(
        db: Session,
        customer_id: int
    ) -> Dict[str, Any]:
        """Get service alerts for a guest (allergies, preferences, VIP status)."""
        from app.models.advanced_features_v9 import GuestPreference

        pref = db.query(GuestPreference).filter(
            GuestPreference.customer_id == customer_id
        ).first()
        
        alerts = []
        
        if pref:
            if pref.allergies:
                alerts.append({
                    "type": "allergy",
                    "severity": "critical",
                    "message": f"ALLERGIES: {', '.join(pref.allergies)}"
                })
            
            if pref.dietary_restrictions:
                alerts.append({
                    "type": "dietary",
                    "severity": "warning",
                    "message": f"Dietary: {', '.join(pref.dietary_restrictions)}"
                })
            
            if pref.vip_status:
                alerts.append({
                    "type": "vip",
                    "severity": "info",
                    "message": f"VIP Guest - {pref.vip_tier or 'Standard VIP'}"
                })
            
            if pref.preferred_seating:
                alerts.append({
                    "type": "seating",
                    "severity": "info",
                    "message": f"Preferred seating: {pref.preferred_seating}"
                })
            
            # Check for upcoming special occasions
            if pref.special_occasions:
                today = date.today()
                for occasion, date_str in pref.special_occasions.items():
                    try:
                        occ_date = datetime.strptime(date_str, "%m-%d").replace(year=today.year).date()
                        days_until = (occ_date - today).days
                        if 0 <= days_until <= 7:
                            alerts.append({
                                "type": "occasion",
                                "severity": "info",
                                "message": f"Upcoming {occasion} in {days_until} days!"
                            })
                    except Exception:
                        pass

        return {
            "customer_id": customer_id,
            "alerts": alerts,
            "has_critical": any(a["severity"] == "critical" for a in alerts)
        }
    
    # ==================== CUSTOMER LIFETIME VALUE ====================
    
    @staticmethod
    def calculate_clv(
        db: Session,
        customer_id: int,
        venue_id: int
    ) -> Dict[str, Any]:
        """
        Calculate Customer Lifetime Value for a guest.
        Uses historical data and predictive modeling.
        """
        from app.models.advanced_features_v9 import CustomerLifetimeValue

        # Get or create CLV record
        clv = db.query(CustomerLifetimeValue).filter(
            CustomerLifetimeValue.customer_id == customer_id,
            CustomerLifetimeValue.venue_id == venue_id
        ).first()

        # CLV is calculated incrementally via update_clv_from_order() method
        # which is called after each order to update the running totals

        if not clv:
            clv = CustomerLifetimeValue(
                customer_id=customer_id,
                venue_id=venue_id,
                total_spend=Decimal("0"),
                visit_count=0,
                average_order_value=Decimal("0"),
                days_since_first_visit=0,
                days_since_last_visit=0,
                visit_frequency_days=0,
                predicted_annual_value=Decimal("0"),
                lifetime_value=Decimal("0"),
                churn_risk_score=Decimal("0.5"),
                segment="new"
            )
            db.add(clv)
            db.commit()
            db.refresh(clv)
        
        # Determine segment based on CLV
        segment = "new"
        if clv.lifetime_value >= Decimal("5000"):
            segment = "champion"
        elif clv.lifetime_value >= Decimal("2000"):
            segment = "loyal"
        elif clv.lifetime_value >= Decimal("500"):
            segment = "potential"
        elif clv.visit_count > 0:
            segment = "active"
        
        # Update segment if changed
        if clv.segment != segment:
            clv.segment = segment
            clv.updated_at = datetime.utcnow()
            db.commit()

        return {
            "customer_id": clv.customer_id,
            "venue_id": clv.venue_id,
            "metrics": {
                "total_spend": float(clv.total_spend),
                "visit_count": clv.visit_count,
                "average_order_value": float(clv.average_order_value),
                "days_since_first_visit": clv.days_since_first_visit,
                "days_since_last_visit": clv.days_since_last_visit,
                "visit_frequency_days": clv.visit_frequency_days
            },
            "predictions": {
                "predicted_annual_value": float(clv.predicted_annual_value),
                "lifetime_value": float(clv.lifetime_value),
                "churn_risk_score": float(clv.churn_risk_score),
                "churn_risk_level": "high" if clv.churn_risk_score > 0.7 else "medium" if clv.churn_risk_score > 0.4 else "low"
            },
            "segment": segment,
            "last_calculated": clv.updated_at.isoformat() if clv.updated_at else None
        }
    
    @staticmethod
    def update_clv_from_order(
        db: Session,
        customer_id: int,
        venue_id: int,
        order_total: Decimal,
        order_date: datetime
    ) -> Dict[str, Any]:
        """Update CLV after a new order."""
        from app.models.advanced_features_v9 import CustomerLifetimeValue

        clv = db.query(CustomerLifetimeValue).filter(
            CustomerLifetimeValue.customer_id == customer_id,
            CustomerLifetimeValue.venue_id == venue_id
        ).first()

        now = datetime.utcnow()

        if not clv:
            clv = CustomerLifetimeValue(
                customer_id=customer_id,
                venue_id=venue_id,
                total_spend=order_total,
                visit_count=1,
                average_order_value=order_total,
                first_visit_date=order_date,
                last_visit_date=order_date,
                days_since_first_visit=0,
                days_since_last_visit=0,
                visit_frequency_days=0,
                predicted_annual_value=order_total * 12,  # Simple projection
                lifetime_value=order_total,
                churn_risk_score=Decimal("0.5"),
                segment="new"
            )
            db.add(clv)
        else:
            # Update metrics
            clv.total_spend += order_total
            clv.visit_count += 1
            clv.average_order_value = clv.total_spend / clv.visit_count
            
            if clv.last_visit_date:
                days_between = (order_date - clv.last_visit_date).days
                if clv.visit_frequency_days > 0:
                    # Weighted average of visit frequency
                    clv.visit_frequency_days = int(
                        (clv.visit_frequency_days * 0.7) + (days_between * 0.3)
                    )
                else:
                    clv.visit_frequency_days = days_between
            
            clv.last_visit_date = order_date
            clv.days_since_last_visit = 0
            
            if clv.first_visit_date:
                clv.days_since_first_visit = (now - clv.first_visit_date).days
            
            # Recalculate predicted values
            if clv.visit_frequency_days > 0:
                visits_per_year = 365 / clv.visit_frequency_days
                clv.predicted_annual_value = clv.average_order_value * Decimal(str(visits_per_year))
            
            # Simple CLV: 3-year projection
            clv.lifetime_value = clv.predicted_annual_value * 3
            
            # Update churn risk (lower because they just visited)
            clv.churn_risk_score = Decimal("0.1")
            
            clv.updated_at = now
        
        db.commit()
        db.refresh(clv)

        return AdvancedCRMService.calculate_clv(db, customer_id, venue_id)
    
    @staticmethod
    def get_at_risk_customers(
        db: Session,
        venue_id: int,
        risk_threshold: float = 0.6,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get customers at risk of churning."""
        from app.models.advanced_features_v9 import CustomerLifetimeValue
        
        at_risk = db.query(CustomerLifetimeValue).filter(
            CustomerLifetimeValue.venue_id == venue_id,
            CustomerLifetimeValue.churn_risk_score >= Decimal(str(risk_threshold))
        ).order_by(CustomerLifetimeValue.lifetime_value.desc()).limit(limit).all()
        
        return [{
            "customer_id": c.customer_id,
            "lifetime_value": float(c.lifetime_value),
            "churn_risk_score": float(c.churn_risk_score),
            "days_since_last_visit": c.days_since_last_visit,
            "visit_count": c.visit_count,
            "segment": c.segment,
            "recommended_action": AdvancedCRMService._get_retention_action(c)
        } for c in at_risk]
    
    @staticmethod
    def _get_retention_action(clv) -> str:
        """Get recommended retention action based on customer profile."""
        if clv.segment == "champion" and clv.churn_risk_score > 0.7:
            return "Personal outreach from manager - high-value customer at risk"
        elif clv.segment in ["champion", "loyal"]:
            return "Send exclusive offer or invite to special event"
        elif clv.days_since_last_visit > 60:
            return "Send 'We miss you' campaign with incentive"
        elif clv.churn_risk_score > 0.8:
            return "Urgent: aggressive win-back offer needed"
        else:
            return "Add to standard re-engagement campaign"
    
    @staticmethod
    def get_customer_segments(
        db: Session,
        venue_id: int
    ) -> Dict[str, Any]:
        """Get customer segmentation summary."""
        from app.models.advanced_features_v9 import CustomerLifetimeValue
        
        segments = db.query(
            CustomerLifetimeValue.segment,
            func.count(CustomerLifetimeValue.id).label("count"),
            func.sum(CustomerLifetimeValue.lifetime_value).label("total_clv"),
            func.avg(CustomerLifetimeValue.average_order_value).label("avg_order")
        ).filter(
            CustomerLifetimeValue.venue_id == venue_id
        ).group_by(CustomerLifetimeValue.segment).all()
        
        result = {}
        total_customers = 0
        total_clv = Decimal("0")
        
        for seg in segments:
            result[seg.segment] = {
                "count": seg.count,
                "total_clv": float(seg.total_clv or 0),
                "avg_order_value": float(seg.avg_order or 0)
            }
            total_customers += seg.count
            total_clv += seg.total_clv or Decimal("0")
        
        return {
            "venue_id": venue_id,
            "total_customers": total_customers,
            "total_clv": float(total_clv),
            "segments": result,
            "segment_definitions": {
                "champion": "CLV >= 5000 BGN",
                "loyal": "CLV >= 2000 BGN",
                "potential": "CLV >= 500 BGN",
                "active": "Has made purchases",
                "new": "Recent first-time customer"
            }
        }
    
    # ==================== VIP MANAGEMENT ====================
    
    @staticmethod
    def set_vip_status(
        db: Session,
        customer_id: int,
        vip_status: bool,
        vip_tier: Optional[str] = None,
        reason: Optional[str] = None,
        set_by: Optional[int] = None
    ) -> Dict[str, Any]:
        """Set or update VIP status for a guest."""
        from app.models.advanced_features_v9 import GuestPreference

        pref = db.query(GuestPreference).filter(
            GuestPreference.customer_id == customer_id
        ).first()

        if not pref:
            pref = GuestPreference(
                customer_id=customer_id,
                vip_status=vip_status,
                vip_tier=vip_tier,
                notes=f"VIP set by staff {set_by}: {reason}" if reason else None
            )
            db.add(pref)
        else:
            pref.vip_status = vip_status
            pref.vip_tier = vip_tier
            if reason:
                existing_notes = pref.notes or ""
                pref.notes = f"{existing_notes}\n[{datetime.utcnow().isoformat()}] VIP status changed: {reason}"
            pref.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(pref)

        return {
            "customer_id": customer_id,
            "vip_status": pref.vip_status,
            "vip_tier": pref.vip_tier,
            "message": "VIP status updated successfully"
        }
    
    @staticmethod
    def get_vip_guests(
        db: Session,
        venue_id: Optional[int] = None,
        tier: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all VIP guests, optionally filtered by tier."""
        from app.models.advanced_features_v9 import GuestPreference, CustomerLifetimeValue
        
        query = db.query(GuestPreference).filter(GuestPreference.vip_status == True)
        
        if tier:
            query = query.filter(GuestPreference.vip_tier == tier)
        
        vips = query.all()
        
        result = []
        for vip in vips:
            # Get CLV if available
            clv_data = None
            if venue_id:
                clv = db.query(CustomerLifetimeValue).filter(
                    CustomerLifetimeValue.customer_id == vip.customer_id,
                    CustomerLifetimeValue.venue_id == venue_id
                ).first()
                if clv:
                    clv_data = {
                        "lifetime_value": float(clv.lifetime_value),
                        "visit_count": clv.visit_count,
                        "segment": clv.segment
                    }

            result.append({
                "customer_id": vip.customer_id,
                "vip_tier": vip.vip_tier,
                "preferred_seating": vip.preferred_seating,
                "dietary_restrictions": vip.dietary_restrictions,
                "allergies": vip.allergies,
                "special_occasions": vip.special_occasions,
                "clv_data": clv_data
            })
        
        return result
    
    # ==================== PERSONALIZATION ====================
    
    @staticmethod
    def get_personalized_recommendations(
        db: Session,
        customer_id: int,
        venue_id: int,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Get personalized menu recommendations for a guest."""
        from app.models.advanced_features_v9 import GuestPreference

        pref = db.query(GuestPreference).filter(
            GuestPreference.customer_id == customer_id
        ).first()

        recommendations = {
            "customer_id": customer_id,
            "favorites": [],
            "try_something_new": [],
            "avoid": [],
            "personalization_level": "low"
        }
        
        if pref:
            recommendations["favorites"] = pref.favorite_items or []
            recommendations["avoid"] = list(set(
                (pref.allergies or []) + 
                (pref.disliked_items or []) + 
                (pref.dietary_restrictions or [])
            ))
            recommendations["personalization_level"] = "high" if pref.favorite_items else "medium"
        
        return recommendations
    
    @staticmethod
    def record_feedback(
        db: Session,
        customer_id: int,
        venue_id: int,
        order_id: int,
        rating: int,
        feedback_type: str,  # "food", "service", "ambiance", "overall"
        comments: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record guest feedback for continuous improvement."""
        from app.models.advanced_features_v9 import ImmutableAuditLog, CustomerLifetimeValue
        from app.models import Order
        import hashlib
        import json

        # Validate rating
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        # Verify order exists
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # Create feedback data
        feedback_data = {
            "customer_id": customer_id,
            "order_id": order_id,
            "rating": rating,
            "feedback_type": feedback_type,
            "comments": comments,
            "recorded_at": datetime.utcnow().isoformat()
        }

        # Store in audit log for immutable record
        previous = db.query(ImmutableAuditLog).filter(
            ImmutableAuditLog.venue_id == venue_id
        ).order_by(ImmutableAuditLog.id.desc()).first()

        previous_checksum = previous.checksum if previous else "GENESIS"

        log_data = {
            "venue_id": venue_id,
            "user_id": customer_id,
            "action_type": "guest_feedback",
            "entity_type": "order",
            "entity_id": order_id,
            "action_details": feedback_data,
            "timestamp": datetime.utcnow().isoformat(),
            "previous_checksum": previous_checksum
        }

        checksum = hashlib.sha256(json.dumps(log_data, sort_keys=True).encode()).hexdigest()

        feedback_log = ImmutableAuditLog(
            venue_id=venue_id,
            user_id=customer_id,
            action_type="guest_feedback",
            entity_type="order",
            entity_id=order_id,
            action_details=feedback_data,
            previous_checksum=previous_checksum,
            checksum=checksum
        )
        db.add(feedback_log)

        # Update customer CLV data if applicable
        if customer_id:
            clv = db.query(CustomerLifetimeValue).filter(
                CustomerLifetimeValue.customer_id == customer_id,
                CustomerLifetimeValue.venue_id == venue_id
            ).first()
            if clv:
                # Higher ratings indicate satisfaction
                if rating >= 4:
                    clv.churn_risk_score = max(Decimal("0"), clv.churn_risk_score - Decimal("0.05"))
                elif rating <= 2:
                    clv.churn_risk_score = min(Decimal("1"), clv.churn_risk_score + Decimal("0.1"))

        db.commit()

        return {
            "feedback_id": feedback_log.id,
            "customer_id": customer_id,
            "order_id": order_id,
            "rating": rating,
            "feedback_type": feedback_type,
            "comments": comments,
            "recorded_at": datetime.utcnow().isoformat(),
            "message": "Thank you for your feedback!"
        }


# Class aliases for backwards compatibility with endpoint imports
GuestPreferencesService = AdvancedCRMService
CustomerLifetimeValueService = AdvancedCRMService
CustomerSegmentationService = AdvancedCRMService
VIPManagementService = AdvancedCRMService
PersonalizationService = AdvancedCRMService

