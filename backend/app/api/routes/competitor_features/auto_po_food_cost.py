"""Auto PO, food cost & supplier performance"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from enum import Enum

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and models
from app.api.routes.competitor_features._shared import *

router = APIRouter()

@router.post("/auto-po/rules", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_auto_po_rule(
    request: Request,
    rule_data: AutoPORuleCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Create auto purchase order rule"""
    if AutoPurchaseOrderRule is None:
        raise HTTPException(
            status_code=501,
            detail="Auto purchase order rules are not yet available. This feature is planned for a future release."
        )
    rule = AutoPurchaseOrderRule(
        venue_id=current_user.venue_id,
        **rule_data.model_dump()
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/auto-po/rules")
@limiter.limit("60/minute")
async def list_auto_po_rules(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all auto PO rules"""
    if AutoPurchaseOrderRule is None:
        return []
    try:
        rules = db.query(AutoPurchaseOrderRule).filter(
            AutoPurchaseOrderRule.venue_id == current_user.venue_id
        ).all()
    except Exception:
        return []
    return rules


@router.post("/auto-po/generate", response_model=List[SuggestedPOResponse])
@limiter.limit("30/minute")
async def generate_suggested_orders(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Generate suggested purchase orders based on rules"""
    if AutoPurchaseOrderService is None:
        raise HTTPException(
            status_code=501,
            detail="Auto purchase order service is not yet available. This feature is planned for a future release."
        )
    service = AutoPurchaseOrderService(db)
    try:
        suggestions = service.check_and_generate_orders(current_user.venue_id)
    except Exception:
        return []
    return suggestions


@router.get("/auto-po/suggestions", response_model=List[SuggestedPOResponse])
@limiter.limit("60/minute")
async def list_suggested_orders(
    request: Request,
    status_filter: Optional[str] = "pending",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List suggested purchase orders"""
    if SuggestedPurchaseOrder is None:
        return {
            "suggestions": [],
            "total": 0,
            "status": "not_implemented",
            "message": "Auto purchase order suggestions are not yet available. This feature is planned for a future release."
        }
    try:
        query = db.query(SuggestedPurchaseOrder).filter(
            SuggestedPurchaseOrder.location_id == current_user.venue_id
        )

        if status_filter:
            query = query.filter(SuggestedPurchaseOrder.status == status_filter)

        return query.order_by(SuggestedPurchaseOrder.generated_at.desc()).all()
    except Exception:
        return []


@router.post("/auto-po/suggestions/{suggestion_id}/approve")
@limiter.limit("30/minute")
async def approve_suggested_order(
    request: Request,
    suggestion_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Approve and convert suggested order to actual PO"""
    if AutoPurchaseOrderService is None:
        raise HTTPException(
            status_code=501,
            detail="Auto purchase order service is not yet available. This feature is planned for a future release."
        )
    service = AutoPurchaseOrderService(db)
    po = service.approve_and_convert(suggestion_id, current_user.id)

    if not po:
        raise HTTPException(status_code=404, detail="Suggestion not found or already processed")

    return {"purchase_order_id": po.id, "order_number": po.order_number}


# =============================================================================
# FOOD COST CALCULATOR ENDPOINTS
# =============================================================================

@router.get("/food-cost/item/{menu_item_id}", response_model=FoodCostResponse)
@limiter.limit("60/minute")
async def calculate_item_food_cost(
    request: Request,
    menu_item_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Calculate food cost for a menu item"""
    service = FoodCostService(db)
    result = service.calculate_menu_item_cost(current_user.venue_id, menu_item_id)

    if not result:
        raise HTTPException(status_code=404, detail="Menu item not found")

    return result


@router.post("/food-cost/calculate-all")
@limiter.limit("30/minute")
async def calculate_all_food_costs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Calculate food costs for all menu items"""
    logger = logging.getLogger(__name__)
    service = FoodCostService(db)

    items = db.query(MenuItem).filter(
        MenuItem.venue_id == current_user.venue_id,
        MenuItem.available == True
    ).all()

    calculated = 0
    failed = 0
    errors = []
    for item in items:
        try:
            result = service.calculate_menu_item_cost(current_user.venue_id, item.id)
            if result:
                calculated += 1
            else:
                failed += 1
                errors.append({"menu_item_id": item.id, "name": item.name, "error": "No recipe found"})
        except Exception as e:
            failed += 1
            error_msg = str(e)
            logger.warning(f"Failed to calculate food cost for menu item {item.id}: {error_msg}")
            errors.append({"menu_item_id": item.id, "name": item.name, "error": error_msg})

    return {
        "calculated_items": calculated,
        "failed_items": failed,
        "total_items": len(items),
        "errors": errors[:10] if errors else []  # Return first 10 errors for debugging
    }


@router.get("/food-cost/snapshot")
@limiter.limit("60/minute")
async def get_food_cost_snapshot(
    request: Request,
    snapshot_date: date = Query(default=None),
    period_type: str = "daily",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get or generate food cost snapshot"""
    if snapshot_date is None:
        snapshot_date = date.today()
    service = FoodCostService(db)
    snapshot = service.generate_cost_snapshot(
        venue_id=current_user.venue_id,
        snapshot_date=snapshot_date,
        period_type=period_type
    )
    return snapshot


@router.get("/food-cost/trend")
@limiter.limit("60/minute")
async def get_food_cost_trend(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get food cost trend over time"""
    start_date = date.today() - timedelta(days=days)

    snapshots = db.query(FoodCostSnapshot).filter(
        FoodCostSnapshot.venue_id == current_user.venue_id,
        FoodCostSnapshot.snapshot_date >= start_date,
        FoodCostSnapshot.period_type == "daily"
    ).order_by(FoodCostSnapshot.snapshot_date).all()

    return snapshots


# =============================================================================
# SUPPLIER PERFORMANCE ENDPOINTS
# =============================================================================

@router.get("/supplier-performance/ranking")
@limiter.limit("60/minute")
async def get_supplier_ranking(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get suppliers ranked by performance"""
    # Get latest performance for each supplier
    subq = db.query(
        SupplierPerformance.supplier_id,
        func.max(SupplierPerformance.calculated_at).label('latest')
    ).filter(
        SupplierPerformance.venue_id == current_user.venue_id
    ).group_by(SupplierPerformance.supplier_id).subquery()

    perfs = db.query(SupplierPerformance).filter(
        SupplierPerformance.venue_id == current_user.venue_id
    ).join(
        subq,
        (SupplierPerformance.supplier_id == subq.c.supplier_id) &
        (SupplierPerformance.calculated_at == subq.c.latest)
    ).order_by(SupplierPerformance.overall_score.desc()).all()

    return perfs


@router.get("/supplier-performance/{supplier_id}", response_model=SupplierPerformanceResponse)
@limiter.limit("60/minute")
async def get_supplier_performance(
    request: Request,
    supplier_id: int,
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get or calculate supplier performance"""
    if period_start is None:
        period_start = date.today() - timedelta(days=30)
    if period_end is None:
        period_end = date.today()
    service = SupplierPerformanceService(db)
    perf = service.calculate_performance(
        venue_id=current_user.venue_id,
        supplier_id=supplier_id,
        period_start=period_start,
        period_end=period_end
    )
    return perf


@router.post("/supplier-issues", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def report_supplier_issue(
    request: Request,
    issue_data: SupplierIssueCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Report an issue with a supplier"""
    service = SupplierPerformanceService(db)
    issue = service.report_issue(
        venue_id=current_user.venue_id,
        reported_by=current_user.id,
        **issue_data.model_dump()
    )
    return issue


@router.get("/supplier-issues")
@limiter.limit("60/minute")
async def list_supplier_issues(
    request: Request,
    supplier_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List supplier issues"""
    query = db.query(SupplierIssue).filter(
        SupplierIssue.venue_id == current_user.venue_id
    )

    if supplier_id:
        query = query.filter(SupplierIssue.supplier_id == supplier_id)
    if status_filter:
        query = query.filter(SupplierIssue.status == status_filter)

    return query.order_by(SupplierIssue.reported_at.desc()).all()


# =============================================================================
# PAR LEVEL ENDPOINTS
# =============================================================================

