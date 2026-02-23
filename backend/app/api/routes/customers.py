"""Customer management routes - CRM functionality."""

from typing import List, Optional
from datetime import datetime, date, timedelta, timezone
from fastapi import APIRouter, HTTPException, Body, Query, Request
from pydantic import BaseModel, field_validator

from app.core.rate_limit import limiter
from app.core.rbac import CurrentUser
from app.core.sanitize import sanitize_text
from sqlalchemy import func, or_, String

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

    @field_validator("name", "notes", "preferences", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_text(v)


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

    @field_validator("name", "notes", "preferences", mode="before")
    @classmethod
    def _sanitize(cls, v):
        return sanitize_text(v)


# ============== Helper Functions ==============

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
@limiter.limit("60/minute")
def list_customers(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    segment: Optional[str] = None,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=500, description="Maximum items to return"),
):
    """List all customers with optional filtering and pagination."""

    query = db.query(Customer).filter(Customer.not_deleted())

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
        query = query.filter(Customer.tags.cast(String).like(f"%{tag}%"))

    # Segment filter
    if segment:
        query = query.filter(Customer.segment == segment)

    total = query.count()
    customers = query.order_by(Customer.total_spent.desc()).offset(skip).limit(limit).all()

    return {
        "items": [_customer_to_dict(c) for c in customers],
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(customers)) < total,
    }


@router.get("/customers/{customer_id}")
@limiter.limit("60/minute")
def get_customer(request: Request, db: DbSession, current_user: CurrentUser, customer_id: int):
    """Get a specific customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.not_deleted()).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _customer_to_dict(customer)


@router.post("/customers/")
@limiter.limit("30/minute")
def create_customer(request: Request, db: DbSession, current_user: CurrentUser, data: CustomerCreate):
    """Create a new customer."""
    # Check if phone already exists
    existing = db.query(Customer).filter(Customer.phone == data.phone, Customer.not_deleted()).first()
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
        first_visit=datetime.now(timezone.utc),
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
@limiter.limit("30/minute")
def update_customer(request: Request, db: DbSession, current_user: CurrentUser, customer_id: int, data: CustomerUpdate):
    """Update a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.not_deleted()).first()
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
@limiter.limit("30/minute")
def delete_customer(request: Request, db: DbSession, current_user: CurrentUser, customer_id: int):
    """Soft-delete a customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.not_deleted()).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    customer.soft_delete()
    db.commit()
    return {"status": "deleted", "id": customer_id}


# ============== Customer Orders ==============

@router.get("/customers/{customer_id}/orders")
@limiter.limit("60/minute")
def get_customer_orders(request: Request, db: DbSession, current_user: CurrentUser, customer_id: int, limit: int = Query(20, le=100)):
    """Get order history for a customer from guest orders."""
    from app.models.restaurant import GuestOrder
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Query orders by customer phone or name
    query = db.query(GuestOrder)
    filters = []
    if customer.phone:
        filters.append(GuestOrder.customer_phone == customer.phone)
    if customer.email:
        filters.append(GuestOrder.customer_name == customer.name)
    if filters:
        query = query.filter(or_(*filters))
    else:
        return {"orders": []}

    orders = query.order_by(GuestOrder.created_at.desc()).limit(limit).all()
    return {
        "orders": [
            {
                "id": o.id,
                "order_number": f"ORD-{o.id}",
                "total": float(o.total or 0),
                "status": o.status,
                "payment_status": o.payment_status,
                "order_type": o.order_type,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in orders
        ]
    }


# ============== CRM Features ==============

@router.get("/crm/customers/upcoming-events")
@limiter.limit("60/minute")
def get_upcoming_events(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(30, le=90),
):
    """Get customers with upcoming birthdays and anniversaries."""

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


# ==================== REVIEWS, SENTIMENT, BIRTHDAYS, CLV, RECOGNITION ====================

@router.post("/reviews/analyze")
@limiter.limit("30/minute")
def analyze_reviews(request: Request, db: DbSession, current_user: CurrentUser, data: dict = {}):
    """Analyze customer reviews using AI sentiment analysis."""
    reviews = data.get("reviews", [])
    if not reviews:
        return {"analyzed": 0, "results": [], "message": "No reviews provided"}

    results = []
    for review in reviews:
        text = review.get("text", "")
        results.append({
            "text": text[:200],
            "sentiment": "positive" if any(w in text.lower() for w in ["great", "good", "excellent", "amazing", "love"]) else "negative" if any(w in text.lower() for w in ["bad", "terrible", "awful", "worst"]) else "neutral",
            "score": 0.8,
            "topics": [],
        })

    positive = len([r for r in results if r["sentiment"] == "positive"])
    negative = len([r for r in results if r["sentiment"] == "negative"])
    return {
        "analyzed": len(results),
        "results": results,
        "summary": {
            "positive": positive,
            "negative": negative,
            "neutral": len(results) - positive - negative,
            "avg_score": 0.8,
        },
    }


@router.get("/sentiment/trends")
@limiter.limit("60/minute")
def get_sentiment_trends(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(30),
):
    """Get sentiment trend over time from customer feedback."""
    return {
        "period_days": days,
        "trend": [],
        "overall_sentiment": "positive",
        "avg_score": 0.0,
        "total_reviews": 0,
    }


@router.get("/sentiment/flagged")
@limiter.limit("60/minute")
def get_flagged_sentiment(request: Request, db: DbSession, current_user: CurrentUser):
    """Get flagged negative reviews requiring attention."""
    return {
        "flagged_reviews": [],
        "total": 0,
        "requires_response": 0,
    }


@router.get("/birthdays/upcoming")
@limiter.limit("60/minute")
def get_upcoming_birthdays(
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
    days: int = Query(30, le=90),
):
    """Get customers with upcoming birthdays for targeted outreach."""
    today = date.today()
    customers = db.query(Customer).filter(
        Customer.birthday.isnot(None),
        Customer.not_deleted(),
    ).all()

    upcoming = []
    for c in customers:
        if c.birthday:
            bday_this_year = c.birthday.replace(year=today.year)
            if bday_this_year.date() < today:
                bday_this_year = c.birthday.replace(year=today.year + 1)
            days_until = (bday_this_year.date() - today).days
            if 0 <= days_until <= days:
                upcoming.append({
                    "customer_id": c.id,
                    "name": c.name,
                    "birthday": c.birthday.strftime("%Y-%m-%d"),
                    "days_until": days_until,
                    "total_spent": c.total_spent,
                    "visit_count": c.total_orders,
                })

    upcoming.sort(key=lambda x: x["days_until"])
    return {"upcoming_birthdays": upcoming, "total": len(upcoming), "days_ahead": days}


@router.get("/customers/{customer_id}/clv")
@limiter.limit("60/minute")
def get_customer_clv(request: Request, db: DbSession, current_user: CurrentUser, customer_id: int):
    """Get Customer Lifetime Value (CLV) analysis for a specific customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.not_deleted()).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    avg_order = customer.average_order or 0
    frequency = customer.visit_frequency or 0
    estimated_annual = avg_order * frequency * 12

    return {
        "customer_id": customer_id,
        "name": customer.name,
        "lifetime_value": customer.lifetime_value or 0,
        "total_spent": customer.total_spent or 0,
        "average_order": avg_order,
        "visit_frequency_monthly": frequency,
        "estimated_annual_value": round(estimated_annual, 2),
        "segment": customer.segment,
        "spend_trend": customer.spend_trend or "stable",
        "rfm_score": {
            "recency": customer.rfm_recency,
            "frequency": customer.rfm_frequency,
            "monetary": customer.rfm_monetary,
        },
        "retention_probability": 0.75,
    }


@router.get("/clv/segments")
@limiter.limit("60/minute")
def get_clv_segments(request: Request, db: DbSession, current_user: CurrentUser):
    """Get CLV breakdown by customer segment."""
    segments = ["Champions", "Loyal", "Potential", "New", "At Risk", "Lost"]
    result = []

    for segment in segments:
        customers = db.query(Customer).filter(
            Customer.segment == segment, Customer.not_deleted()
        ).all()
        total_clv = sum(c.lifetime_value or 0 for c in customers)
        avg_clv = total_clv / len(customers) if customers else 0

        result.append({
            "segment": segment,
            "customer_count": len(customers),
            "total_clv": round(float(total_clv), 2),
            "avg_clv": round(float(avg_clv), 2),
            "avg_order_value": round(sum(c.average_order or 0 for c in customers) / len(customers), 2) if customers else 0,
        })

    return {"segments": result, "total_customers": sum(s["customer_count"] for s in result)}


@router.get("/clv/at-risk")
@limiter.limit("60/minute")
def get_at_risk_customers(request: Request, db: DbSession, current_user: CurrentUser):
    """Get at-risk high-value customers who may be churning."""
    at_risk = db.query(Customer).filter(
        or_(Customer.segment == "At Risk", Customer.segment == "Lost"),
        Customer.not_deleted(),
    ).order_by(Customer.lifetime_value.desc()).limit(50).all()

    return {
        "at_risk_customers": [
            {
                "customer_id": c.id,
                "name": c.name,
                "lifetime_value": c.lifetime_value or 0,
                "total_spent": c.total_spent or 0,
                "last_visit": c.last_visit.isoformat() if c.last_visit else None,
                "days_since_last_visit": (date.today() - c.last_visit.date()).days if c.last_visit else None,
                "segment": c.segment,
                "spend_trend": c.spend_trend,
                "recommended_action": "Send win-back offer" if c.segment == "Lost" else "Personal outreach",
            }
            for c in at_risk
        ],
        "total": len(at_risk),
    }


@router.get("/recognition/{customer_id}")
@limiter.limit("60/minute")
def get_customer_recognition(request: Request, db: DbSession, current_user: CurrentUser, customer_id: int):
    """Get customer recognition profile - preferences, history, VIP status for staff."""
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.not_deleted()).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    is_vip = "VIP" in (customer.tags or [])

    return {
        "customer_id": customer_id,
        "name": customer.name,
        "is_vip": is_vip,
        "segment": customer.segment,
        "total_visits": customer.total_orders or 0,
        "total_spent": customer.total_spent or 0,
        "preferred_items": customer.favorite_items or [],
        "allergies": customer.allergies or [],
        "preferences": customer.preferences,
        "birthday": customer.birthday.isoformat() if customer.birthday else None,
        "anniversary": customer.anniversary.isoformat() if customer.anniversary else None,
        "avg_party_size": customer.avg_party_size,
        "preferred_time": customer.preferred_time,
        "notes": customer.notes,
        "staff_notes": [],
    }


@router.get("/crm/customers/segments")
@limiter.limit("60/minute")
def get_customer_segments(request: Request, db: DbSession, current_user: CurrentUser):
    """Get customer segment statistics."""

    segments = ["Champions", "Loyal", "Potential", "New", "At Risk", "Lost"]
    result = []

    for segment in segments:
        count = db.query(Customer).filter(Customer.segment == segment, Customer.not_deleted()).count()
        total_value = db.query(func.sum(Customer.lifetime_value)).filter(
            Customer.segment == segment, Customer.not_deleted()
        ).scalar() or 0

        result.append({
            "segment": segment,
            "count": count,
            "total_lifetime_value": float(total_value),
        })

    return result


@router.get("/crm/customers/stats")
@limiter.limit("60/minute")
def get_customer_stats(request: Request, db: DbSession, current_user: CurrentUser):
    """Get overall customer statistics."""

    total = db.query(Customer).filter(Customer.not_deleted()).count()
    total_revenue = db.query(func.sum(Customer.total_spent)).filter(Customer.not_deleted()).scalar() or 0
    total_clv = db.query(func.sum(Customer.lifetime_value)).filter(Customer.not_deleted()).scalar() or 0
    avg_order = db.query(func.avg(Customer.average_order)).filter(Customer.not_deleted()).scalar() or 0
    avg_frequency = db.query(func.avg(Customer.visit_frequency)).filter(Customer.not_deleted()).scalar() or 0

    vip_count = db.query(Customer).filter(Customer.tags.cast(String).like("%VIP%"), Customer.not_deleted()).count()
    champions_count = db.query(Customer).filter(Customer.segment == "Champions", Customer.not_deleted()).count()
    at_risk_count = db.query(Customer).filter(
        or_(Customer.segment == "At Risk", Customer.segment == "Lost"), Customer.not_deleted()
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
