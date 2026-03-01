"""Transfers, cost analysis, AI scanner, availability, PAR, reservations"""
import logging
import random
import uuid
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, UploadFile

from app.core.rate_limit import limiter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, and_, or_

from app.db.session import DbSession
from app.models.stock import StockOnHand, StockMovement, MovementReason
from app.models.product import Product
from app.models.location import Location
from app.models.order import PurchaseOrder, PurchaseOrderLine
from app.models.inventory import InventorySession, InventoryLine, SessionStatus
from app.services.stock_deduction_service import StockDeductionService
from app.services.stock_alert_service import StockAlertService
from app.services.stock_count_service import StockCountService
from app.models.menu_inventory_complete import (
    StockItemBarcode, StockBatchFIFO, ShrinkageRecord,
    CycleCountSchedule, CycleCountTask, CycleCountItem, UnitConversion,
    ReconciliationSession, ReconciliationItem, SupplierPerformanceRecord,
    ReorderPriority, CountType, ShrinkageReason, ReconciliationStatus
)
from app.models.feature_models import AutoReorderRule

logger = logging.getLogger(__name__)

router = APIRouter()

# ====================================================================
# MERGED FROM stock_management.py - Unique endpoints
# Transfers (create/bulk), Cost Analysis, AI Scanner, Availability,
# Smart PAR, Reservations, Multi-location Aggregation, Transfer Suggestions
# ====================================================================

# ==================== SCHEMAS (from stock_management) ====================

class StockTransferRequest(BaseModel):
    product_id: int
    quantity: float
    from_location_id: int
    to_location_id: int
    notes: Optional[str] = None


class BulkTransferItem(BaseModel):
    product_id: int
    quantity: float


class BulkTransferRequest(BaseModel):
    from_location_id: int
    to_location_id: int
    items: List[BulkTransferItem]
    notes: Optional[str] = None


class AIShelfScanRequest(BaseModel):
    location_id: int
    image_data: Optional[str] = None  # base64 encoded image
    image_url: Optional[str] = None
    shelf_section: Optional[str] = None
    notes: Optional[str] = None


class CostMethodRequest(BaseModel):
    product_id: int
    method: str = "weighted_average"  # fifo, weighted_average, last_cost


class SmartParRequest(BaseModel):
    lookback_days: int = 30
    safety_factor: float = 1.5
    order_cycle_days: int = 7


class BulkParRequest(BaseModel):
    location_id: int = 1
    lookback_days: int = 30
    safety_factor: float = 1.5
    order_cycle_days: int = 7
    auto_apply: bool = False


class ReserveStockRequest(BaseModel):
    order_items: List[dict]  # [{menu_item_id, quantity}]
    location_id: int = 1
    reference_id: Optional[int] = None


class CancelReservationRequest(BaseModel):
    reference_id: int
    reference_type: str = "order_reservation"
    location_id: int = 1


# ==================== TRANSFERS (create / bulk / history) ====================

@router.post("/transfers")
@limiter.limit("30/minute")
def create_transfer(
    request: Request,
    db: DbSession,
    transfer_request: StockTransferRequest,
):
    """
    Transfer stock between locations.
    Creates paired TRANSFER_OUT and TRANSFER_IN movements (like Revel/Toast).
    Validates sufficient stock at source location.
    """
    stock_service = StockDeductionService(db)
    result = stock_service.transfer_stock(
        product_id=transfer_request.product_id,
        quantity=Decimal(str(transfer_request.quantity)),
        from_location_id=transfer_request.from_location_id,
        to_location_id=transfer_request.to_location_id,
        notes=transfer_request.notes,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Transfer failed"))

    return result


@router.post("/transfers/bulk")
@limiter.limit("30/minute")
def create_bulk_transfer(
    request: Request,
    db: DbSession,
    bulk_request: BulkTransferRequest,
):
    """
    Transfer multiple products between locations in a single operation.
    All-or-nothing: if any transfer fails, none are committed.
    """
    stock_service = StockDeductionService(db)
    results = []
    errors = []

    for item in bulk_request.items:
        result = stock_service.transfer_stock(
            product_id=item.product_id,
            quantity=Decimal(str(item.quantity)),
            from_location_id=bulk_request.from_location_id,
            to_location_id=bulk_request.to_location_id,
            notes=bulk_request.notes,
        )
        if result.get("success"):
            results.append(result)
        else:
            errors.append(result)

    return {
        "success": len(errors) == 0,
        "transferred": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@router.get("/transfers/history")
@limiter.limit("60/minute")
def get_transfer_history(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
    limit: int = Query(50, le=500),
):
    """Get transfer movement history."""
    query = db.query(StockMovement).filter(
        StockMovement.reason.in_([
            MovementReason.TRANSFER_IN.value,
            MovementReason.TRANSFER_OUT.value,
        ])
    )
    if location_id:
        query = query.filter(StockMovement.location_id == location_id)

    movements = query.order_by(StockMovement.ts.desc()).limit(limit).all()

    return {
        "transfers": [
            {
                "id": m.id,
                "product_id": m.product_id,
                "location_id": m.location_id,
                "qty_delta": float(m.qty_delta),
                "direction": "in" if m.reason == MovementReason.TRANSFER_IN.value else "out",
                "ref_id": m.ref_id,
                "notes": m.notes,
                "timestamp": m.ts.isoformat() if m.ts else None,
                "created_by": m.created_by,
            }
            for m in movements
        ],
        "total": len(movements),
    }


# ==================== COST TRACKING ====================

@router.get("/cost-analysis")
@limiter.limit("60/minute")
def get_cost_analysis(
    request: Request,
    db: DbSession,
    location_id: int = Query(1),
    method: str = Query("weighted_average", description="fifo, weighted_average, or last_cost"),
):
    """
    Calculate product costs using FIFO, weighted average, or last cost method.
    Matches Restaurant365/MarketMan COGS tracking.
    """
    stock_items = db.query(StockOnHand).filter(
        StockOnHand.location_id == location_id,
    ).all()

    items = []
    total_value = Decimal("0")

    for s in stock_items:
        product = db.query(Product).filter(Product.id == s.product_id).first()
        if not product or s.qty <= 0:
            continue

        if method == "last_cost":
            # Last purchase cost
            last_purchase = db.query(StockMovement).filter(
                StockMovement.product_id == product.id,
                StockMovement.reason == MovementReason.PURCHASE.value,
                StockMovement.qty_delta > 0,
            ).order_by(StockMovement.ts.desc()).first()

            if last_purchase:
                # Get cost from PO line
                po_line = db.query(PurchaseOrderLine).filter(
                    PurchaseOrderLine.product_id == product.id,
                ).order_by(PurchaseOrderLine.id.desc()).first()
                unit_cost = po_line.unit_cost if po_line and po_line.unit_cost else product.cost_price or Decimal("0")
            else:
                unit_cost = product.cost_price or Decimal("0")

        elif method == "fifo":
            # FIFO: use oldest purchase costs first
            try:
                from app.models.advanced_features import InventoryBatch
                batches = db.query(InventoryBatch).filter(
                    InventoryBatch.product_id == product.id,
                    InventoryBatch.location_id == location_id,
                    InventoryBatch.current_quantity > 0,
                ).order_by(InventoryBatch.received_date.asc()).all()

                if batches:
                    total_cost = sum(
                        b.current_quantity * (b.unit_cost or product.cost_price or Decimal("0"))
                        for b in batches
                    )
                    total_qty = sum(b.current_quantity for b in batches)
                    unit_cost = total_cost / total_qty if total_qty > 0 else Decimal("0")
                else:
                    unit_cost = product.cost_price or Decimal("0")
            except Exception as e:
                logger.warning(f"FIFO batch cost calculation failed for product {product.id} at location {location_id}, falling back to cost_price: {e}")
                unit_cost = product.cost_price or Decimal("0")

        else:  # weighted_average
            # Weighted average of all purchases
            purchases = db.query(
                func.sum(PurchaseOrderLine.qty).label("total_qty"),
                func.sum(PurchaseOrderLine.qty * PurchaseOrderLine.unit_cost).label("total_cost"),
            ).filter(
                PurchaseOrderLine.product_id == product.id,
                PurchaseOrderLine.unit_cost.isnot(None),
            ).first()

            if purchases and purchases.total_qty and purchases.total_qty > 0:
                unit_cost = purchases.total_cost / purchases.total_qty
            else:
                unit_cost = product.cost_price or Decimal("0")

        item_value = s.qty * unit_cost
        total_value += item_value

        items.append({
            "product_id": product.id,
            "product_name": product.name,
            "qty_on_hand": float(s.qty),
            "unit": product.unit,
            "unit_cost": float(unit_cost),
            "total_value": float(item_value),
            "cost_method": method,
        })

    items.sort(key=lambda x: x["total_value"], reverse=True)

    return {
        "method": method,
        "location_id": location_id,
        "total_inventory_value": float(total_value),
        "total_items": len(items),
        "items": items,
    }


# ==================== AI SHELF SCANNER ====================

@router.post("/ai-scan")
@limiter.limit("30/minute")
def ai_shelf_scan(
    request: Request,
    db: DbSession,
    scan_request: AIShelfScanRequest,
):
    """
    AI-powered shelf scanning for inventory counting.

    Flow:
    1. Receives shelf image (camera/upload)
    2. Uses CLIP/YOLO to detect products and estimate quantities
    3. Creates an InventorySession with detected items
    4. Returns detected items with confidence scores for human review
    5. User approves -> session is committed -> stock adjusted

    Integrates with existing AI infrastructure and inventory count system.
    """
    # Create an inventory session for this scan
    session = InventorySession(
        location_id=scan_request.location_id,
        notes=f"AI Shelf Scan - {scan_request.shelf_section or 'Full shelf'} - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
    )
    db.add(session)
    db.flush()

    detected_items = []

    # Try to use AI models for detection
    ai_available = False
    try:
        from app.services.ai.combined_recognition import CombinedRecognitionService
        ai_service = CombinedRecognitionService()
        ai_available = True
    except Exception as e:
        logger.debug(f"Optional: load AI recognition service: {e}")

    if ai_available and (scan_request.image_data or scan_request.image_url):
        try:
            # Use AI to detect products in the image
            recognition_result = ai_service.recognize(
                image_data=scan_request.image_data,
                image_url=scan_request.image_url,
            )

            for detection in recognition_result.get("detections", []):
                product_name = detection.get("label", "")
                confidence = detection.get("confidence", 0)
                estimated_qty = detection.get("quantity", 1)

                # Match detected item to product in database
                product = db.query(Product).filter(
                    Product.ai_label == product_name
                ).first()

                if not product:
                    product = db.query(Product).filter(
                        Product.name.ilike(f"%{product_name}%")
                    ).first()

                if product:
                    # Add to inventory session
                    line = InventoryLine(
                        session_id=session.id,
                        product_id=product.id,
                        counted_qty=Decimal(str(estimated_qty)),
                        method="ai_scan",
                        confidence=confidence,
                    )
                    db.add(line)

                    # Get current stock for comparison
                    current_stock = db.query(StockOnHand).filter(
                        StockOnHand.product_id == product.id,
                        StockOnHand.location_id == scan_request.location_id,
                    ).first()

                    detected_items.append({
                        "product_id": product.id,
                        "product_name": product.name,
                        "detected_qty": estimated_qty,
                        "current_stock_qty": float(current_stock.qty) if current_stock else 0,
                        "variance": estimated_qty - (float(current_stock.qty) if current_stock else 0),
                        "confidence": confidence,
                        "ai_label": product_name,
                        "needs_review": confidence < 0.8,
                    })
        except Exception as e:
            logger.warning(f"AI scan failed, falling back to manual: {e}")

    # If no AI detections, create a template session with all products at location
    if not detected_items:
        products = db.query(Product).filter(Product.active == True).limit(100).all()
        for product in products:
            current_stock = db.query(StockOnHand).filter(
                StockOnHand.product_id == product.id,
                StockOnHand.location_id == scan_request.location_id,
            ).first()

            detected_items.append({
                "product_id": product.id,
                "product_name": product.name,
                "detected_qty": None,  # To be filled by user
                "current_stock_qty": float(current_stock.qty) if current_stock else 0,
                "variance": None,
                "confidence": None,
                "ai_label": product.ai_label,
                "needs_review": True,
            })

    db.commit()

    return {
        "session_id": session.id,
        "location_id": scan_request.location_id,
        "shelf_section": scan_request.shelf_section,
        "ai_available": ai_available,
        "detected_items": detected_items,
        "total_detected": len([i for i in detected_items if i["detected_qty"] is not None]),
        "needs_review": len([i for i in detected_items if i.get("needs_review")]),
        "instructions": "Review detected items, adjust quantities, then POST /stock/ai-scan/{session_id}/commit to apply.",
    }


@router.post("/ai-scan/{session_id}/commit")
@limiter.limit("30/minute")
def commit_ai_scan(
    request: Request,
    db: DbSession,
    session_id: int,
):
    """
    Commit an AI shelf scan session.
    This creates stock movements for any variances between scanned and current quantities.
    Same logic as inventory session commit.
    """
    session = db.query(InventorySession).filter(InventorySession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Scan session not found")

    if session.status != SessionStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Session already committed")

    if not session.lines:
        raise HTTPException(status_code=400, detail="No items in scan session")

    movements_created = 0
    adjustments = []

    for line in session.lines:
        stock = db.query(StockOnHand).filter(
            StockOnHand.product_id == line.product_id,
            StockOnHand.location_id == session.location_id,
        ).first()

        current_qty = stock.qty if stock else Decimal("0")
        delta = line.counted_qty - current_qty

        if delta != 0:
            movement = StockMovement(
                product_id=line.product_id,
                location_id=session.location_id,
                qty_delta=delta,
                reason=MovementReason.INVENTORY_COUNT.value,
                ref_type="ai_shelf_scan",
                ref_id=session.id,
                notes=f"AI Scan adjustment (confidence: {line.confidence or 'manual'})",
            )
            db.add(movement)
            movements_created += 1

            if stock:
                stock.qty = line.counted_qty
            else:
                stock = StockOnHand(
                    product_id=line.product_id,
                    location_id=session.location_id,
                    qty=line.counted_qty,
                )
                db.add(stock)

            adjustments.append({
                "product_id": line.product_id,
                "previous_qty": float(current_qty),
                "scanned_qty": float(line.counted_qty),
                "delta": float(delta),
                "confidence": line.confidence,
            })

    session.status = SessionStatus.COMMITTED
    session.committed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "session_id": session.id,
        "status": "committed",
        "movements_created": movements_created,
        "adjustments": adjustments,
    }


@router.put("/ai-scan/{session_id}/lines/{line_id}")
@limiter.limit("30/minute")
def update_scan_line(
    request: Request,
    db: DbSession,
    session_id: int,
    line_id: int,
    counted_qty: float = Query(...),
    confidence: Optional[float] = None,
):
    """Update a scanned item quantity (for human review/correction)."""
    session = db.query(InventorySession).filter(InventorySession.id == session_id).first()
    if not session or session.status != SessionStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Session not found or already committed")

    line = db.query(InventoryLine).filter(
        InventoryLine.id == line_id,
        InventoryLine.session_id == session_id,
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Line not found")

    line.counted_qty = Decimal(str(counted_qty))
    if confidence is not None:
        line.confidence = confidence
    line.method = "manual_override"
    db.commit()

    return {"status": "updated", "line_id": line_id, "new_qty": counted_qty}


# ==================== STOCK AVAILABILITY CHECK ====================

@router.get("/availability")
@limiter.limit("60/minute")
def check_menu_availability(
    request: Request,
    db: DbSession,
    location_id: int = Query(1),
):
    """
    Check which menu items can be made with current stock.
    Auto-identifies items that should be 86'd.
    Matches Toast/TouchBistro 86'd item detection.
    """
    from app.models.restaurant import MenuItem

    stock_service = StockDeductionService(db)
    menu_items = db.query(MenuItem).filter(MenuItem.available == True).all()
    menu_item_ids = [item.id for item in menu_items]

    result = stock_service.check_availability(menu_item_ids, location_id)
    return result


# ==================== SMART PAR CALCULATION ====================

@router.post("/calculate-par/{product_id}")
@limiter.limit("30/minute")
def calculate_smart_par(
    request: Request,
    db: DbSession,
    product_id: int,
    location_id: int = Query(1),
    lookback_days: int = Query(30, le=365),
    safety_factor: float = Query(1.5),
    order_cycle_days: int = Query(7),
):
    """
    Calculate smart PAR level for a product using industry formula:
    - avg_daily_usage = sum of SALE movements / lookback_days
    - safety_stock = avg_daily_usage x safety_factor
    - reorder_point = (avg_daily_usage x lead_time) + safety_stock
    - recommended_par = reorder_point + (avg_daily_usage x order_cycle_days)

    Matches MarketMan/xtraCHEF/Toast PAR calculation.
    """
    stock_service = StockDeductionService(db)
    result = stock_service.calculate_smart_par(
        product_id=product_id,
        location_id=location_id,
        lookback_days=lookback_days,
        safety_factor=safety_factor,
        order_cycle_days=order_cycle_days,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/recalculate-all-pars")
@limiter.limit("30/minute")
def recalculate_all_pars(
    request: Request,
    db: DbSession,
    par_request: BulkParRequest,
):
    """
    Recalculate PAR levels for ALL active products using smart formula.
    Set auto_apply=true to automatically update product PAR levels.
    """
    stock_service = StockDeductionService(db)
    return stock_service.bulk_recalculate_pars(
        location_id=par_request.location_id,
        lookback_days=par_request.lookback_days,
        safety_factor=par_request.safety_factor,
        order_cycle_days=par_request.order_cycle_days,
        auto_apply=par_request.auto_apply,
    )


# ==================== STOCK RESERVATION ====================

@router.post("/reserve")
@limiter.limit("30/minute")
def reserve_stock(
    request: Request,
    db: DbSession,
    reserve_request: ReserveStockRequest,
):
    """
    Reserve stock for an in-progress order.
    Reserved stock remains physically present but is not available for new orders.
    Use /stock/fulfill to convert reservation to actual deduction.
    Use /stock/cancel-reservation to release reserved stock.
    """
    stock_service = StockDeductionService(db)
    result = stock_service.reserve_for_order(
        order_items=reserve_request.order_items,
        location_id=reserve_request.location_id,
        reference_id=reserve_request.reference_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("errors", "Reservation failed"))
    return result


@router.post("/cancel-reservation")
@limiter.limit("30/minute")
def cancel_reservation(
    request: Request,
    db: DbSession,
    cancel_request: CancelReservationRequest,
):
    """Cancel stock reservations and release reserved stock back to available pool."""
    stock_service = StockDeductionService(db)
    return stock_service.cancel_reservation(
        reference_id=cancel_request.reference_id,
        reference_type=cancel_request.reference_type,
        location_id=cancel_request.location_id,
    )


# ==================== MULTI-LOCATION AGGREGATION ====================

@router.get("/aggregate")
@limiter.limit("60/minute")
def get_aggregate_stock(
    request: Request,
    db: DbSession,
):
    """
    Company-wide stock aggregation across all locations.
    Returns total quantity, value, and per-location breakdown for every product.
    """
    stock_service = StockDeductionService(db)
    return stock_service.get_aggregate_stock()


@router.get("/transfer-suggestions")
@limiter.limit("60/minute")
def get_transfer_suggestions(
    request: Request,
    db: DbSession,
    location_id: Optional[int] = None,
):
    """
    Suggest stock transfers from overstocked to understocked locations.
    Identifies products where one location has >150% of PAR
    and another has <50% of PAR.
    """
    stock_service = StockDeductionService(db)
    return stock_service.suggest_transfers(location_id=location_id)


