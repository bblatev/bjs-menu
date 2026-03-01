"""Limited offers, 86 system, digital boards & engineering"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.menu_complete_features._shared import *
from app.api.routes.menu_complete_features._shared import _next_ids, _limited_offers, _item86_records, _digital_boards, _variants

router = APIRouter()

@router.post("/limited-offers", response_model=LimitedTimeOfferResponse)
@limiter.limit("30/minute")
def create_limited_offer(
    request: Request,
    data: LimitedTimeOfferCreate,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Create a limited-time offer."""
    global _next_ids

    # Calculate savings
    savings = None
    if data.original_price and data.offer_price:
        savings = data.original_price - data.offer_price
    elif data.original_price and data.discount_percentage:
        savings = data.original_price * data.discount_percentage / 100

    now = datetime.now(timezone.utc)
    is_expired = now > data.end_datetime
    time_remaining = int((data.end_datetime - now).total_seconds()) if not is_expired else 0

    offer = {
        "id": _next_ids["offer"],
        "name": data.name,
        "description": data.description,
        "menu_item_id": data.menu_item_id,
        "category_id": data.category_id,
        "offer_type": data.offer_type,
        "original_price": data.original_price,
        "offer_price": data.offer_price,
        "discount_percentage": data.discount_percentage,
        "start_datetime": data.start_datetime.isoformat(),
        "end_datetime": data.end_datetime.isoformat(),
        "max_quantity": data.max_quantity,
        "remaining_quantity": data.max_quantity,
        "max_per_customer": data.max_per_customer,
        "image_url": data.image_url,
        "badge_text": data.badge_text,
        "countdown_enabled": data.countdown_enabled,
        "auto_disable_when_sold_out": data.auto_disable_when_sold_out,
        "active": data.active,
    }
    _limited_offers.append(offer)
    _next_ids["offer"] += 1

    return LimitedTimeOfferResponse(
        id=offer["id"],
        name=offer["name"],
        description=offer["description"],
        menu_item_id=offer["menu_item_id"],
        offer_type=offer["offer_type"],
        original_price=offer["original_price"],
        offer_price=offer["offer_price"],
        discount_percentage=offer["discount_percentage"],
        savings=savings,
        start_datetime=offer["start_datetime"],
        end_datetime=offer["end_datetime"],
        remaining_quantity=offer["remaining_quantity"],
        is_active=offer["active"] and not is_expired,
        is_expired=is_expired,
        time_remaining_seconds=time_remaining,
        badge_text=offer["badge_text"],
    )


@router.get("/limited-offers")
@limiter.limit("60/minute")
def list_limited_offers(
    request: Request,
    active_only: bool = True,
    include_expired: bool = False,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """List limited-time offers."""
    now = datetime.now(timezone.utc)

    result = []
    for offer in _limited_offers:
        end_dt = datetime.fromisoformat(offer["end_datetime"])
        is_expired = now > end_dt
        if not include_expired and is_expired:
            continue
        if active_only and not offer.get("active", True):
            continue

        time_remaining = int((end_dt - now).total_seconds()) if not is_expired else 0

        result.append({
            "id": offer["id"],
            "name": offer["name"],
            "description": offer.get("description"),
            "menu_item_id": offer.get("menu_item_id"),
            "offer_type": offer["offer_type"],
            "original_price": offer.get("original_price"),
            "offer_price": offer.get("offer_price"),
            "discount_percentage": offer.get("discount_percentage"),
            "start_datetime": offer["start_datetime"],
            "end_datetime": offer["end_datetime"],
            "remaining_quantity": offer.get("remaining_quantity"),
            "is_expired": is_expired,
            "is_active": offer.get("active", True) and not is_expired,
            "time_remaining_seconds": time_remaining,
            "badge_text": offer.get("badge_text"),
        })

    return {
        "offers": result,
        "total": len(result),
        "active_count": sum(1 for o in result if o["is_active"]),
        "expiring_soon": sum(1 for o in result if 0 < o["time_remaining_seconds"] < 3600),
    }


# =============================================================================
# 86'd ITEMS (OUT OF STOCK)
# =============================================================================

@router.post("/86", response_model=Item86Response)
@limiter.limit("30/minute")
def mark_item_86(
    request: Request,
    data: Item86Request,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Mark an item as 86'd (out of stock/unavailable)."""
    from app.models.restaurant import MenuItem
    global _next_ids

    item = db.query(MenuItem).filter(MenuItem.id == data.menu_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Check if already 86'd
    for r in _item86_records:
        if r["menu_item_id"] == data.menu_item_id and r["is_active"]:
            raise HTTPException(status_code=400, detail="Item is already 86'd")

    now = datetime.now(timezone.utc)

    record = {
        "id": _next_ids["item86"],
        "menu_item_id": data.menu_item_id,
        "reason": data.reason,
        "notes": data.notes,
        "expected_back": data.expected_back,
        "auto_restore": data.auto_restore,
        "alternative_items": data.alternative_items,
        "notify_staff": data.notify_staff,
        "marked_at": now.isoformat(),
        "marked_by": "Staff",
        "is_active": True,
    }
    _item86_records.append(record)
    _next_ids["item86"] += 1

    # Update item availability
    item.available = False
    db.commit()

    # Get alternatives
    alternatives = []
    if data.alternative_items:
        for alt_id in data.alternative_items:
            alt = db.query(MenuItem).filter(MenuItem.id == alt_id).first()
            if alt:
                alternatives.append({
                    "id": alt.id,
                    "name": alt.name,
                    "price": float(alt.price),
                })

    return Item86Response(
        id=record["id"],
        menu_item_id=data.menu_item_id,
        menu_item_name=item.name,
        reason=record["reason"],
        marked_at=record["marked_at"],
        marked_by=record["marked_by"],
        expected_back=data.expected_back,
        is_active=True,
        alternative_items=alternatives if alternatives else None,
        duration_minutes=0,
    )


@router.get("/86")
@limiter.limit("60/minute")
def list_86_items(
    request: Request,
    active_only: bool = True,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """List all 86'd items."""
    from app.models.restaurant import MenuItem

    now = datetime.now(timezone.utc)

    records = list(_item86_records)
    if active_only:
        records = [r for r in records if r["is_active"]]

    result = []
    for r in records:
        item = db.query(MenuItem).filter(MenuItem.id == r["menu_item_id"]).first()
        marked_at = datetime.fromisoformat(r["marked_at"])
        duration = int((now - marked_at).total_seconds() / 60)

        result.append({
            "id": r["id"],
            "menu_item_id": r["menu_item_id"],
            "menu_item_name": item.name if item else "Unknown",
            "reason": r["reason"],
            "notes": r.get("notes"),
            "marked_at": r["marked_at"],
            "marked_by": r.get("marked_by", "Unknown"),
            "expected_back": r.get("expected_back"),
            "is_active": r["is_active"],
            "duration_minutes": duration,
            "alternative_items": r.get("alternative_items"),
        })

    reasons_count = {}
    for reason in ["sold_out", "ingredient_missing", "equipment_issue", "quality_issue"]:
        reasons_count[reason] = sum(1 for r in result if r["reason"] == reason)

    return {
        "items": result,
        "total_86": len([r for r in result if r["is_active"]]),
        "reasons": reasons_count,
    }


@router.delete("/86/{item86_id}")
@limiter.limit("30/minute")
def restore_86_item(
    request: Request,
    item86_id: int,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Restore an 86'd item (make available again)."""
    from app.models.restaurant import MenuItem

    record = None
    for r in _item86_records:
        if r["id"] == item86_id:
            record = r
            break

    if not record:
        raise HTTPException(status_code=404, detail="86 record not found")

    # Restore item
    item = db.query(MenuItem).filter(MenuItem.id == record["menu_item_id"]).first()
    if item:
        item.available = True

    record["is_active"] = False
    record["restored_at"] = datetime.now(timezone.utc).isoformat()

    db.commit()

    return {"message": "Item restored", "id": item86_id}


# =============================================================================
# DIGITAL MENU BOARD
# =============================================================================

@router.post("/digital-boards")
@limiter.limit("30/minute")
def create_digital_board(
    request: Request,
    data: DigitalMenuBoardCreate,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """Create a digital menu board configuration."""
    from app.models.restaurant import MenuItem
    global _next_ids

    board_token = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc)

    board = {
        "id": _next_ids["board"],
        "name": data.name,
        "token": board_token,
        "display_type": data.display_type,
        "layout": data.layout,
        "columns": data.columns,
        "categories": data.categories,
        "items": data.items,
        "show_prices": data.show_prices,
        "show_descriptions": data.show_descriptions,
        "show_images": data.show_images,
        "show_calories": data.show_calories,
        "show_allergens": data.show_allergens,
        "rotation_seconds": data.rotation_seconds,
        "theme": data.theme,
        "custom_css": data.custom_css,
        "header_text": data.header_text,
        "footer_text": data.footer_text,
        "background_image": data.background_image,
        "auto_hide_unavailable": data.auto_hide_unavailable,
        "active": data.active,
        "created_at": now.isoformat(),
    }
    _digital_boards.append(board)
    _next_ids["board"] += 1

    # Generate URLs
    base_url = "https://menu.bjsbar.com"
    public_url = f"{base_url}/board/{board_token}"
    embed_code = f'<iframe src="{public_url}" width="100%" height="100%" frameborder="0"></iframe>'

    # Generate QR code (try qrcode library, fall back to placeholder)
    qr_code_url = None
    try:
        import qrcode as qr_lib
        qr = qr_lib.QRCode(version=1, box_size=10, border=5)
        qr.add_data(public_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        qr_code_url = f"data:image/png;base64,{qr_base64}"
    except ImportError:
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={public_url}"

    # Count items
    items_count = 0
    if data.items:
        items_count = len(data.items)
    elif data.categories:
        for cat in data.categories:
            items_count += db.query(MenuItem).filter(MenuItem.category == cat).count()
    else:
        items_count = db.query(MenuItem).count()

    return {
        "id": board["id"],
        "name": data.name,
        "display_type": data.display_type,
        "layout": data.layout,
        "token": board_token,
        "public_url": public_url,
        "embed_code": embed_code,
        "qr_code_url": qr_code_url,
        "items_count": items_count,
        "active": data.active,
        "created_at": board["created_at"],
    }


@router.get("/digital-boards")
@limiter.limit("60/minute")
def list_digital_boards(
    request: Request,
    db: DbSession,
    current_user: CurrentUser = None,
):
    """List all digital menu boards."""
    base_url = "https://menu.bjsbar.com"

    result = []
    for board in _digital_boards:
        result.append({
            "id": board["id"],
            "name": board["name"],
            "display_type": board.get("display_type", "full_menu"),
            "layout": board.get("layout", "grid"),
            "public_url": f"{base_url}/board/{board['token']}",
            "active": board.get("active", True),
            "last_updated": board.get("created_at"),
        })

    return {"boards": result, "total": len(result)}


@router.get("/digital-boards/{board_id}/content")
@limiter.limit("60/minute")
def get_digital_board_content(
    request: Request,
    board_id: int,
    language: str = "en",
    db: DbSession = None,
):
    """Get content for a digital menu board (public endpoint)."""
    from app.models.restaurant import MenuItem

    board = None
    for b in _digital_boards:
        if b["id"] == board_id:
            board = b
            break

    if not board:
        raise HTTPException(status_code=404, detail="Board not found")

    if not board.get("active", True):
        raise HTTPException(status_code=404, detail="Board is inactive")

    # Get menu items
    query = db.query(MenuItem)

    if board.get("items"):
        query = query.filter(MenuItem.id.in_(board["items"]))
    elif board.get("categories"):
        query = query.filter(MenuItem.category.in_(board["categories"]))

    if board.get("auto_hide_unavailable", True):
        query = query.filter(MenuItem.available == True)

    items = query.all()

    formatted_items = []
    for item in items:
        item_data = {
            "id": item.id,
            "name": item.name,
            "price": float(item.price),
            "available": item.available,
        }

        if board.get("show_descriptions", True) and item.description:
            item_data["description"] = item.description

        if board.get("show_allergens", True) and item.allergens:
            item_data["allergens"] = item.allergens

        formatted_items.append(item_data)

    return {
        "board_id": board_id,
        "name": board["name"],
        "layout": board.get("layout", "grid"),
        "columns": board.get("columns", 3),
        "theme": board.get("theme", "dark"),
        "header_text": board.get("header_text"),
        "footer_text": board.get("footer_text"),
        "background_image": board.get("background_image"),
        "rotation_seconds": board.get("rotation_seconds", 10),
        "items": formatted_items,
        "total_items": len(formatted_items),
        "last_updated": board.get("created_at"),
    }


# =============================================================================
# MENU ENGINEERING ANALYTICS
# =============================================================================

@router.get("/engineering/report", response_model=MenuEngineeringReport)
@limiter.limit("60/minute")
def get_menu_engineering_report(
    request: Request,
    period_days: int = 30,
    category: Optional[str] = None,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """
    Generate a menu engineering report.

    Classifies items into:
    - Stars: High popularity, high profit
    - Puzzles: Low popularity, high profit
    - Plow Horses: High popularity, low profit
    - Dogs: Low popularity, low profit
    """
    from app.models.restaurant import MenuItem, Check, CheckItem

    period_end = date.today()
    period_start = period_end - timedelta(days=period_days)

    # Get items
    items_query = db.query(MenuItem)
    if category:
        items_query = items_query.filter(MenuItem.category == category)

    items = items_query.all()

    # Calculate metrics
    item_metrics = []
    total_revenue = 0.0
    total_profit = 0.0
    total_quantity = 0

    for item in items:
        # Get actual sales data from check_items
        sales = db.query(
            func.coalesce(func.sum(CheckItem.quantity), 0).label("quantity"),
            func.coalesce(func.sum(CheckItem.total), 0).label("revenue"),
        ).join(Check).filter(
            CheckItem.menu_item_id == item.id,
            Check.opened_at >= datetime.combine(period_start, datetime.min.time()),
            Check.status != "voided",
            CheckItem.status != "voided",
        ).first()

        quantity_sold = int(sales.quantity or 0)
        revenue = float(sales.revenue or 0)

        # Estimate cost (35% food cost if not specified)
        cost_per_item = float(item.base_price) if item.base_price else float(item.price) * 0.35

        # Check for variants with cost
        variant_costs = [v["cost"] for v in _variants if v["menu_item_id"] == item.id and v.get("cost")]
        if variant_costs:
            cost_per_item = variant_costs[0]

        profit = revenue - (cost_per_item * quantity_sold)
        profit_margin = (float(item.price) - cost_per_item) / float(item.price) * 100 if item.price and float(item.price) > 0 else 0

        total_revenue += revenue
        total_profit += profit
        total_quantity += quantity_sold

        item_metrics.append({
            "menu_item_id": item.id,
            "name": item.name,
            "category": item.category or "Uncategorized",
            "price": float(item.price),
            "cost": round(cost_per_item, 2),
            "profit_margin": round(profit_margin, 1),
            "profit_margin_percentage": round(profit_margin, 1),
            "quantity_sold": quantity_sold,
            "revenue": round(revenue, 2),
            "profit": round(profit, 2),
        })

    # Calculate averages
    if item_metrics:
        avg_quantity = total_quantity / len(item_metrics) if len(item_metrics) > 0 else 1
        avg_profit_margin = sum(i["profit_margin"] for i in item_metrics) / len(item_metrics)
    else:
        avg_quantity = 1
        avg_profit_margin = 0

    # Classify items
    stars = []
    puzzles = []
    plow_horses = []
    dogs = []

    for item in item_metrics:
        popularity_index = item["quantity_sold"] / max(avg_quantity, 1)
        profitability_index = item["profit_margin"] / max(avg_profit_margin, 1)

        item["popularity_index"] = round(popularity_index, 2)
        item["profitability_index"] = round(profitability_index, 2)
        item["trend"] = "stable"

        high_popularity = popularity_index >= 1.0
        high_profit = profitability_index >= 1.0

        if high_popularity and high_profit:
            item["classification"] = "star"
            item["recommendation"] = "Maintain quality, feature prominently"
            stars.append(MenuEngineeringItem(**item))
        elif not high_popularity and high_profit:
            item["classification"] = "puzzle"
            item["recommendation"] = "Increase visibility, add to promotions"
            puzzles.append(MenuEngineeringItem(**item))
        elif high_popularity and not high_profit:
            item["classification"] = "plow_horse"
            item["recommendation"] = "Reengineer recipe to reduce cost"
            plow_horses.append(MenuEngineeringItem(**item))
        else:
            item["classification"] = "dog"
            item["recommendation"] = "Consider removing or major repositioning"
            dogs.append(MenuEngineeringItem(**item))

    # Generate recommendations
    recommendations = []
    if stars:
        recommendations.append({"type": "maintain", "message": f"{len(stars)} star items performing well"})
    if puzzles:
        recommendations.append({"type": "promote", "message": f"{len(puzzles)} puzzle items need more visibility"})
    if plow_horses:
        recommendations.append({"type": "optimize", "message": f"{len(plow_horses)} items could benefit from cost optimization"})
    if dogs:
        recommendations.append({"type": "review", "message": f"{len(dogs)} items should be reviewed for removal"})

    return MenuEngineeringReport(
        period_start=str(period_start),
        period_end=str(period_end),
        total_items=len(item_metrics),
        total_revenue=round(total_revenue, 2),
        total_profit=round(total_profit, 2),
        average_profit_margin=round(avg_profit_margin, 1),
        stars=stars,
        puzzles=puzzles,
        plow_horses=plow_horses,
        dogs=dogs,
        recommendations=recommendations,
    )


# =============================================================================
# QR CODE MENU GENERATION
# =============================================================================

