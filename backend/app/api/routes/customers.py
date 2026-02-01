"""Customer management routes - CRM functionality."""

from typing import List, Optional
from datetime import datetime, date, timedelta
from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from sqlalchemy import func, or_

from app.db.session import DbSession
from app.models.customer import Customer

router = APIRouter()


# ============== Pydantic Schemas ==============

class CustomerCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    notes: Optional[str] = None
    allergies: Optional[List[str]] = None
    preferences: Optional[str] = None
    marketing_consent: bool = True
    tags: Optional[List[str]] = None
    birthday: Optional[str] = None
    anniversary: Optional[str] = None
    acquisition_source: Optional[str] = "direct"
    communication_preference: Optional[str] = "email"


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    allergies: Optional[List[str]] = None
    preferences: Optional[str] = None
    marketing_consent: Optional[bool] = None
    tags: Optional[List[str]] = None
    birthday: Optional[str] = None
    anniversary: Optional[str] = None
    acquisition_source: Optional[str] = None
    communication_preference: Optional[str] = None


# ============== Helper Functions ==============

def _init_demo_customers(db: DbSession):
    """Initialize demo customers if none exist."""
    count = db.query(Customer).count()
    if count == 0:
        demo_customers = [
            {
                "name": "Иван Петров",
                "phone": "+359 888 123 456",
                "email": "ivan.petrov@email.com",
                "total_orders": 45,
                "total_spent": 2850.50,
                "average_order": 63.34,
                "visit_frequency": 4.5,
                "lifetime_value": 4500.00,
                "tags": ["VIP", "Regular"],
                "segment": "Champions",
                "spend_trend": "up",
                "rfm_recency": 5,
                "rfm_frequency": 5,
                "rfm_monetary": 5,
                "acquisition_source": "referral",
                "birthday": datetime(1985, 6, 15),
                "favorite_items": ["Margherita Pizza", "Tiramisu"],
            },
            {
                "name": "Maria Ivanova",
                "phone": "+359 888 234 567",
                "email": "maria.i@email.com",
                "total_orders": 28,
                "total_spent": 1540.00,
                "average_order": 55.00,
                "visit_frequency": 2.8,
                "lifetime_value": 2500.00,
                "tags": ["Regular"],
                "segment": "Loyal",
                "spend_trend": "stable",
                "rfm_recency": 4,
                "rfm_frequency": 4,
                "rfm_monetary": 4,
                "acquisition_source": "walk-in",
            },
            {
                "name": "Georgi Dimitrov",
                "phone": "+359 888 345 678",
                "email": None,
                "total_orders": 8,
                "total_spent": 420.00,
                "average_order": 52.50,
                "visit_frequency": 0.8,
                "lifetime_value": 600.00,
                "tags": ["New"],
                "segment": "Potential",
                "spend_trend": "up",
                "rfm_recency": 3,
                "rfm_frequency": 2,
                "rfm_monetary": 2,
                "acquisition_source": "google",
            },
            {
                "name": "Elena Stoyanova",
                "phone": "+359 888 456 789",
                "email": "elena.s@email.com",
                "total_orders": 52,
                "total_spent": 3650.00,
                "average_order": 70.19,
                "visit_frequency": 5.2,
                "lifetime_value": 5800.00,
                "tags": ["VIP", "Business"],
                "segment": "Champions",
                "spend_trend": "up",
                "rfm_recency": 5,
                "rfm_frequency": 5,
                "rfm_monetary": 5,
                "acquisition_source": "website",
                "allergies": ["Gluten"],
                "notes": "Always requests corner table",
            },
            {
                "name": "Nikolay Todorov",
                "phone": "+359 888 567 890",
                "total_orders": 3,
                "total_spent": 145.00,
                "average_order": 48.33,
                "visit_frequency": 0.3,
                "lifetime_value": 200.00,
                "tags": [],
                "segment": "At Risk",
                "spend_trend": "down",
                "rfm_recency": 1,
                "rfm_frequency": 1,
                "rfm_monetary": 1,
                "acquisition_source": "facebook",
            },
        ]

        for c in demo_customers:
            customer = Customer(**c)
            customer.first_visit = datetime.utcnow() - timedelta(days=180)
            customer.last_visit = datetime.utcnow() - timedelta(days=7)
            db.add(customer)
        db.commit()


def _customer_to_dict(customer: Customer) -> dict:
    """Convert Customer to response dict."""
    return {
        "id": customer.id,
        "name": customer.name,
        "phone": customer.phone,
        "email": customer.email,
        "total_orders": customer.total_orders,
        "total_spent": customer.total_spent,
        "average_order": customer.average_order,
        "first_visit": customer.first_visit.isoformat() if customer.first_visit else None,
        "last_visit": customer.last_visit.isoformat() if customer.last_visit else None,
        "visit_frequency": customer.visit_frequency,
        "lifetime_value": customer.lifetime_value,
        "tags": customer.tags or [],
        "segment": customer.segment,
        "spend_trend": customer.spend_trend or "stable",
        "rfm_score": {
            "recency": customer.rfm_recency,
            "frequency": customer.rfm_frequency,
            "monetary": customer.rfm_monetary,
            "total": customer.rfm_recency + customer.rfm_frequency + customer.rfm_monetary,
        },
        "birthday": customer.birthday.isoformat() if customer.birthday else None,
        "anniversary": customer.anniversary.isoformat() if customer.anniversary else None,
        "acquisition_source": customer.acquisition_source,
        "notes": customer.notes,
        "allergies": customer.allergies or [],
        "preferences": customer.preferences,
        "favorite_items": customer.favorite_items or [],
        "avg_party_size": customer.avg_party_size,
        "preferred_time": customer.preferred_time,
        "marketing_consent": customer.marketing_consent,
        "communication_preference": customer.communication_preference,
        "created_at": customer.created_at.isoformat() if customer.created_at else None,
    }


# ============== Customer CRUD ==============

@router.get("/customers/")
def list_customers(
    db: DbSession,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    segment: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
):
    """List all customers with optional filtering."""
    _init_demo_customers(db)

    query = db.query(Customer)

    # Search filter
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Customer.name.ilike(search_term),
                Customer.phone.ilike(search_term),
                Customer.email.ilike(search_term),
            )
        )

    # Tag filter
    if tag:
        # JSON contains check varies by database - this works for SQLite
        query = query.filter(Customer.tags.contains(tag))

    # Segment filter
    if segment:
        query = query.filter(Customer.segment == segment)

    total = query.count()
    customers = query.order_by(Customer.total_spent.desc()).offset(offset).limit(limit).all()

    return {
        "customers": [_customer_to_dict(c) for c in customers],
        "total": total,
    }


@router.get("/customers/{customer_id}")
def get_customer(db: DbSession, customer_id: int):
    """Get a specific customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _customer_to_dict(customer)


@router.post("/customers/")
def create_customer(db: DbSession, data: CustomerCreate):
    """Create a new customer."""
    # Check if phone already exists
    existing = db.query(Customer).filter(Customer.phone == data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Customer with this phone already exists")

    customer = Customer(
        name=data.name,
        phone=data.phone,
        email=data.email,
        notes=data.notes,
        allergies=data.allergies,
        preferences=data.preferences,
        marketing_consent=data.marketing_consent,
        tags=data.tags or [],
        acquisition_source=data.acquisition_source,
        communication_preference=data.communication_preference,
        first_visit=datetime.utcnow(),
    )

    if data.birthday:
        try:
            customer.birthday = datetime.strptime(data.birthday, "%Y-%m-%d")
        except ValueError:
            pass

    if data.anniversary:
        try:
            customer.anniversary = datetime.strptime(data.anniversary, "%Y-%m-%d")
        except ValueError:
            pass

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return _customer_to_dict(customer)


@router.put("/customers/{customer_id}")
def update_customer(db: DbSession, customer_id: int, data: CustomerUpdate):
    """Update a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    if data.name is not None:
        customer.name = data.name
    if data.phone is not None:
        customer.phone = data.phone
    if data.email is not None:
        customer.email = data.email
    if data.notes is not None:
        customer.notes = data.notes
    if data.allergies is not None:
        customer.allergies = data.allergies
    if data.preferences is not None:
        customer.preferences = data.preferences
    if data.marketing_consent is not None:
        customer.marketing_consent = data.marketing_consent
    if data.tags is not None:
        customer.tags = data.tags
    if data.acquisition_source is not None:
        customer.acquisition_source = data.acquisition_source
    if data.communication_preference is not None:
        customer.communication_preference = data.communication_preference

    if data.birthday:
        try:
            customer.birthday = datetime.strptime(data.birthday, "%Y-%m-%d")
        except ValueError:
            pass

    if data.anniversary:
        try:
            customer.anniversary = datetime.strptime(data.anniversary, "%Y-%m-%d")
        except ValueError:
            pass

    db.commit()
    db.refresh(customer)

    return _customer_to_dict(customer)


@router.delete("/customers/{customer_id}")
def delete_customer(db: DbSession, customer_id: int):
    """Delete a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    db.delete(customer)
    db.commit()
    return {"status": "deleted", "id": customer_id}


# ============== Customer Orders ==============

@router.get("/customers/{customer_id}/orders")
def get_customer_orders(db: DbSession, customer_id: int):
    """Get order history for a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # For demo, return mock order data
    # In production, would join with orders table
    import random
    orders = []
    for i in range(min(customer.total_orders, 10)):
        order_date = datetime.utcnow() - timedelta(days=i * 7)
        orders.append({
            "id": 1000 + i,
            "order_number": f"ORD-{1000 + i}",
            "total": round(random.uniform(30, 120), 2),
            "status": "completed",
            "created_at": order_date.isoformat(),
        })

    return {"orders": orders}


# ============== CRM Features ==============

@router.get("/crm/customers/upcoming-events")
def get_upcoming_events(
    db: DbSession,
    days: int = Query(30, le=90),
):
    """Get customers with upcoming birthdays and anniversaries."""
    _init_demo_customers(db)

    today = date.today()
    events = []

    customers = db.query(Customer).filter(
        or_(Customer.birthday.isnot(None), Customer.anniversary.isnot(None))
    ).all()

    for customer in customers:
        if customer.birthday:
            # Check if birthday is within next X days
            bday_this_year = customer.birthday.replace(year=today.year)
            if bday_this_year.date() < today:
                bday_this_year = customer.birthday.replace(year=today.year + 1)
            days_until = (bday_this_year.date() - today).days
            if 0 <= days_until <= days:
                events.append({
                    "customer_id": customer.id,
                    "customer_name": customer.name,
                    "event_type": "birthday",
                    "date": bday_this_year.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                })

        if customer.anniversary:
            # Check if anniversary is within next X days
            anni_this_year = customer.anniversary.replace(year=today.year)
            if anni_this_year.date() < today:
                anni_this_year = customer.anniversary.replace(year=today.year + 1)
            days_until = (anni_this_year.date() - today).days
            if 0 <= days_until <= days:
                events.append({
                    "customer_id": customer.id,
                    "customer_name": customer.name,
                    "event_type": "anniversary",
                    "date": anni_this_year.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                })

    # Sort by days_until
    events.sort(key=lambda x: x["days_until"])

    return events


@router.get("/crm/customers/segments")
def get_customer_segments(db: DbSession):
    """Get customer segment statistics."""
    _init_demo_customers(db)

    segments = ["Champions", "Loyal", "Potential", "New", "At Risk", "Lost"]
    result = []

    for segment in segments:
        count = db.query(Customer).filter(Customer.segment == segment).count()
        total_value = db.query(func.sum(Customer.lifetime_value)).filter(
            Customer.segment == segment
        ).scalar() or 0

        result.append({
            "segment": segment,
            "count": count,
            "total_lifetime_value": float(total_value),
        })

    return result


@router.get("/crm/customers/stats")
def get_customer_stats(db: DbSession):
    """Get overall customer statistics."""
    _init_demo_customers(db)

    total = db.query(Customer).count()
    total_revenue = db.query(func.sum(Customer.total_spent)).scalar() or 0
    total_clv = db.query(func.sum(Customer.lifetime_value)).scalar() or 0
    avg_order = db.query(func.avg(Customer.average_order)).scalar() or 0
    avg_frequency = db.query(func.avg(Customer.visit_frequency)).scalar() or 0

    vip_count = db.query(Customer).filter(Customer.tags.contains("VIP")).count()
    champions_count = db.query(Customer).filter(Customer.segment == "Champions").count()
    at_risk_count = db.query(Customer).filter(
        or_(Customer.segment == "At Risk", Customer.segment == "Lost")
    ).count()

    return {
        "total_customers": total,
        "vip_customers": vip_count,
        "champions": champions_count,
        "at_risk": at_risk_count,
        "total_revenue": float(total_revenue),
        "total_clv": float(total_clv),
        "avg_order_value": float(avg_order),
        "avg_visit_frequency": float(avg_frequency),
    }
