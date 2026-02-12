"""
Auto Reorder Service
Automatically generates purchase orders when stock levels are low
"""
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime
import logging

from app.models import StockItem, Supplier, PurchaseOrder, PurchaseOrderItem
from app.models.feature_models import AutoReorderRule, AutoReorderLog

logger = logging.getLogger(__name__)


class AutoReorderService:
    """
    Handles automatic purchase order generation based on reorder rules.
    """

    def __init__(self, db: Session):
        self.db = db

    def check_and_reorder(self, venue_id: int) -> Dict[str, Any]:
        """
        Check all active reorder rules and generate POs as needed.

        Args:
            venue_id: Venue to check

        Returns:
            Dict with reorder results
        """
        results = {
            "venue_id": venue_id,
            "rules_checked": 0,
            "orders_created": [],
            "orders_pending_approval": [],
            "errors": []
        }

        # Get all active reorder rules for this venue
        rules = self.db.query(AutoReorderRule).filter(
            AutoReorderRule.venue_id == venue_id,
            AutoReorderRule.is_active == True
        ).all()

        results["rules_checked"] = len(rules)

        # Group rules by preferred supplier
        supplier_orders: Dict[int, List[Dict]] = {}

        for rule in rules:
            try:
                trigger_result = self._check_rule_trigger(rule)

                if trigger_result["should_trigger"]:
                    supplier_id = rule.preferred_supplier_id
                    if supplier_id not in supplier_orders:
                        supplier_orders[supplier_id] = []

                    supplier_orders[supplier_id].append({
                        "rule": rule,
                        "stock_item": trigger_result["stock_item"],
                        "quantity": trigger_result["order_quantity"],
                        "unit_price": trigger_result.get("unit_price", 0)
                    })

            except Exception as e:
                results["errors"].append({
                    "rule_id": rule.id,
                    "error": str(e)
                })

        # Create purchase orders grouped by supplier
        for supplier_id, items in supplier_orders.items():
            try:
                po_result = self._create_purchase_order(venue_id, supplier_id, items)

                if po_result.get("requires_approval"):
                    results["orders_pending_approval"].append(po_result)
                else:
                    results["orders_created"].append(po_result)

            except Exception as e:
                results["errors"].append({
                    "supplier_id": supplier_id,
                    "error": str(e)
                })

        results["success"] = len(results["errors"]) == 0
        return results

    def _check_rule_trigger(self, rule: AutoReorderRule) -> Dict[str, Any]:
        """
        Check if a rule should trigger a reorder.
        """
        stock_item = self.db.query(StockItem).filter(
            StockItem.id == rule.stock_item_id
        ).first()

        if not stock_item:
            return {"should_trigger": False}

        current_qty = float(stock_item.current_quantity or 0)
        reorder_point = float(rule.reorder_point or 0)

        # Check trigger conditions
        should_trigger = False

        if rule.trigger_type.value == "below_reorder_point":
            should_trigger = current_qty <= reorder_point

        elif rule.trigger_type.value == "below_par":
            par_level = float(rule.par_level or 0)
            should_trigger = current_qty <= par_level

        if not should_trigger:
            return {"should_trigger": False}

        # Calculate order quantity
        par_level = float(rule.par_level or rule.reorder_point or 0)
        quantity_needed = par_level - current_qty

        # Apply order constraints
        if rule.min_order_quantity:
            quantity_needed = max(quantity_needed, float(rule.min_order_quantity))

        if rule.max_order_quantity:
            quantity_needed = min(quantity_needed, float(rule.max_order_quantity))

        if rule.order_multiple:
            multiple = float(rule.order_multiple)
            quantity_needed = (quantity_needed // multiple + 1) * multiple

        # Get unit price from supplier
        unit_price = self._get_supplier_price(rule.preferred_supplier_id, stock_item.id)

        return {
            "should_trigger": True,
            "stock_item": stock_item,
            "order_quantity": quantity_needed,
            "current_quantity": current_qty,
            "reorder_point": reorder_point,
            "unit_price": unit_price
        }

    def _get_supplier_price(self, supplier_id: int, stock_item_id: int) -> float:
        """Get the last known price from supplier for this item."""
        # Check last PO for this supplier/item combo
        last_poi = self.db.query(PurchaseOrderItem).join(PurchaseOrder).filter(
            PurchaseOrder.supplier_id == supplier_id,
            PurchaseOrderItem.stock_item_id == stock_item_id
        ).order_by(PurchaseOrder.created_at.desc()).first()

        if last_poi and last_poi.unit_price:
            return float(last_poi.unit_price)

        return 0.0

    def _create_purchase_order(
        self,
        venue_id: int,
        supplier_id: int,
        items: List[Dict]
    ) -> Dict[str, Any]:
        """
        Create a purchase order for the given items.
        """
        supplier = self.db.query(Supplier).filter(Supplier.id == supplier_id).first()

        # Calculate totals
        total_amount = sum(
            item["quantity"] * item["unit_price"]
            for item in items
        )

        # Check if auto-approval is allowed
        requires_approval = True
        for item in items:
            rule = item["rule"]
            if rule.requires_approval:
                requires_approval = True
                break
            if rule.auto_approve_below_amount:
                item_total = item["quantity"] * item["unit_price"]
                if item_total >= float(rule.auto_approve_below_amount):
                    requires_approval = True

        # Create PO
        po = PurchaseOrder(
            venue_id=venue_id,
            supplier_id=supplier_id,
            order_number=f"AUTO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            status="pending_approval" if requires_approval else "pending",
            total_amount=total_amount,
            notes="Auto-generated by reorder service",
            created_at=datetime.utcnow()
        )
        self.db.add(po)
        self.db.flush()

        # Create PO items
        for item in items:
            poi = PurchaseOrderItem(
                purchase_order_id=po.id,
                stock_item_id=item["stock_item"].id,
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                total_price=item["quantity"] * item["unit_price"]
            )
            self.db.add(poi)

            # Update rule statistics
            rule = item["rule"]
            rule.times_triggered = (rule.times_triggered or 0) + 1
            rule.last_triggered_at = datetime.utcnow()
            rule.last_order_id = po.id

            # Create log entry
            log = AutoReorderLog(
                venue_id=venue_id,
                rule_id=rule.id,
                stock_item_id=item["stock_item"].id,
                triggered_at=datetime.utcnow(),
                trigger_type=rule.trigger_type.value,
                trigger_reason=f"Stock level {item['stock_item'].current_quantity} below reorder point {rule.reorder_point}",
                current_stock=float(item["stock_item"].current_quantity or 0),
                reorder_point=float(rule.reorder_point or 0),
                par_level=float(rule.par_level or 0),
                suggested_quantity=item["quantity"],
                final_quantity=item["quantity"],
                unit_price=item["unit_price"],
                total_amount=item["quantity"] * item["unit_price"],
                supplier_id=supplier_id,
                status="pending_approval" if requires_approval else "ordered",
                purchase_order_id=po.id
            )
            self.db.add(log)

        self.db.commit()

        return {
            "purchase_order_id": po.id,
            "order_number": po.order_number,
            "supplier_id": supplier_id,
            "supplier_name": supplier.name if supplier else None,
            "total_amount": total_amount,
            "item_count": len(items),
            "requires_approval": requires_approval,
            "status": po.status
        }

    def create_reorder_rule(
        self,
        venue_id: int,
        stock_item_id: int,
        reorder_point: float,
        par_level: float,
        preferred_supplier_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new auto-reorder rule.
        """
        rule = AutoReorderRule(
            venue_id=venue_id,
            stock_item_id=stock_item_id,
            is_active=True,
            reorder_point=reorder_point,
            par_level=par_level,
            preferred_supplier_id=preferred_supplier_id,
            **kwargs
        )

        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)

        return {
            "id": rule.id,
            "stock_item_id": stock_item_id,
            "reorder_point": reorder_point,
            "par_level": par_level,
            "preferred_supplier_id": preferred_supplier_id,
            "is_active": True
        }

    def get_reorder_rules(
        self,
        venue_id: int,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all reorder rules for a venue.
        """
        query = self.db.query(AutoReorderRule).filter(
            AutoReorderRule.venue_id == venue_id
        )

        if active_only:
            query = query.filter(AutoReorderRule.is_active == True)

        rules = query.all()

        return [
            {
                "id": r.id,
                "stock_item_id": r.stock_item_id,
                "reorder_point": float(r.reorder_point or 0),
                "par_level": float(r.par_level or 0),
                "preferred_supplier_id": r.preferred_supplier_id,
                "trigger_type": r.trigger_type.value if r.trigger_type else None,
                "is_active": r.is_active,
                "times_triggered": r.times_triggered,
                "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None
            }
            for r in rules
        ]

    def get_reorder_logs(
        self,
        venue_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get reorder history/logs.
        """
        query = self.db.query(AutoReorderLog).filter(
            AutoReorderLog.venue_id == venue_id
        )

        total = query.count()
        logs = query.order_by(AutoReorderLog.triggered_at.desc()).offset(offset).limit(limit).all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": [
                {
                    "id": log.id,
                    "rule_id": log.rule_id,
                    "stock_item_id": log.stock_item_id,
                    "triggered_at": log.triggered_at.isoformat() if log.triggered_at else None,
                    "trigger_type": log.trigger_type,
                    "current_stock": float(log.current_stock or 0),
                    "reorder_point": float(log.reorder_point or 0),
                    "final_quantity": float(log.final_quantity or 0),
                    "total_amount": float(log.total_amount or 0),
                    "status": log.status,
                    "purchase_order_id": log.purchase_order_id
                }
                for log in logs
            ]
        }


def get_auto_reorder_service(db: Session) -> AutoReorderService:
    """Factory function to get auto reorder service"""
    return AutoReorderService(db)
