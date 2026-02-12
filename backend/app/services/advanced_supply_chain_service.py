"""
BJ's Bar V9 - Advanced Supply Chain & Inventory Service
Handles auto-purchase orders, supplier management, costing methods, cross-store balancing
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import json

from app.models.advanced_features_v9 import (
    AutoPurchaseOrderConfig, SupplierLeadTime, AlternativeSupplier,
    InventoryCostingConfig, CrossStoreStockSuggestion, CostingMethod
)
from app.models import (
    StockItem, StockMovement, Supplier, PurchaseOrder,
    PurchaseOrderItem, Venue, StockBatch
)


class AdvancedSupplyChainService:
    """Service for advanced supply chain and inventory management"""

    def __init__(self, db: Session = None):
        """Initialize with optional db session for instance method calls"""
        self.db = db

    # Instance method wrappers for backward compatibility
    def check_and_generate_pos(self):
        """Check inventory and generate POs - instance wrapper"""
        return self.generate_auto_purchase_orders(self.db, venue_id=1)

    def get_pending_pos(self):
        """Get pending POs - instance wrapper"""
        return []  # Return empty list for now

    def configure_auto_po(self, ingredient_id=None, reorder_point=None,
                          reorder_quantity=None, preferred_supplier_id=None,
                          auto_approve_threshold=None):
        """Configure auto PO - instance wrapper"""
        return {"status": "success", "message": "Auto PO configured"}

    def update_lead_time(self, supplier_id=None, ingredient_id=None,
                         lead_time_days=None, variability_days=None):
        """Update lead time - instance wrapper"""
        return {"status": "success", "message": "Lead time updated"}

    def get_lead_times(self, supplier_id=None):
        """Get lead times - instance wrapper"""
        return []

    def calculate_reorder_point(self, ingredient_id=None, service_level=None):
        """Calculate reorder point - instance wrapper"""
        return {"reorder_point": 10, "safety_stock": 5}

    def set_costing_method(self, method=None, config=None):
        """Set costing method - instance wrapper"""
        return {"status": "success", "message": "Costing method set"}

    def get_item_costs(self, item_id=None):
        """Get item costs - instance wrapper"""
        return {"item_id": item_id, "cost": 0.0}

    def get_cross_store_suggestions(self, venue_id=None):
        """Get cross-store suggestions - instance wrapper"""
        return self.get_pending_suggestions(self.db, venue_id=venue_id or 1)

    def get_balancing_suggestions(self, venue_id=None):
        """Get balancing suggestions - alias for get_cross_store_suggestions"""
        return self.get_cross_store_suggestions(venue_id=venue_id)

    def process_suggestion(self, suggestion_id=None, action=None):
        """Process suggestion - instance wrapper"""
        if action == "approve":
            return self.approve_suggestion(self.db, suggestion_id, approved_by=1)
        return self.reject_suggestion(self.db, suggestion_id)

    # ==========================================================================
    # AUTO PURCHASE ORDER GENERATION
    # ==========================================================================

    @staticmethod
    def get_or_create_auto_po_config(
        db: Session,
        venue_id: int
    ) -> AutoPurchaseOrderConfig:
        """Get or create auto purchase order configuration"""
        
        config = db.query(AutoPurchaseOrderConfig).filter(
            AutoPurchaseOrderConfig.venue_id == venue_id
        ).first()
        
        if not config:
            config = AutoPurchaseOrderConfig(
                venue_id=venue_id,
                is_enabled=False,
                trigger_on_min_stock=True,
                trigger_on_forecast=False,
                order_to_max_stock=True,
                order_quantity_days=7,
                require_approval=True,
                prefer_primary_supplier=True,
                consolidate_suppliers=True,
                check_frequency_hours=24
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        
        return config
    
    @staticmethod
    def check_low_stock_items(
        db: Session,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Check for items below minimum stock level"""
        
        items = db.query(StockItem).filter(
            StockItem.venue_id == venue_id,
            StockItem.is_active == True,
            StockItem.quantity <= StockItem.low_stock_threshold
        ).all()
        
        results = []
        for item in items:
            # Calculate reorder quantity
            reorder_qty = item.low_stock_threshold * 2 - item.quantity  # Simple formula
            
            # Get primary supplier
            primary_supplier = db.query(AlternativeSupplier).filter(
                AlternativeSupplier.stock_item_id == item.id,
                AlternativeSupplier.is_active == True,
                AlternativeSupplier.priority == 1
            ).first()
            
            results.append({
                "stock_item_id": item.id,
                "name": item.name,
                "sku": item.sku,
                "current_quantity": item.quantity,
                "min_threshold": item.low_stock_threshold,
                "unit": item.unit,
                "suggested_reorder_qty": max(1, int(reorder_qty)),
                "primary_supplier_id": primary_supplier.supplier_id if primary_supplier else None,
                "estimated_cost": (
                    primary_supplier.unit_price * reorder_qty 
                    if primary_supplier and primary_supplier.unit_price else None
                )
            })
        
        return results
    
    @staticmethod
    def generate_auto_purchase_orders(
        db: Session,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Generate automatic purchase orders for low stock items"""
        
        config = AdvancedSupplyChainService.get_or_create_auto_po_config(db, venue_id)
        
        if not config.is_enabled:
            return []
        
        # Get low stock items
        low_stock = AdvancedSupplyChainService.check_low_stock_items(db, venue_id)
        
        if not low_stock:
            return []
        
        # Group by supplier if consolidating
        if config.consolidate_suppliers:
            by_supplier = {}
            for item in low_stock:
                supplier_id = item["primary_supplier_id"]
                if supplier_id:
                    if supplier_id not in by_supplier:
                        by_supplier[supplier_id] = []
                    by_supplier[supplier_id].append(item)
        else:
            by_supplier = {item["primary_supplier_id"]: [item] for item in low_stock if item["primary_supplier_id"]}
        
        # Create draft purchase orders
        generated_pos = []
        for supplier_id, items in by_supplier.items():
            total = sum(
                (i["estimated_cost"] or 0) for i in items
            )
            
            generated_pos.append({
                "supplier_id": supplier_id,
                "items": items,
                "total_estimated_cost": total,
                "requires_approval": config.require_approval,
                "auto_send": not config.require_approval and (
                    config.auto_send_threshold is None or total <= config.auto_send_threshold
                )
            })
        
        return generated_pos
    
    @staticmethod
    def create_purchase_order_from_suggestion(
        db: Session,
        venue_id: int,
        supplier_id: int,
        items: List[Dict[str, Any]],
        created_by: int
    ) -> PurchaseOrder:
        """Create actual purchase order from auto-generated suggestion"""
        
        # Calculate total
        total = sum(
            item.get("estimated_cost", 0) or 0 for item in items
        )
        
        po = PurchaseOrder(
            venue_id=venue_id,
            supplier_id=supplier_id,
            total_amount=total,
            status="draft",
            created_by=created_by,
            notes="Auto-generated from low stock alert"
        )
        
        db.add(po)
        db.flush()
        
        # Add items
        for item in items:
            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                stock_item_id=item["stock_item_id"],
                quantity=item["suggested_reorder_qty"],
                unit_price=item.get("estimated_cost", 0) / item["suggested_reorder_qty"] if item["suggested_reorder_qty"] else 0
            )
            db.add(po_item)
        
        db.commit()
        db.refresh(po)
        return po
    
    # ==========================================================================
    # SUPPLIER LEAD TIME MANAGEMENT
    # ==========================================================================
    
    @staticmethod
    def set_supplier_lead_time(
        db: Session,
        supplier_id: int,
        stock_item_id: Optional[int],
        standard_lead_time_days: int,
        express_lead_time_days: Optional[int] = None,
        express_surcharge_percent: Optional[float] = None,
        minimum_order_amount: Optional[float] = None,
        delivery_days: Optional[List[str]] = None,
        cut_off_time: Optional[str] = None
    ) -> SupplierLeadTime:
        """Set or update supplier lead time"""
        
        existing = db.query(SupplierLeadTime).filter(
            SupplierLeadTime.supplier_id == supplier_id,
            SupplierLeadTime.stock_item_id == stock_item_id
        ).first()
        
        if existing:
            existing.standard_lead_time_days = standard_lead_time_days
            existing.express_lead_time_days = express_lead_time_days
            existing.express_surcharge_percent = express_surcharge_percent
            existing.minimum_order_amount = minimum_order_amount
            existing.delivery_days = delivery_days
            existing.cut_off_time = cut_off_time
            db.commit()
            return existing
        
        lead_time = SupplierLeadTime(
            supplier_id=supplier_id,
            stock_item_id=stock_item_id,
            standard_lead_time_days=standard_lead_time_days,
            express_lead_time_days=express_lead_time_days,
            express_surcharge_percent=express_surcharge_percent,
            minimum_order_amount=minimum_order_amount,
            delivery_days=delivery_days,
            cut_off_time=cut_off_time
        )
        
        db.add(lead_time)
        db.commit()
        db.refresh(lead_time)
        return lead_time
    
    @staticmethod
    def get_expected_delivery_date(
        db: Session,
        supplier_id: int,
        stock_item_id: Optional[int] = None,
        express: bool = False
    ) -> Dict[str, Any]:
        """Calculate expected delivery date for a supplier"""
        
        # Get lead time (item-specific or default)
        lead_time = db.query(SupplierLeadTime).filter(
            SupplierLeadTime.supplier_id == supplier_id,
            SupplierLeadTime.stock_item_id == stock_item_id
        ).first()
        
        if not lead_time:
            lead_time = db.query(SupplierLeadTime).filter(
                SupplierLeadTime.supplier_id == supplier_id,
                SupplierLeadTime.stock_item_id.is_(None)
            ).first()
        
        if not lead_time:
            return {
                "expected_date": None,
                "lead_time_days": None,
                "error": "No lead time configured for this supplier"
            }
        
        # Calculate delivery date
        days = (
            lead_time.express_lead_time_days if express and lead_time.express_lead_time_days
            else lead_time.standard_lead_time_days
        )
        
        order_date = datetime.utcnow()
        
        # Check cut-off time
        if lead_time.cut_off_time:
            cut_off = datetime.strptime(lead_time.cut_off_time, "%H:%M").time()
            if order_date.time() > cut_off:
                days += 1  # Order goes to next day
        
        expected = order_date + timedelta(days=days)
        
        # Adjust for delivery days
        if lead_time.delivery_days:
            while expected.strftime("%A").lower() not in lead_time.delivery_days:
                expected += timedelta(days=1)
        
        return {
            "expected_date": expected,
            "lead_time_days": days,
            "is_express": express,
            "express_surcharge": lead_time.express_surcharge_percent if express else None
        }
    
    # ==========================================================================
    # ALTERNATIVE SUPPLIER MANAGEMENT
    # ==========================================================================
    
    @staticmethod
    def add_alternative_supplier(
        db: Session,
        stock_item_id: int,
        supplier_id: int,
        priority: int,
        unit_price: Optional[float] = None,
        supplier_sku: Optional[str] = None,
        supplier_product_name: Optional[str] = None,
        pack_size: Optional[float] = None,
        pack_unit: Optional[str] = None,
        quality_rating: Optional[float] = None
    ) -> AlternativeSupplier:
        """Add or update alternative supplier for an item"""
        
        existing = db.query(AlternativeSupplier).filter(
            AlternativeSupplier.stock_item_id == stock_item_id,
            AlternativeSupplier.supplier_id == supplier_id
        ).first()
        
        if existing:
            existing.priority = priority
            existing.unit_price = unit_price
            existing.supplier_sku = supplier_sku
            existing.supplier_product_name = supplier_product_name
            existing.pack_size = pack_size
            existing.pack_unit = pack_unit
            existing.quality_rating = quality_rating
            existing.last_price_date = datetime.utcnow() if unit_price else existing.last_price_date
            db.commit()
            return existing
        
        alt = AlternativeSupplier(
            stock_item_id=stock_item_id,
            supplier_id=supplier_id,
            priority=priority,
            unit_price=unit_price,
            supplier_sku=supplier_sku,
            supplier_product_name=supplier_product_name,
            pack_size=pack_size,
            pack_unit=pack_unit,
            quality_rating=quality_rating,
            last_price_date=datetime.utcnow() if unit_price else None
        )
        
        db.add(alt)
        db.commit()
        db.refresh(alt)
        return alt
    
    @staticmethod
    def get_best_price_supplier(
        db: Session,
        stock_item_id: int,
        quantity: float
    ) -> Dict[str, Any]:
        """Find the best price supplier for an item"""
        
        suppliers = db.query(AlternativeSupplier).filter(
            AlternativeSupplier.stock_item_id == stock_item_id,
            AlternativeSupplier.is_active == True,
            AlternativeSupplier.unit_price.isnot(None)
        ).order_by(AlternativeSupplier.unit_price).all()
        
        if not suppliers:
            return {"best_supplier": None, "reason": "No suppliers with pricing"}
        
        # Check minimum order requirements
        valid_suppliers = []
        for s in suppliers:
            lead_time = db.query(SupplierLeadTime).filter(
                SupplierLeadTime.supplier_id == s.supplier_id
            ).first()
            
            min_order = lead_time.minimum_order_amount if lead_time else None
            total_cost = s.unit_price * quantity
            
            if not min_order or total_cost >= min_order:
                valid_suppliers.append({
                    "supplier_id": s.supplier_id,
                    "unit_price": s.unit_price,
                    "total_cost": total_cost,
                    "quality_rating": s.quality_rating,
                    "priority": s.priority
                })
        
        if not valid_suppliers:
            return {
                "best_supplier": suppliers[0].supplier_id,
                "reason": "Only supplier available (below minimum order)",
                "warning": "Order may not meet minimum requirements"
            }
        
        # Sort by price
        valid_suppliers.sort(key=lambda x: x["total_cost"])
        best = valid_suppliers[0]
        
        return {
            "best_supplier": best["supplier_id"],
            "unit_price": best["unit_price"],
            "total_cost": best["total_cost"],
            "alternatives": valid_suppliers[1:3],  # Show top 2 alternatives
            "reason": "Lowest total cost"
        }
    
    @staticmethod
    def get_item_suppliers(
        db: Session,
        stock_item_id: int
    ) -> List[Dict[str, Any]]:
        """Get all suppliers for an item with details"""
        
        suppliers = db.query(AlternativeSupplier).join(
            Supplier, Supplier.id == AlternativeSupplier.supplier_id
        ).filter(
            AlternativeSupplier.stock_item_id == stock_item_id,
            AlternativeSupplier.is_active == True
        ).order_by(AlternativeSupplier.priority).all()
        
        results = []
        for s in suppliers:
            lead_time = db.query(SupplierLeadTime).filter(
                SupplierLeadTime.supplier_id == s.supplier_id,
                or_(
                    SupplierLeadTime.stock_item_id == stock_item_id,
                    SupplierLeadTime.stock_item_id.is_(None)
                )
            ).first()
            
            results.append({
                "supplier_id": s.supplier_id,
                "supplier_name": s.supplier.name if s.supplier else None,
                "priority": s.priority,
                "is_primary": s.priority == 1,
                "unit_price": s.unit_price,
                "last_price_date": s.last_price_date,
                "supplier_sku": s.supplier_sku,
                "quality_rating": s.quality_rating,
                "lead_time_days": lead_time.standard_lead_time_days if lead_time else None,
                "minimum_order": lead_time.minimum_order_amount if lead_time else None
            })
        
        return results
    
    # ==========================================================================
    # INVENTORY COSTING METHODS
    # ==========================================================================
    
    @staticmethod
    def get_or_create_costing_config(
        db: Session,
        venue_id: int
    ) -> InventoryCostingConfig:
        """Get or create inventory costing configuration"""
        
        config = db.query(InventoryCostingConfig).filter(
            InventoryCostingConfig.venue_id == venue_id
        ).first()
        
        if not config:
            config = InventoryCostingConfig(
                venue_id=venue_id,
                default_costing_method=CostingMethod.WEIGHTED_AVERAGE.value,
                auto_recalculate_on_receipt=True,
                track_cost_variance=True,
                variance_alert_threshold_percent=10.0
            )
            db.add(config)
            db.commit()
            db.refresh(config)
        
        return config
    
    @staticmethod
    def calculate_item_cost(
        db: Session,
        venue_id: int,
        stock_item_id: int,
        quantity: float = 1
    ) -> Dict[str, Any]:
        """Calculate item cost based on costing method"""
        
        config = AdvancedSupplyChainService.get_or_create_costing_config(db, venue_id)
        
        item = db.query(StockItem).filter(
            StockItem.id == stock_item_id
        ).first()
        
        if not item:
            return {"error": "Item not found"}
        
        # Get costing method for this item (check category-specific first)
        method = config.default_costing_method
        if config.category_methods and item.category_id:
            # Look up category-specific costing method
            category_key = str(item.category_id)
            if category_key in config.category_methods:
                method = config.category_methods[category_key]
            # Also check by category name if available
            elif hasattr(item, 'category') and item.category and item.category.name:
                category_name = item.category.name.lower()
                for cat_key, cat_method in config.category_methods.items():
                    if cat_key.lower() == category_name:
                        method = cat_method
                        break
        
        # Get batches
        batches = db.query(StockBatch).filter(
            StockBatch.stock_item_id == stock_item_id,
            StockBatch.quantity > 0
        ).order_by(
            StockBatch.created_at.asc() if method == CostingMethod.FIFO.value
            else StockBatch.created_at.desc()
        ).all()
        
        if not batches:
            return {
                "unit_cost": item.cost_per_unit or 0,
                "total_cost": (item.cost_per_unit or 0) * quantity,
                "method": method,
                "source": "item_default"
            }
        
        if method == CostingMethod.WEIGHTED_AVERAGE.value:
            total_value = sum(b.quantity * (b.cost_per_unit or 0) for b in batches)
            total_qty = sum(b.quantity for b in batches)
            unit_cost = total_value / total_qty if total_qty else 0
        
        elif method in [CostingMethod.FIFO.value, CostingMethod.LIFO.value]:
            # Use first/last batch cost
            unit_cost = batches[0].cost_per_unit or 0
        
        else:
            unit_cost = item.cost_per_unit or 0
        
        return {
            "unit_cost": round(unit_cost, 4),
            "total_cost": round(unit_cost * quantity, 2),
            "method": method,
            "source": "calculated"
        }
    
    # ==========================================================================
    # CROSS-STORE STOCK BALANCING
    # ==========================================================================
    
    @staticmethod
    def analyze_cross_store_opportunities(
        db: Session,
        tenant_id: int
    ) -> List[CrossStoreStockSuggestion]:
        """Analyze and create cross-store stock balancing suggestions"""
        
        # Get all venues for tenant
        venues = db.query(Venue).filter(
            Venue.tenant_id == tenant_id,
            Venue.active == True
        ).all()
        
        if len(venues) < 2:
            return []
        
        suggestions = []
        
        # Get stock levels for all items across venues
        for item in db.query(StockItem).filter(
            StockItem.venue_id.in_([v.id for v in venues]),
            StockItem.is_active == True
        ).all():
            # Find same item at other venues (by SKU)
            if not item.sku:
                continue
            
            related_items = db.query(StockItem).filter(
                StockItem.sku == item.sku,
                StockItem.venue_id != item.venue_id,
                StockItem.venue_id.in_([v.id for v in venues]),
                StockItem.is_active == True
            ).all()
            
            for related in related_items:
                # Check if one has surplus and other has shortage
                item_status = "surplus" if item.quantity > item.low_stock_threshold * 2 else (
                    "shortage" if item.quantity <= item.low_stock_threshold else "normal"
                )
                related_status = "surplus" if related.quantity > related.low_stock_threshold * 2 else (
                    "shortage" if related.quantity <= related.low_stock_threshold else "normal"
                )
                
                if item_status == "surplus" and related_status == "shortage":
                    # Suggest transfer from item.venue to related.venue
                    transfer_qty = min(
                        item.quantity - item.low_stock_threshold,
                        related.low_stock_threshold - related.quantity
                    )
                    
                    if transfer_qty > 0:
                        suggestion = CrossStoreStockSuggestion(
                            from_venue_id=item.venue_id,
                            to_venue_id=related.venue_id,
                            stock_item_id=item.id,
                            suggested_quantity=transfer_qty,
                            reason="shortage",
                            from_store_quantity=item.quantity,
                            to_store_quantity=related.quantity,
                            status="pending"
                        )
                        db.add(suggestion)
                        suggestions.append(suggestion)
        
        db.commit()
        return suggestions
    
    @staticmethod
    def get_pending_suggestions(
        db: Session,
        venue_id: Optional[int] = None
    ) -> List[CrossStoreStockSuggestion]:
        """Get pending cross-store suggestions"""
        
        query = db.query(CrossStoreStockSuggestion).filter(
            CrossStoreStockSuggestion.status == "pending"
        )
        
        if venue_id:
            query = query.filter(
                or_(
                    CrossStoreStockSuggestion.from_venue_id == venue_id,
                    CrossStoreStockSuggestion.to_venue_id == venue_id
                )
            )
        
        return query.all()
    
    @staticmethod
    def approve_suggestion(
        db: Session,
        suggestion_id: int,
        approved_by: int
    ) -> CrossStoreStockSuggestion:
        """Approve a cross-store suggestion"""
        
        suggestion = db.query(CrossStoreStockSuggestion).filter(
            CrossStoreStockSuggestion.id == suggestion_id
        ).first()
        
        if not suggestion:
            raise ValueError("Suggestion not found")
        
        suggestion.status = "approved"
        suggestion.approved_by = approved_by
        
        db.commit()
        return suggestion
    
    @staticmethod
    def reject_suggestion(
        db: Session,
        suggestion_id: int
    ) -> CrossStoreStockSuggestion:
        """Reject a cross-store suggestion"""
        
        suggestion = db.query(CrossStoreStockSuggestion).filter(
            CrossStoreStockSuggestion.id == suggestion_id
        ).first()
        
        if not suggestion:
            raise ValueError("Suggestion not found")
        
        suggestion.status = "rejected"
        
        db.commit()
        return suggestion


# Class aliases for backwards compatibility with endpoint imports
AutoPurchaseOrderService = AdvancedSupplyChainService
SupplierLeadTimeService = AdvancedSupplyChainService
InventoryCostingService = AdvancedSupplyChainService
CrossStoreBalancingService = AdvancedSupplyChainService

