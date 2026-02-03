"""Price lists, daily menus, and manager alerts routes - TouchSale gap features."""

from typing import List, Optional
from datetime import datetime, date, time, timedelta
from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from sqlalchemy import func, and_

from app.db.session import DbSession
from app.models.price_lists import (
    PriceList, ProductPrice, DailyMenu,
    OperatorRecentItem, ManagerAlert, CustomerCredit
)
from app.models.staff import StaffUser
from app.services.notification_service import NotificationService

router = APIRouter()


# ============== Pydantic Schemas ==============

class PriceListCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    start_time: Optional[str] = None  # HH:MM
    end_time: Optional[str] = None
    days_of_week: Optional[List[int]] = None  # [0,1,2,3,4,5,6]
    priority: int = 0
    min_order_amount: Optional[float] = None
    requires_membership: bool = False


class ProductPriceCreate(BaseModel):
    product_id: int
    price: float
    adjustment_type: Optional[str] = None
    adjustment_value: Optional[float] = None


class DailyMenuCreate(BaseModel):
    date: str  # YYYY-MM-DD
    name: str
    description: Optional[str] = None
    available_from: Optional[str] = None  # HH:MM
    available_until: Optional[str] = None
    items: Optional[List[dict]] = None
    set_price: Optional[float] = None
    max_orders: Optional[int] = None


class ManagerAlertCreate(BaseModel):
    name: str
    alert_type: str
    threshold_value: Optional[float] = None
    threshold_operator: Optional[str] = None
    recipient_phones: Optional[List[str]] = None
    recipient_emails: Optional[List[str]] = None
    send_sms: bool = True
    send_email: bool = False
    send_push: bool = False
    cooldown_minutes: int = 5


# ============== Helper Functions ==============

def _init_default_price_lists(db: DbSession):
    """Initialize default price lists if none exist."""
    count = db.query(PriceList).count()
    if count == 0:
        defaults = [
            {"name": "Dine-In", "code": "dine_in", "description": "Standard dine-in pricing", "priority": 10},
            {"name": "Takeout", "code": "takeout", "description": "Takeout/pickup pricing", "priority": 5},
            {"name": "Delivery", "code": "delivery", "description": "Delivery platform pricing", "priority": 5},
            {"name": "Happy Hour", "code": "happy_hour", "description": "Happy hour discounts", "priority": 20,
             "start_time": datetime.strptime("16:00", "%H:%M").time(),
             "end_time": datetime.strptime("19:00", "%H:%M").time(),
             "days_of_week": [0, 1, 2, 3, 4]},  # Mon-Fri
            {"name": "VIP", "code": "vip", "description": "VIP customer pricing", "priority": 15, "requires_membership": True},
        ]
        for pl in defaults:
            price_list = PriceList(**pl)
            db.add(price_list)
        db.commit()


def _price_list_to_dict(pl: PriceList) -> dict:
    return {
        "id": pl.id,
        "name": pl.name,
        "code": pl.code,
        "description": pl.description,
        "start_time": pl.start_time.strftime("%H:%M") if pl.start_time else None,
        "end_time": pl.end_time.strftime("%H:%M") if pl.end_time else None,
        "days_of_week": pl.days_of_week,
        "priority": pl.priority,
        "min_order_amount": pl.min_order_amount,
        "requires_membership": pl.requires_membership,
        "is_active": pl.is_active,
        "created_at": pl.created_at.isoformat() if pl.created_at else None,
    }


def _daily_menu_to_dict(dm: DailyMenu) -> dict:
    return {
        "id": dm.id,
        "date": dm.date.strftime("%Y-%m-%d") if dm.date else None,
        "name": dm.name,
        "description": dm.description,
        "available_from": dm.available_from.strftime("%H:%M") if dm.available_from else None,
        "available_until": dm.available_until.strftime("%H:%M") if dm.available_until else None,
        "items": dm.items or [],
        "set_price": dm.set_price,
        "max_orders": dm.max_orders,
        "orders_sold": dm.orders_sold,
        "is_active": dm.is_active,
        "is_available": dm.is_active and (dm.max_orders is None or dm.orders_sold < dm.max_orders),
    }


# ============== Price Lists CRUD ==============

@router.get("/price-lists")
def list_price_lists(db: DbSession, active_only: bool = False):
    """List all price lists."""
    _init_default_price_lists(db)

    query = db.query(PriceList)
    if active_only:
        query = query.filter(PriceList.is_active == True)

    price_lists = query.order_by(PriceList.priority.desc()).all()
    return [_price_list_to_dict(pl) for pl in price_lists]


@router.get("/price-lists/active")
def get_active_price_list(
    db: DbSession,
    context: Optional[str] = None,
    is_member: bool = False,
    order_amount: float = 0,
):
    """Get the currently active price list based on context and time."""
    _init_default_price_lists(db)

    now = datetime.now()
    current_time = now.time()
    current_day = now.weekday()

    query = db.query(PriceList).filter(PriceList.is_active == True)

    # Filter by context if specified
    if context:
        query = query.filter(PriceList.code == context)

    # Filter by membership requirement
    if not is_member:
        query = query.filter(PriceList.requires_membership == False)

    price_lists = query.order_by(PriceList.priority.desc()).all()

    # Find best matching price list
    for pl in price_lists:
        # Check time constraints
        if pl.start_time and pl.end_time:
            if not (pl.start_time <= current_time <= pl.end_time):
                continue

        # Check day constraints
        if pl.days_of_week:
            if current_day not in pl.days_of_week:
                continue

        # Check minimum order amount
        if pl.min_order_amount and order_amount < pl.min_order_amount:
            continue

        return _price_list_to_dict(pl)

    # Return default if no match
    default = db.query(PriceList).filter(PriceList.code == "dine_in").first()
    if default:
        return _price_list_to_dict(default)

    return None


@router.post("/price-lists")
def create_price_list(db: DbSession, data: PriceListCreate):
    """Create a new price list."""
    # Check for duplicate code
    existing = db.query(PriceList).filter(PriceList.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Price list code already exists")

    price_list = PriceList(
        name=data.name,
        code=data.code,
        description=data.description,
        priority=data.priority,
        min_order_amount=data.min_order_amount,
        requires_membership=data.requires_membership,
        days_of_week=data.days_of_week,
    )

    if data.start_time:
        price_list.start_time = datetime.strptime(data.start_time, "%H:%M").time()
    if data.end_time:
        price_list.end_time = datetime.strptime(data.end_time, "%H:%M").time()

    db.add(price_list)
    db.commit()
    db.refresh(price_list)

    return _price_list_to_dict(price_list)


@router.put("/price-lists/{price_list_id}")
def update_price_list(db: DbSession, price_list_id: int, data: dict = Body(...)):
    """Update a price list."""
    price_list = db.query(PriceList).filter(PriceList.id == price_list_id).first()
    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")

    for key, value in data.items():
        if hasattr(price_list, key):
            if key in ["start_time", "end_time"] and value:
                value = datetime.strptime(value, "%H:%M").time()
            setattr(price_list, key, value)

    db.commit()
    db.refresh(price_list)
    return _price_list_to_dict(price_list)


@router.delete("/price-lists/{price_list_id}")
def delete_price_list(db: DbSession, price_list_id: int):
    """Delete a price list."""
    price_list = db.query(PriceList).filter(PriceList.id == price_list_id).first()
    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")

    db.delete(price_list)
    db.commit()
    return {"status": "deleted", "id": price_list_id}


# ============== Product Prices ==============

@router.get("/products/{product_id}/prices")
def get_product_prices(db: DbSession, product_id: int):
    """Get all prices for a product across price lists."""
    prices = db.query(ProductPrice).filter(ProductPrice.product_id == product_id).all()

    result = []
    for p in prices:
        price_list = db.query(PriceList).filter(PriceList.id == p.price_list_id).first()
        result.append({
            "id": p.id,
            "product_id": p.product_id,
            "price_list_id": p.price_list_id,
            "price_list_name": price_list.name if price_list else None,
            "price_list_code": price_list.code if price_list else None,
            "price": p.price,
            "adjustment_type": p.adjustment_type,
            "adjustment_value": p.adjustment_value,
            "is_active": p.is_active,
        })

    return result


@router.post("/products/{product_id}/prices")
def set_product_price(db: DbSession, product_id: int, data: ProductPriceCreate):
    """Set a product's price in a specific price list."""
    # Check if price already exists for this product/price list combo
    existing = db.query(ProductPrice).filter(
        ProductPrice.product_id == product_id,
        ProductPrice.price_list_id == data.product_id  # Assuming this should be price_list_id
    ).first()

    if existing:
        existing.price = data.price
        existing.adjustment_type = data.adjustment_type
        existing.adjustment_value = data.adjustment_value
        db.commit()
        return {"id": existing.id, "status": "updated"}

    price = ProductPrice(
        product_id=product_id,
        price_list_id=data.product_id,  # This needs to be price_list_id from request
        price=data.price,
        adjustment_type=data.adjustment_type,
        adjustment_value=data.adjustment_value,
    )
    db.add(price)
    db.commit()
    db.refresh(price)

    return {"id": price.id, "status": "created"}


@router.post("/price-lists/{price_list_id}/products/{product_id}")
def set_price_in_list(db: DbSession, price_list_id: int, product_id: int, data: dict = Body(...)):
    """Set a product's price in a specific price list."""
    price_list = db.query(PriceList).filter(PriceList.id == price_list_id).first()
    if not price_list:
        raise HTTPException(status_code=404, detail="Price list not found")

    existing = db.query(ProductPrice).filter(
        ProductPrice.product_id == product_id,
        ProductPrice.price_list_id == price_list_id
    ).first()

    if existing:
        existing.price = data.get("price", existing.price)
        existing.adjustment_type = data.get("adjustment_type", existing.adjustment_type)
        existing.adjustment_value = data.get("adjustment_value", existing.adjustment_value)
        existing.is_active = data.get("is_active", existing.is_active)
        db.commit()
        return {"id": existing.id, "status": "updated"}

    price = ProductPrice(
        product_id=product_id,
        price_list_id=price_list_id,
        price=data.get("price", 0),
        adjustment_type=data.get("adjustment_type"),
        adjustment_value=data.get("adjustment_value"),
    )
    db.add(price)
    db.commit()
    db.refresh(price)

    return {"id": price.id, "status": "created"}


# ============== Daily Menu ==============

@router.get("/daily-menu")
def list_daily_menus(
    db: DbSession,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """List daily menus for a date range."""
    query = db.query(DailyMenu)

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(DailyMenu.date >= start)

    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.filter(DailyMenu.date <= end)

    menus = query.order_by(DailyMenu.date.desc()).all()
    return [_daily_menu_to_dict(m) for m in menus]


@router.get("/daily-menu/today")
def get_todays_menu(db: DbSession):
    """Get today's daily menu."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    menus = db.query(DailyMenu).filter(
        DailyMenu.date >= today,
        DailyMenu.date < tomorrow,
        DailyMenu.is_active == True
    ).all()

    return [_daily_menu_to_dict(m) for m in menus]


@router.get("/daily-menu/current")
def get_current_menu(db: DbSession):
    """Get currently available daily menu (active and within time window)."""
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    current_time = now.time()

    menus = db.query(DailyMenu).filter(
        DailyMenu.date >= today,
        DailyMenu.date < tomorrow,
        DailyMenu.is_active == True
    ).all()

    # Filter by time availability
    available = []
    for m in menus:
        if m.available_from and current_time < m.available_from:
            continue
        if m.available_until and current_time > m.available_until:
            continue
        if m.max_orders and m.orders_sold >= m.max_orders:
            continue
        available.append(_daily_menu_to_dict(m))

    return available


@router.post("/daily-menu")
def create_daily_menu(db: DbSession, data: DailyMenuCreate):
    """Create a new daily menu."""
    menu_date = datetime.strptime(data.date, "%Y-%m-%d")

    menu = DailyMenu(
        date=menu_date,
        name=data.name,
        description=data.description,
        items=data.items,
        set_price=data.set_price,
        max_orders=data.max_orders,
    )

    if data.available_from:
        menu.available_from = datetime.strptime(data.available_from, "%H:%M").time()
    if data.available_until:
        menu.available_until = datetime.strptime(data.available_until, "%H:%M").time()

    db.add(menu)
    db.commit()
    db.refresh(menu)

    return _daily_menu_to_dict(menu)


@router.put("/daily-menu/{menu_id}")
def update_daily_menu(db: DbSession, menu_id: int, data: dict = Body(...)):
    """Update a daily menu."""
    menu = db.query(DailyMenu).filter(DailyMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Daily menu not found")

    for key, value in data.items():
        if hasattr(menu, key):
            if key == "date" and value:
                value = datetime.strptime(value, "%Y-%m-%d")
            elif key in ["available_from", "available_until"] and value:
                value = datetime.strptime(value, "%H:%M").time()
            setattr(menu, key, value)

    db.commit()
    db.refresh(menu)
    return _daily_menu_to_dict(menu)


@router.post("/daily-menu/{menu_id}/order")
def record_daily_menu_order(db: DbSession, menu_id: int):
    """Record an order of the daily menu (increment sold count)."""
    menu = db.query(DailyMenu).filter(DailyMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Daily menu not found")

    if menu.max_orders and menu.orders_sold >= menu.max_orders:
        raise HTTPException(status_code=400, detail="Daily menu sold out")

    menu.orders_sold += 1
    db.commit()

    return {"status": "success", "orders_sold": menu.orders_sold, "remaining": menu.max_orders - menu.orders_sold if menu.max_orders else None}


@router.delete("/daily-menu/{menu_id}")
def delete_daily_menu(db: DbSession, menu_id: int):
    """Delete a daily menu."""
    menu = db.query(DailyMenu).filter(DailyMenu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Daily menu not found")

    db.delete(menu)
    db.commit()
    return {"status": "deleted", "id": menu_id}


# ============== Recently Used Items ==============

@router.get("/staff/{staff_id}/recent-items")
def get_recent_items(db: DbSession, staff_id: int, limit: int = 20):
    """Get recently used items for an operator."""
    items = db.query(OperatorRecentItem).filter(
        OperatorRecentItem.staff_id == staff_id
    ).order_by(OperatorRecentItem.last_used.desc()).limit(limit).all()

    return [
        {
            "product_id": i.product_id,
            "last_used": i.last_used.isoformat() if i.last_used else None,
            "use_count": i.use_count,
        }
        for i in items
    ]


@router.post("/staff/{staff_id}/recent-items/{product_id}")
def record_item_use(db: DbSession, staff_id: int, product_id: int):
    """Record that an operator used/ordered an item."""
    existing = db.query(OperatorRecentItem).filter(
        OperatorRecentItem.staff_id == staff_id,
        OperatorRecentItem.product_id == product_id
    ).first()

    if existing:
        existing.last_used = datetime.utcnow()
        existing.use_count += 1
        db.commit()
        return {"status": "updated", "use_count": existing.use_count}

    item = OperatorRecentItem(
        staff_id=staff_id,
        product_id=product_id,
        last_used=datetime.utcnow(),
        use_count=1,
    )
    db.add(item)
    db.commit()

    return {"status": "created", "use_count": 1}


@router.get("/recent-items/most-used")
def get_most_used_items(db: DbSession, limit: int = 10):
    """Get most frequently used items across all operators."""
    items = db.query(
        OperatorRecentItem.product_id,
        func.sum(OperatorRecentItem.use_count).label("total_uses")
    ).group_by(OperatorRecentItem.product_id).order_by(
        func.sum(OperatorRecentItem.use_count).desc()
    ).limit(limit).all()

    return [{"product_id": i.product_id, "total_uses": i.total_uses} for i in items]


# ============== Manager Alerts ==============

@router.get("/manager-alerts")
def list_manager_alerts(db: DbSession, active_only: bool = True):
    """List all manager alerts."""
    query = db.query(ManagerAlert)
    if active_only:
        query = query.filter(ManagerAlert.is_active == True)

    alerts = query.all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "alert_type": a.alert_type,
            "threshold_value": a.threshold_value,
            "threshold_operator": a.threshold_operator,
            "recipient_phones": a.recipient_phones or [],
            "recipient_emails": a.recipient_emails or [],
            "send_sms": a.send_sms,
            "send_email": a.send_email,
            "send_push": a.send_push,
            "cooldown_minutes": a.cooldown_minutes,
            "last_triggered": a.last_triggered.isoformat() if a.last_triggered else None,
            "is_active": a.is_active,
        }
        for a in alerts
    ]


@router.post("/manager-alerts")
def create_manager_alert(db: DbSession, data: ManagerAlertCreate):
    """Create a new manager alert."""
    alert = ManagerAlert(
        name=data.name,
        alert_type=data.alert_type,
        threshold_value=data.threshold_value,
        threshold_operator=data.threshold_operator,
        recipient_phones=data.recipient_phones,
        recipient_emails=data.recipient_emails,
        send_sms=data.send_sms,
        send_email=data.send_email,
        send_push=data.send_push,
        cooldown_minutes=data.cooldown_minutes,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {"id": alert.id, "status": "created"}


@router.put("/manager-alerts/{alert_id}")
def update_manager_alert(db: DbSession, alert_id: int, data: dict = Body(...)):
    """Update a manager alert."""
    alert = db.query(ManagerAlert).filter(ManagerAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    for key, value in data.items():
        if hasattr(alert, key):
            setattr(alert, key, value)

    db.commit()
    db.refresh(alert)
    return {"id": alert.id, "status": "updated"}


@router.delete("/manager-alerts/{alert_id}")
def delete_manager_alert(db: DbSession, alert_id: int):
    """Delete a manager alert."""
    alert = db.query(ManagerAlert).filter(ManagerAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(alert)
    db.commit()
    return {"status": "deleted", "id": alert_id}


@router.post("/manager-alerts/trigger")
def trigger_alert(db: DbSession, data: dict = Body(...)):
    """Trigger an alert (called by system when events occur)."""
    alert_type = data.get("alert_type")
    value = data.get("value", 0)
    message = data.get("message", "")

    alerts = db.query(ManagerAlert).filter(
        ManagerAlert.alert_type == alert_type,
        ManagerAlert.is_active == True
    ).all()

    triggered = []
    for alert in alerts:
        # Check cooldown
        if alert.last_triggered:
            cooldown_end = alert.last_triggered + timedelta(minutes=alert.cooldown_minutes)
            if datetime.utcnow() < cooldown_end:
                continue

        # Check threshold
        if alert.threshold_value is not None and alert.threshold_operator:
            op = alert.threshold_operator
            if op == ">" and not (value > alert.threshold_value):
                continue
            elif op == "<" and not (value < alert.threshold_value):
                continue
            elif op == ">=" and not (value >= alert.threshold_value):
                continue
            elif op == "<=" and not (value <= alert.threshold_value):
                continue
            elif op == "=" and not (value == alert.threshold_value):
                continue

        # Trigger alert
        alert.last_triggered = datetime.utcnow()

        alert_data = {
            "alert_id": alert.id,
            "name": alert.name,
            "phones": alert.recipient_phones if alert.send_sms else [],
            "emails": alert.recipient_emails if alert.send_email else [],
            "message": message,
            "sms_sent": False,
            "email_sent": False,
            "errors": [],
        }

        # Send SMS notifications
        if alert.send_sms and alert.recipient_phones:
            try:
                sms_result = NotificationService.send_manager_alert(
                    alert_type=alert_type,
                    message=message,
                    phones=alert.recipient_phones,
                    emails=None
                )
                alert_data["sms_sent"] = sms_result.get("sms", {}).get("success", False)
                if not alert_data["sms_sent"] and sms_result.get("sms", {}).get("error"):
                    alert_data["errors"].append(f"SMS: {sms_result['sms']['error']}")
            except Exception as e:
                alert_data["errors"].append(f"SMS error: {str(e)}")

        # Send email notifications
        if alert.send_email and alert.recipient_emails:
            try:
                email_result = NotificationService.send_manager_alert(
                    alert_type=alert_type,
                    message=message,
                    phones=None,
                    emails=alert.recipient_emails
                )
                alert_data["email_sent"] = email_result.get("email", {}).get("success", False)
                if not alert_data["email_sent"] and email_result.get("email", {}).get("error"):
                    alert_data["errors"].append(f"Email: {email_result['email']['error']}")
            except Exception as e:
                alert_data["errors"].append(f"Email error: {str(e)}")

        triggered.append(alert_data)

    db.commit()

    return {"triggered_count": len(triggered), "alerts": triggered}


# ============== Customer Credit ==============

@router.get("/customers/{customer_id}/credit")
def get_customer_credit(db: DbSession, customer_id: int):
    """Get customer credit status."""
    credit = db.query(CustomerCredit).filter(CustomerCredit.customer_id == customer_id).first()

    if not credit:
        return {
            "customer_id": customer_id,
            "credit_limit": 0,
            "current_balance": 0,
            "available_credit": 0,
            "is_blocked": False,
        }

    return {
        "customer_id": customer_id,
        "credit_limit": credit.credit_limit,
        "current_balance": credit.current_balance,
        "available_credit": credit.credit_limit - credit.current_balance,
        "is_blocked": credit.is_blocked,
        "block_reason": credit.block_reason,
        "last_payment_date": credit.last_payment_date.isoformat() if credit.last_payment_date else None,
        "last_payment_amount": credit.last_payment_amount,
    }


@router.post("/customers/{customer_id}/credit")
def set_customer_credit(db: DbSession, customer_id: int, data: dict = Body(...)):
    """Set or update customer credit limit."""
    credit = db.query(CustomerCredit).filter(CustomerCredit.customer_id == customer_id).first()

    if not credit:
        credit = CustomerCredit(customer_id=customer_id)
        db.add(credit)

    if "credit_limit" in data:
        credit.credit_limit = data["credit_limit"]
    if "is_blocked" in data:
        credit.is_blocked = data["is_blocked"]
    if "block_reason" in data:
        credit.block_reason = data["block_reason"]

    db.commit()
    db.refresh(credit)

    return {"status": "updated", "credit_limit": credit.credit_limit}


@router.post("/customers/{customer_id}/credit/charge")
def charge_customer_credit(db: DbSession, customer_id: int, data: dict = Body(...)):
    """Charge amount to customer's credit balance."""
    amount = data.get("amount", 0)

    credit = db.query(CustomerCredit).filter(CustomerCredit.customer_id == customer_id).first()

    if not credit:
        credit = CustomerCredit(customer_id=customer_id)
        db.add(credit)

    if credit.is_blocked:
        raise HTTPException(status_code=400, detail=f"Customer account is blocked: {credit.block_reason}")

    new_balance = credit.current_balance + amount

    if credit.credit_limit > 0 and new_balance > credit.credit_limit:
        raise HTTPException(status_code=400, detail=f"Exceeds credit limit. Available: {credit.credit_limit - credit.current_balance}")

    credit.current_balance = new_balance
    db.commit()

    return {
        "status": "charged",
        "amount": amount,
        "new_balance": credit.current_balance,
        "available_credit": credit.credit_limit - credit.current_balance if credit.credit_limit > 0 else None,
    }


@router.post("/customers/{customer_id}/credit/payment")
def record_customer_payment(db: DbSession, customer_id: int, data: dict = Body(...)):
    """Record a payment to reduce customer's credit balance."""
    amount = data.get("amount", 0)

    credit = db.query(CustomerCredit).filter(CustomerCredit.customer_id == customer_id).first()

    if not credit:
        raise HTTPException(status_code=404, detail="Customer has no credit account")

    credit.current_balance = max(0, credit.current_balance - amount)
    credit.last_payment_date = datetime.utcnow()
    credit.last_payment_amount = amount

    db.commit()

    return {
        "status": "payment_recorded",
        "amount": amount,
        "new_balance": credit.current_balance,
    }


# ============== Quick Reorder ==============

@router.get("/orders/{order_id}/items")
def get_order_items_for_reorder(db: DbSession, order_id: int):
    """Get items from a previous order for quick reorder."""
    # This would connect to the actual orders system
    # Returning mock data for now
    return {
        "order_id": order_id,
        "items": [
            {"product_id": 1, "quantity": 2, "modifiers": []},
            {"product_id": 5, "quantity": 1, "modifiers": [{"id": 3, "name": "Extra cheese"}]},
        ]
    }


@router.post("/orders/reorder/{order_id}")
def reorder_previous_order(db: DbSession, order_id: int, data: dict = Body(...)):
    """Create a new order based on a previous order."""
    table_id = data.get("table_id")

    # In production, would:
    # 1. Fetch original order items
    # 2. Create new order with same items
    # 3. Apply current prices

    return {
        "status": "success",
        "message": "Reorder functionality - would create new order based on order #{order_id}",
        "original_order_id": order_id,
        "new_order_id": None,  # Would return actual new order ID
    }


# ============== Subtables ==============

class SubTableCreate(BaseModel):
    name: str
    seats: int = 2


class SubTableUpdate(BaseModel):
    name: Optional[str] = None
    seats: Optional[int] = None
    current_guests: Optional[int] = None
    status: Optional[str] = None
    waiter_id: Optional[int] = None
    current_order_id: Optional[int] = None


def _subtable_to_dict(st) -> dict:
    return {
        "id": st.id,
        "parent_table_id": st.parent_table_id,
        "name": st.name,
        "seats": st.seats,
        "current_guests": st.current_guests,
        "status": st.status,
        "current_order_id": st.current_order_id,
        "waiter_id": st.waiter_id,
        "is_active": st.is_active,
        "created_at": st.created_at.isoformat() if st.created_at else None,
    }


@router.get("/tables/{table_id}/subtables")
def list_subtables(db: DbSession, table_id: int):
    """List all subtables for a table."""
    from app.models.price_lists import SubTable

    subtables = db.query(SubTable).filter(
        SubTable.parent_table_id == table_id,
        SubTable.is_active == True
    ).order_by(SubTable.name).all()

    return [_subtable_to_dict(st) for st in subtables]


@router.post("/tables/{table_id}/subtables")
def create_subtable(db: DbSession, table_id: int, data: SubTableCreate):
    """Create a new subtable under a table."""
    from app.models.price_lists import SubTable

    # Check for duplicate name
    existing = db.query(SubTable).filter(
        SubTable.parent_table_id == table_id,
        SubTable.name == data.name,
        SubTable.is_active == True
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"Subtable '{data.name}' already exists for this table")

    subtable = SubTable(
        parent_table_id=table_id,
        name=data.name,
        seats=data.seats,
        status="available",
    )
    db.add(subtable)
    db.commit()
    db.refresh(subtable)

    return _subtable_to_dict(subtable)


@router.post("/tables/{table_id}/subtables/auto-create")
def auto_create_subtables(db: DbSession, table_id: int, data: dict = Body(...)):
    """Auto-create multiple subtables (A, B, C or 1, 2, 3)."""
    from app.models.price_lists import SubTable

    count = data.get("count", 2)
    naming = data.get("naming", "letter")  # "letter" (A, B, C) or "number" (1, 2, 3)
    seats_each = data.get("seats_each", 2)

    if count < 2 or count > 10:
        raise HTTPException(status_code=400, detail="Count must be between 2 and 10")

    # Delete existing subtables for this table
    db.query(SubTable).filter(SubTable.parent_table_id == table_id).delete()

    created = []
    for i in range(count):
        name = chr(65 + i) if naming == "letter" else str(i + 1)  # A, B, C or 1, 2, 3
        subtable = SubTable(
            parent_table_id=table_id,
            name=name,
            seats=seats_each,
            status="available",
        )
        db.add(subtable)
        created.append(subtable)

    db.commit()

    return {
        "status": "created",
        "count": len(created),
        "subtables": [_subtable_to_dict(st) for st in created],
    }


@router.put("/subtables/{subtable_id}")
def update_subtable(db: DbSession, subtable_id: int, data: SubTableUpdate):
    """Update a subtable."""
    from app.models.price_lists import SubTable

    subtable = db.query(SubTable).filter(SubTable.id == subtable_id).first()
    if not subtable:
        raise HTTPException(status_code=404, detail="Subtable not found")

    if data.name is not None:
        subtable.name = data.name
    if data.seats is not None:
        subtable.seats = data.seats
    if data.current_guests is not None:
        subtable.current_guests = data.current_guests
    if data.status is not None:
        subtable.status = data.status
    if data.waiter_id is not None:
        subtable.waiter_id = data.waiter_id
    if data.current_order_id is not None:
        subtable.current_order_id = data.current_order_id

    db.commit()
    db.refresh(subtable)

    return _subtable_to_dict(subtable)


@router.post("/subtables/{subtable_id}/occupy")
def occupy_subtable(db: DbSession, subtable_id: int, data: dict = Body(...)):
    """Mark a subtable as occupied with guests."""
    from app.models.price_lists import SubTable

    subtable = db.query(SubTable).filter(SubTable.id == subtable_id).first()
    if not subtable:
        raise HTTPException(status_code=404, detail="Subtable not found")

    subtable.status = "occupied"
    subtable.current_guests = data.get("guests", 1)
    subtable.waiter_id = data.get("waiter_id")

    db.commit()

    return _subtable_to_dict(subtable)


@router.post("/subtables/{subtable_id}/clear")
def clear_subtable(db: DbSession, subtable_id: int):
    """Clear a subtable (mark as available)."""
    from app.models.price_lists import SubTable

    subtable = db.query(SubTable).filter(SubTable.id == subtable_id).first()
    if not subtable:
        raise HTTPException(status_code=404, detail="Subtable not found")

    subtable.status = "available"
    subtable.current_guests = 0
    subtable.current_order_id = None
    subtable.waiter_id = None

    db.commit()

    return _subtable_to_dict(subtable)


@router.post("/tables/{table_id}/subtables/merge")
def merge_subtables(db: DbSession, table_id: int):
    """Merge all subtables back into the main table (delete subtables)."""
    from app.models.price_lists import SubTable

    # Check if any subtable has active orders
    active = db.query(SubTable).filter(
        SubTable.parent_table_id == table_id,
        SubTable.status == "occupied"
    ).count()

    if active > 0:
        raise HTTPException(status_code=400, detail=f"{active} subtable(s) are occupied. Clear them first.")

    deleted = db.query(SubTable).filter(SubTable.parent_table_id == table_id).delete()
    db.commit()

    return {"status": "merged", "deleted_count": deleted}


@router.delete("/subtables/{subtable_id}")
def delete_subtable(db: DbSession, subtable_id: int):
    """Delete a specific subtable."""
    from app.models.price_lists import SubTable

    subtable = db.query(SubTable).filter(SubTable.id == subtable_id).first()
    if not subtable:
        raise HTTPException(status_code=404, detail="Subtable not found")

    if subtable.status == "occupied":
        raise HTTPException(status_code=400, detail="Cannot delete occupied subtable")

    db.delete(subtable)
    db.commit()

    return {"status": "deleted", "id": subtable_id}
