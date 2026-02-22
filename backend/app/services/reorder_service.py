"""Reorder service: Generate reorder proposals based on stock analysis."""

import json
import math
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import logging

from sqlalchemy.orm import Session

from app.models.inventory import InventorySession, InventoryLine
from app.models.reconciliation import ReorderProposal, DeltaSeverity
from app.models.product import Product
from app.models.supplier import Supplier
from app.services.pos import get_pos_adapter, POSProduct, POSSalesAggregate, POSInTransitOrder

logger = logging.getLogger(__name__)


class ReorderConfig:
    """Configuration for reorder calculations."""

    def __init__(
        self,
        coverage_days: int = 14,
        use_par_level: bool = True,
        round_to_case: bool = True,
        min_order_qty: int = 1,
        safety_stock_percent: Decimal = Decimal("10"),
    ):
        self.coverage_days = coverage_days
        self.use_par_level = use_par_level
        self.round_to_case = round_to_case
        self.min_order_qty = min_order_qty
        self.safety_stock_percent = safety_stock_percent  # Extra % for safety stock


class ReorderService:
    """Service for generating reorder proposals."""

    def __init__(self, db: Session, config: Optional[ReorderConfig] = None):
        self.db = db
        self.config = config or ReorderConfig()
        self.pos_adapter = get_pos_adapter(db)

    def get_counted_stock(
        self,
        session_id: int,
    ) -> Dict[int, Decimal]:
        """Get current stock from inventory count."""
        lines = (
            self.db.query(InventoryLine)
            .filter(InventoryLine.session_id == session_id)
            .all()
        )

        # Aggregate by product (in case multiple counts)
        result: Dict[int, Decimal] = {}
        for line in lines:
            if line.product_id not in result:
                result[line.product_id] = Decimal("0")
            result[line.product_id] += line.counted_qty

        return result

    def get_in_transit_quantities(
        self,
        product_ids: List[int],
    ) -> Dict[int, Decimal]:
        """Get in-transit order quantities from POS."""
        orders = self.pos_adapter.get_in_transit_orders(product_ids=product_ids)

        result: Dict[int, Decimal] = {}
        for order in orders:
            if order.product_id not in result:
                result[order.product_id] = Decimal("0")
            result[order.product_id] += Decimal(str(order.qty_ordered - order.qty_received))

        return result

    def get_avg_daily_sales(
        self,
        location_id: int,
        product_ids: List[int],
        days: int = 30,
    ) -> Dict[int, Decimal]:
        """Get average daily sales for products over recent period."""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        sales = self.pos_adapter.get_sales_aggregate(
            location_id=location_id,
            product_ids=product_ids,
            start_date=start_date,
            end_date=end_date,
        )

        return {
            s.product_id: Decimal(str(s.avg_daily_qty)) if s.avg_daily_qty else Decimal("0")
            for s in sales
        }

    def calculate_target_stock(
        self,
        product: Product,
        avg_daily_sales: Decimal,
    ) -> Decimal:
        """Calculate target stock level for a product."""
        # Use par level if available and configured
        if self.config.use_par_level and product.par_level:
            return Decimal(str(product.par_level))

        # Calculate based on coverage days + safety stock
        base_target = avg_daily_sales * self.config.coverage_days
        safety_stock = base_target * (self.config.safety_stock_percent / 100)

        return base_target + safety_stock

    def round_to_pack(self, qty: Decimal, pack_size: int) -> Decimal:
        """Round quantity up to nearest pack size."""
        if not self.config.round_to_case or pack_size <= 1:
            return max(qty, Decimal(self.config.min_order_qty))

        packs_needed = math.ceil(float(qty) / pack_size)
        return Decimal(max(packs_needed * pack_size, self.config.min_order_qty))

    def generate_proposals(
        self,
        session_id: int,
        clear_previous: bool = True,
    ) -> List[ReorderProposal]:
        """
        Generate reorder proposals for products that need restocking.

        Args:
            session_id: The inventory session to base proposals on
            clear_previous: If True, delete previous proposals for this session

        Returns:
            List of ReorderProposal objects created
        """
        # Get the session
        session = self.db.query(InventorySession).filter(
            InventorySession.id == session_id
        ).first()

        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Clear previous proposals if requested
        if clear_previous:
            self.db.query(ReorderProposal).filter(
                ReorderProposal.session_id == session_id
            ).delete()

        # Get counted stock
        counted_stock = self.get_counted_stock(session_id)

        if not counted_stock:
            logger.warning(f"No inventory lines found for session {session_id}")
            return []

        product_ids = list(counted_stock.keys())

        # Get product info
        products = {
            p.id: p
            for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()
        }

        # Get in-transit quantities
        in_transit = self.get_in_transit_quantities(product_ids)

        # Get average daily sales
        avg_daily_sales = self.get_avg_daily_sales(
            location_id=session.location_id,
            product_ids=product_ids,
        )

        proposals = []

        for product_id, current_stock in counted_stock.items():
            product = products.get(product_id)
            if not product:
                continue

            # Skip inactive products
            if hasattr(product, 'is_active') and not product.is_active:
                continue

            # Calculate target stock
            daily_sales = avg_daily_sales.get(product_id, Decimal("0"))
            target_stock = self.calculate_target_stock(product, daily_sales)

            # Get in-transit
            transit_qty = in_transit.get(product_id, Decimal("0"))

            # Calculate recommended order quantity
            available = current_stock + transit_qty
            need = target_stock - available

            if need <= 0:
                continue  # No reorder needed

            # Get pack size from product (try pack_size first, then case_pack for compatibility)
            pack_size = getattr(product, 'pack_size', None) or getattr(product, 'case_pack', 1) or 1

            # Round to pack size
            rounded_qty = self.round_to_pack(need, pack_size)

            # Calculate cost
            unit_cost = product.cost_price if hasattr(product, 'cost_price') else None
            line_total = rounded_qty * unit_cost if unit_cost else None

            # Build rationale
            rationale = {
                "calculation": "target - (current + in_transit)",
                "target_stock": float(target_stock),
                "current_stock": float(current_stock),
                "in_transit": float(transit_qty),
                "raw_need": float(need),
                "avg_daily_sales": float(daily_sales),
                "coverage_days": self.config.coverage_days,
                "par_level_used": bool(self.config.use_par_level and product.par_level),
                "pack_size": pack_size,
            }

            # Create proposal
            proposal = ReorderProposal(
                session_id=session_id,
                product_id=product_id,
                supplier_id=product.supplier_id if hasattr(product, 'supplier_id') else None,
                current_stock=current_stock,
                target_stock=target_stock,
                in_transit=transit_qty,
                recommended_qty=need,
                rounded_qty=rounded_qty,
                pack_size=pack_size,
                unit_cost=unit_cost,
                line_total=line_total,
                rationale_json=json.dumps(rationale),
                included=True,
            )

            self.db.add(proposal)
            proposals.append(proposal)

        self.db.flush()  # Assign IDs

        logger.info(
            f"Generated {len(proposals)} reorder proposals for session {session_id}"
        )

        return proposals

    def get_proposals_by_supplier(
        self,
        session_id: int,
        include_excluded: bool = False,
    ) -> Dict[int, Dict]:
        """
        Get reorder proposals grouped by supplier.

        Returns dict mapping supplier_id -> {supplier_info, proposals, totals}
        """
        query = (
            self.db.query(ReorderProposal)
            .filter(ReorderProposal.session_id == session_id)
        )

        if not include_excluded:
            query = query.filter(ReorderProposal.included == True)

        proposals = query.all()

        if not proposals:
            return {}

        # Get supplier info
        supplier_ids = list(set(p.supplier_id for p in proposals if p.supplier_id))
        suppliers = {
            s.id: s
            for s in self.db.query(Supplier).filter(Supplier.id.in_(supplier_ids)).all()
        }

        # Get product info
        product_ids = list(set(p.product_id for p in proposals))
        products = {
            p.id: p
            for p in self.db.query(Product).filter(Product.id.in_(product_ids)).all()
        }

        # Group by supplier
        result: Dict[int, Dict] = {}

        for proposal in proposals:
            supplier_id = proposal.supplier_id or 0  # 0 for products without supplier

            if supplier_id not in result:
                supplier = suppliers.get(supplier_id) if supplier_id else None
                result[supplier_id] = {
                    "supplier_id": supplier_id if supplier_id else None,
                    "supplier_name": supplier.name if supplier else "No Supplier",
                    "supplier_email": supplier.contact_email if supplier else None,
                    "supplier_phone": supplier.contact_phone if supplier else None,
                    "proposals": [],
                    "total_qty": Decimal("0"),
                    "total_value": Decimal("0"),
                    "line_count": 0,
                }

            product = products.get(proposal.product_id)

            # Use user_qty if set, otherwise rounded_qty
            order_qty = proposal.user_qty if proposal.user_qty is not None else proposal.rounded_qty

            result[supplier_id]["proposals"].append({
                "id": proposal.id,
                "product_id": proposal.product_id,
                "product_name": product.name if product else None,
                "product_barcode": product.barcode if product else None,
                "product_sku": getattr(product, 'sku', None) if product else None,
                "current_stock": float(proposal.current_stock),
                "target_stock": float(proposal.target_stock),
                "in_transit": float(proposal.in_transit),
                "recommended_qty": float(proposal.recommended_qty),
                "rounded_qty": float(proposal.rounded_qty),
                "order_qty": float(order_qty),
                "pack_size": proposal.pack_size,
                "unit_cost": float(proposal.unit_cost) if proposal.unit_cost else None,
                "line_total": float(order_qty * proposal.unit_cost) if proposal.unit_cost else None,
                "included": proposal.included,
            })

            result[supplier_id]["total_qty"] += order_qty
            result[supplier_id]["line_count"] += 1
            if proposal.unit_cost:
                result[supplier_id]["total_value"] += order_qty * proposal.unit_cost

        # Convert decimals to floats for JSON serialization
        for supplier_id, data in result.items():
            data["total_qty"] = float(data["total_qty"])
            data["total_value"] = float(data["total_value"])

        return result

    def get_reorder_summary(
        self,
        session_id: int,
    ) -> Dict:
        """Get summary of reorder proposals for a session."""
        proposals = (
            self.db.query(ReorderProposal)
            .filter(ReorderProposal.session_id == session_id)
            .filter(ReorderProposal.included == True)
            .all()
        )

        if not proposals:
            return {
                "session_id": session_id,
                "total_products": 0,
                "total_qty": 0,
                "total_value": None,
                "suppliers_count": 0,
            }

        supplier_ids = set(p.supplier_id for p in proposals if p.supplier_id)
        total_qty = sum(p.user_qty if p.user_qty is not None else p.rounded_qty for p in proposals)
        total_value = sum(
            (p.user_qty if p.user_qty is not None else p.rounded_qty) * p.unit_cost
            for p in proposals if p.unit_cost
        )

        return {
            "session_id": session_id,
            "total_products": len(proposals),
            "total_qty": float(total_qty),
            "total_value": float(total_value) if total_value else None,
            "suppliers_count": len(supplier_ids),
            "proposals_by_supplier": self.get_proposals_by_supplier(session_id),
        }

    def update_proposal(
        self,
        proposal_id: int,
        user_qty: Optional[Decimal] = None,
        included: Optional[bool] = None,
    ) -> ReorderProposal:
        """Update a reorder proposal with user overrides."""
        proposal = self.db.query(ReorderProposal).filter(
            ReorderProposal.id == proposal_id
        ).first()

        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        if user_qty is not None:
            proposal.user_qty = user_qty
            # Recalculate line total
            if proposal.unit_cost:
                proposal.line_total = user_qty * proposal.unit_cost

        if included is not None:
            proposal.included = included

        self.db.flush()
        return proposal


def generate_reorder_proposals(
    db: Session,
    session_id: int,
    coverage_days: int = 14,
    use_par_level: bool = True,
    round_to_case: bool = True,
) -> Dict:
    """
    Convenience function to generate reorder proposals.
    Returns the reorder summary grouped by supplier.
    """
    config = ReorderConfig(
        coverage_days=coverage_days,
        use_par_level=use_par_level,
        round_to_case=round_to_case,
    )

    service = ReorderService(db, config)
    service.generate_proposals(session_id)

    return service.get_reorder_summary(session_id)
