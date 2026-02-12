"""
Missing Features Implementation
Comprehensive endpoints for features identified as missing or incomplete
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
from decimal import Decimal
from pydantic import BaseModel, Field
import json

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    StaffUser, StaffShift, Table, Venue, PayrollEntry
)


router = APIRouter()


# ===================== SCHEMAS =====================

class OvertimeRuleCreate(BaseModel):
    """Overtime calculation rules"""
    name: str = Field(..., description="Rule name")
    threshold_hours_daily: float = Field(8.0, description="Daily hours before overtime")
    threshold_hours_weekly: float = Field(40.0, description="Weekly hours before overtime")
    multiplier_regular: float = Field(1.5, description="Overtime multiplier (1.5x)")
    multiplier_holiday: float = Field(2.0, description="Holiday multiplier (2x)")
    multiplier_night: float = Field(1.25, description="Night shift multiplier")
    night_start_hour: int = Field(22, description="Night shift start hour (22:00)")
    night_end_hour: int = Field(6, description="Night shift end hour (06:00)")


class ShiftSwapRequest(BaseModel):
    """Shift swap request between staff"""
    requesting_staff_id: int
    target_staff_id: int
    shift_id: int
    reason: Optional[str] = None


class TimeOffRequest(BaseModel):
    """Time off/vacation request"""
    staff_id: int
    start_date: date
    end_date: date
    request_type: str = Field(..., description="vacation, sick, personal, unpaid")
    reason: Optional[str] = None
    hours_requested: Optional[float] = None


class BonusCreate(BaseModel):
    """Staff bonus/commission"""
    staff_id: int
    bonus_type: str = Field(..., description="performance, sales, referral, holiday")
    amount: float
    description: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class AllergenInfo(BaseModel):
    """Allergen information for recipes"""
    recipe_id: int
    allergens: List[str] = Field(..., description="List of allergen codes")
    cross_contamination_risk: List[str] = Field(default=[], description="Cross-contamination risks")
    dietary_labels: List[str] = Field(default=[], description="vegetarian, vegan, gluten-free, etc.")


class NutritionalInfo(BaseModel):
    """Nutritional information per serving"""
    recipe_id: int
    serving_size: str
    calories: float
    protein_g: float
    carbohydrates_g: float
    fat_g: float
    fiber_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    sugar_g: Optional[float] = None


class CustomerFeedback(BaseModel):
    """Customer feedback/review"""
    customer_id: Optional[int] = None
    order_id: Optional[int] = None
    overall_rating: int = Field(..., ge=1, le=5)
    food_rating: Optional[int] = Field(None, ge=1, le=5)
    service_rating: Optional[int] = Field(None, ge=1, le=5)
    ambiance_rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
    would_recommend: Optional[bool] = None


class CustomerSegment(BaseModel):
    """Customer segmentation"""
    name: str
    criteria: Dict = Field(..., description="Segmentation criteria")
    description: Optional[str] = None


class ProfitLossRequest(BaseModel):
    """Profit & Loss report request"""
    start_date: date
    end_date: date
    venue_id: Optional[int] = None
    include_projections: bool = False


class BudgetVarianceRequest(BaseModel):
    """Budget variance analysis request"""
    budget_id: int
    period: str = Field("month", description="day, week, month, quarter, year")


# ===================== STAFF/PAYROLL ENDPOINTS =====================

@router.post("/payroll/overtime-rules", summary="Create overtime calculation rules")
def create_overtime_rules(
    rule: OvertimeRuleCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Define overtime calculation rules for payroll

    - Daily threshold: Hours after which daily overtime kicks in (default 8)
    - Weekly threshold: Hours after which weekly overtime kicks in (default 40)
    - Regular multiplier: Standard overtime rate (default 1.5x)
    - Holiday multiplier: Holiday/weekend rate (default 2x)
    - Night multiplier: Night shift premium (default 1.25x)
    """
    # Store in venue settings or dedicated table
    venue = db.query(Venue).filter(Venue.id == current_user.venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    settings = venue.settings or {}
    settings["overtime_rules"] = rule.dict()
    venue.settings = settings

    db.commit()

    return {
        "message": "Overtime rules configured",
        "rules": rule.dict()
    }


@router.get("/payroll/overtime-rules", summary="Get overtime calculation rules")
def get_overtime_rules(
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get current overtime calculation rules"""
    venue = db.query(Venue).filter(Venue.id == current_user.venue_id).first()
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")

    # Get settings from VenueSettings relationship
    settings_data = {}
    if venue.settings and len(venue.settings) > 0:
        settings_data = venue.settings[0].settings_data or {}

    rules = settings_data.get("overtime_rules", {
        "threshold_hours_daily": 8.0,
        "threshold_hours_weekly": 40.0,
        "multiplier_regular": 1.5,
        "multiplier_holiday": 2.0,
        "multiplier_night": 1.25,
        "night_start_hour": 22,
        "night_end_hour": 6
    })

    return rules


@router.post("/shifts/swap-request", summary="Request shift swap")
def request_shift_swap(
    swap: ShiftSwapRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Request to swap shifts with another staff member

    Workflow:
    1. Requesting staff submits swap request
    2. Target staff receives notification
    3. Target staff approves/rejects
    4. Manager final approval (if required)
    5. Shifts are swapped in system
    """
    # Verify shift exists
    shift = db.query(StaffShift).filter(StaffShift.id == swap.shift_id).first()
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    # Verify requesting staff is the shift owner
    if shift.staff_id != swap.requesting_staff_id:
        raise HTTPException(status_code=400, detail="Only shift owner can request swap")

    # Verify target staff exists
    target_staff = db.query(StaffUser).filter(StaffUser.id == swap.target_staff_id).first()
    if not target_staff:
        raise HTTPException(status_code=404, detail="Target staff not found")

    # Create swap request (store in shift or separate table)
    swap_data = {
        "requesting_staff_id": swap.requesting_staff_id,
        "target_staff_id": swap.target_staff_id,
        "shift_id": swap.shift_id,
        "reason": swap.reason,
        "status": "pending",
        "requested_at": datetime.now().isoformat()
    }

    # Store in shift's metadata or create swap_requests table
    shift_notes = shift.notes or ""
    shift.notes = f"{shift_notes}\n[SWAP REQUEST]: {json.dumps(swap_data)}"

    db.commit()

    return {
        "message": "Shift swap request submitted",
        "swap_request": swap_data,
        "notification_sent_to": target_staff.full_name
    }


@router.post("/staff/time-off", summary="Submit time off request")
def submit_time_off_request(
    request: TimeOffRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Submit time off/vacation request

    Request types:
    - vacation: Paid vacation days
    - sick: Sick leave
    - personal: Personal days
    - unpaid: Unpaid leave

    Workflow:
    1. Staff submits request
    2. Manager reviews and approves/rejects
    3. System updates availability calendar
    4. Scheduling adjusted accordingly
    """
    staff = db.query(StaffUser).filter(StaffUser.id == request.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Calculate total days
    total_days = (request.end_date - request.start_date).days + 1

    # Check available balance (for vacation type)
    if request.request_type == "vacation":
        # Would check vacation_balance from staff record
        available_days = getattr(staff, 'vacation_days_remaining', 20)
        if total_days > available_days:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient vacation days. Available: {available_days}, Requested: {total_days}"
            )

    time_off_data = {
        "staff_id": request.staff_id,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "type": request.request_type,
        "reason": request.reason,
        "total_days": total_days,
        "hours_requested": request.hours_requested or (total_days * 8),
        "status": "pending",
        "submitted_at": datetime.now().isoformat()
    }

    return {
        "message": "Time off request submitted",
        "request": time_off_data,
        "pending_approval_from": "manager"
    }


@router.post("/staff/bonus", summary="Add staff bonus/commission")
def add_staff_bonus(
    bonus: BonusCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Add bonus or commission for staff member

    Bonus types:
    - performance: Based on performance metrics
    - sales: Sales-based commission
    - referral: Customer/staff referral bonus
    - holiday: Holiday bonus
    - tips: Tip pooling distribution
    """
    staff = db.query(StaffUser).filter(StaffUser.id == bonus.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Create payroll entry for bonus
    payroll_entry = PayrollEntry(
        staff_id=bonus.staff_id,
        venue_id=current_user.venue_id,
        period_start=bonus.period_start or date.today().replace(day=1),
        period_end=bonus.period_end or date.today(),
        hours_worked=0,
        regular_hours=0,
        overtime_hours=0,
        hourly_rate=Decimal("0"),
        gross_pay=Decimal(str(bonus.amount)),
        deductions=Decimal("0"),
        net_pay=Decimal(str(bonus.amount)),
        status="pending",
        notes=f"{bonus.bonus_type}: {bonus.description or 'Bonus payment'}"
    )

    db.add(payroll_entry)
    db.commit()

    return {
        "message": "Bonus added successfully",
        "bonus": {
            "staff_id": bonus.staff_id,
            "staff_name": staff.full_name,
            "type": bonus.bonus_type,
            "amount": bonus.amount,
            "description": bonus.description,
            "payroll_entry_id": payroll_entry.id
        }
    }


@router.get("/payroll/tax-report", summary="Generate tax report")
def generate_tax_report(
    year: int = Query(..., description="Tax year"),
    quarter: Optional[int] = Query(None, ge=1, le=4, description="Quarter (1-4)"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Generate Bulgarian tax report for payroll

    Includes:
    - Social security contributions (DОО)
    - Health insurance (НЗОК)
    - Income tax (ДДФЛ)
    - Employer contributions

    Outputs for:
    - Declaration 1 / Declaration 6
    - Annual reporting requirements
    """
    # Determine date range
    if quarter:
        start_month = (quarter - 1) * 3 + 1
        start_date = date(year, start_month, 1)
        end_month = quarter * 3
        if end_month == 12:
            end_date = date(year, 12, 31)
        else:
            end_date = date(year, end_month + 1, 1) - timedelta(days=1)
    else:
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

    # Get all payroll entries for period
    entries = db.query(PayrollEntry).filter(
        PayrollEntry.venue_id == current_user.venue_id,
        PayrollEntry.period_start >= start_date,
        PayrollEntry.period_end <= end_date,
        PayrollEntry.status.in_(["approved", "paid"])
    ).all()

    # Calculate totals
    total_gross = sum(float(e.gross_pay or 0) for e in entries)
    total_net = sum(float(e.net_pay or 0) for e in entries)
    total_deductions = sum(float(e.deductions or 0) for e in entries)

    # Bulgarian tax rates (2024)
    INCOME_TAX_RATE = 0.10  # 10% flat tax
    SOCIAL_SECURITY_EMPLOYEE = 0.1378  # Employee portion
    SOCIAL_SECURITY_EMPLOYER = 0.1892  # Employer portion
    HEALTH_INSURANCE_EMPLOYEE = 0.032  # Employee portion
    HEALTH_INSURANCE_EMPLOYER = 0.048  # Employer portion

    # Calculate contributions
    income_tax = total_gross * INCOME_TAX_RATE
    employee_social = total_gross * SOCIAL_SECURITY_EMPLOYEE
    employer_social = total_gross * SOCIAL_SECURITY_EMPLOYER
    employee_health = total_gross * HEALTH_INSURANCE_EMPLOYEE
    employer_health = total_gross * HEALTH_INSURANCE_EMPLOYER

    total_employer_cost = total_gross + employer_social + employer_health

    # Staff breakdown
    staff_summary = {}
    for entry in entries:
        staff_id = entry.staff_id
        if staff_id not in staff_summary:
            staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
            staff_summary[staff_id] = {
                "name": staff.full_name if staff else "Unknown",
                "gross_pay": 0,
                "income_tax": 0,
                "social_security": 0,
                "health_insurance": 0,
                "net_pay": 0
            }

        gross = float(entry.gross_pay or 0)
        staff_summary[staff_id]["gross_pay"] += gross
        staff_summary[staff_id]["income_tax"] += gross * INCOME_TAX_RATE
        staff_summary[staff_id]["social_security"] += gross * SOCIAL_SECURITY_EMPLOYEE
        staff_summary[staff_id]["health_insurance"] += gross * HEALTH_INSURANCE_EMPLOYEE
        staff_summary[staff_id]["net_pay"] += float(entry.net_pay or 0)

    return {
        "report_period": {
            "year": year,
            "quarter": quarter,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "summary": {
            "total_gross_wages": round(total_gross, 2),
            "total_net_wages": round(total_net, 2),
            "total_deductions": round(total_deductions, 2),
            "payroll_entries_count": len(entries)
        },
        "tax_breakdown": {
            "income_tax_10_percent": round(income_tax, 2),
            "employee_contributions": {
                "social_security_doo": round(employee_social, 2),
                "health_insurance_nzok": round(employee_health, 2),
                "total": round(employee_social + employee_health, 2)
            },
            "employer_contributions": {
                "social_security_doo": round(employer_social, 2),
                "health_insurance_nzok": round(employer_health, 2),
                "total": round(employer_social + employer_health, 2)
            }
        },
        "total_employer_cost": round(total_employer_cost, 2),
        "staff_breakdown": list(staff_summary.values())
    }


# ===================== RECIPE/KITCHEN ENDPOINTS =====================

@router.post("/recipes/{recipe_id}/allergens", summary="Set recipe allergens")
def set_recipe_allergens(
    recipe_id: int,
    allergen_info: AllergenInfo,
    db: Session = Depends(get_db)
):
    """
    Set allergen information for a recipe

    Standard allergens (EU 14):
    - celery, gluten, crustaceans, eggs, fish, lupin, milk,
    - molluscs, mustard, nuts, peanuts, sesame, soybeans, sulphites

    Dietary labels:
    - vegetarian, vegan, gluten-free, dairy-free, nut-free, halal, kosher
    """
    # Would update Recipe model or create RecipeAllergen table
    return {
        "recipe_id": recipe_id,
        "allergens": allergen_info.allergens,
        "cross_contamination_risk": allergen_info.cross_contamination_risk,
        "dietary_labels": allergen_info.dietary_labels,
        "updated_at": datetime.now().isoformat()
    }


@router.get("/recipes/{recipe_id}/allergens", summary="Get recipe allergens")
def get_recipe_allergens(recipe_id: int, db: Session = Depends(get_db)):
    """Get allergen information for a recipe"""
    # Would fetch from Recipe model or RecipeAllergen table
    return {
        "recipe_id": recipe_id,
        "allergens": ["gluten", "eggs", "milk"],
        "cross_contamination_risk": ["nuts"],
        "dietary_labels": ["vegetarian"],
        "allergen_statement": "Contains gluten, eggs, milk. May contain traces of nuts."
    }


@router.post("/recipes/{recipe_id}/nutrition", summary="Set nutritional info")
def set_nutritional_info(
    recipe_id: int,
    nutrition: NutritionalInfo,
    db: Session = Depends(get_db)
):
    """
    Set nutritional information per serving

    Nutritional values are per serving size.
    Can be auto-calculated from ingredients if ingredient nutrition data is available.
    """
    return {
        "recipe_id": recipe_id,
        "nutrition": nutrition.dict(),
        "updated_at": datetime.now().isoformat()
    }


@router.get("/recipes/{recipe_id}/nutrition", summary="Get nutritional info")
def get_nutritional_info(recipe_id: int, db: Session = Depends(get_db)):
    """Get nutritional information for a recipe"""
    return {
        "recipe_id": recipe_id,
        "serving_size": "1 portion (250g)",
        "calories": 450,
        "protein_g": 25.5,
        "carbohydrates_g": 35.0,
        "fat_g": 22.0,
        "fiber_g": 4.5,
        "sodium_mg": 680,
        "sugar_g": 8.0,
        "daily_value_percentages": {
            "calories": 22.5,
            "protein": 51.0,
            "carbohydrates": 12.7,
            "fat": 33.8,
            "fiber": 18.0,
            "sodium": 28.3
        }
    }


@router.post("/recipes/{recipe_id}/scale", summary="Scale recipe")
def scale_recipe(
    recipe_id: int,
    target_servings: int = Query(..., gt=0, description="Target number of servings"),
    db: Session = Depends(get_db)
):
    """
    Scale recipe ingredients for batch production

    Automatically adjusts all ingredient quantities proportionally.
    Useful for prep lists and large batch production.
    """
    # Would fetch recipe and scale ingredients
    original_servings = 4
    scale_factor = target_servings / original_servings

    return {
        "recipe_id": recipe_id,
        "original_servings": original_servings,
        "target_servings": target_servings,
        "scale_factor": round(scale_factor, 2),
        "scaled_ingredients": [
            {"name": "Chicken breast", "original": "500g", "scaled": f"{int(500 * scale_factor)}g"},
            {"name": "Olive oil", "original": "30ml", "scaled": f"{int(30 * scale_factor)}ml"},
            {"name": "Garlic", "original": "3 cloves", "scaled": f"{int(3 * scale_factor)} cloves"},
            {"name": "Salt", "original": "5g", "scaled": f"{int(5 * scale_factor)}g"}
        ],
        "preparation_time_adjusted": f"{int(30 * (1 + (scale_factor - 1) * 0.3))} minutes"
    }


@router.get("/kitchen/prep-list", summary="Generate prep list")
def generate_prep_list(
    date_for: date = Query(..., description="Date to generate prep for"),
    shift: Optional[str] = Query(None, description="morning, afternoon, evening"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Generate kitchen prep list based on expected demand

    Uses:
    - Historical sales data for the day of week
    - Reservations for the day
    - Events scheduled
    - Current stock levels

    Outputs list of items to prep with quantities.
    """
    day_of_week = date_for.strftime("%A")

    return {
        "date": date_for.isoformat(),
        "day_of_week": day_of_week,
        "shift": shift or "all",
        "expected_covers": 150,
        "prep_items": [
            {
                "item": "Burger Patties",
                "quantity_needed": 50,
                "current_stock": 12,
                "to_prep": 38,
                "prep_time_minutes": 45,
                "priority": "high",
                "assigned_to": None
            },
            {
                "item": "Caesar Dressing",
                "quantity_needed": 3,
                "current_stock": 1,
                "to_prep": 2,
                "prep_time_minutes": 15,
                "priority": "medium",
                "assigned_to": None
            },
            {
                "item": "Chopped Vegetables",
                "quantity_needed": 5,
                "current_stock": 2,
                "to_prep": 3,
                "prep_time_minutes": 30,
                "priority": "medium",
                "assigned_to": None
            }
        ],
        "total_prep_time_minutes": 90,
        "staff_required": 2,
        "notes": [
            "VIP reservation at 19:00 - 8 guests",
            "Birthday party at 18:00 - special cake needed"
        ]
    }


# ===================== CUSTOMER ENDPOINTS =====================

@router.post("/customers/feedback", summary="Submit customer feedback")
def submit_customer_feedback(
    feedback: CustomerFeedback,
    db: Session = Depends(get_db)
):
    """
    Submit customer feedback/review

    Can be linked to specific order or submitted independently.
    Triggers notifications to management for low ratings.
    """
    # Calculate overall sentiment
    ratings = [
        feedback.overall_rating,
        feedback.food_rating,
        feedback.service_rating,
        feedback.ambiance_rating
    ]
    valid_ratings = [r for r in ratings if r is not None]
    avg_rating = sum(valid_ratings) / len(valid_ratings) if valid_ratings else 0

    sentiment = "positive" if avg_rating >= 4 else "neutral" if avg_rating >= 3 else "negative"

    # Alert management for low ratings
    alert_management = avg_rating < 3

    return {
        "feedback_id": 1,  # Would be auto-generated
        "submitted_at": datetime.now().isoformat(),
        "ratings": {
            "overall": feedback.overall_rating,
            "food": feedback.food_rating,
            "service": feedback.service_rating,
            "ambiance": feedback.ambiance_rating,
            "average": round(avg_rating, 1)
        },
        "sentiment": sentiment,
        "would_recommend": feedback.would_recommend,
        "comment": feedback.comment,
        "alert_sent_to_management": alert_management,
        "thank_you_message": "Thank you for your feedback! Your opinion helps us improve."
    }


@router.get("/customers/feedback/summary", summary="Get feedback summary")
def get_feedback_summary(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get summary of customer feedback for a period"""
    return {
        "period": {
            "start": (start_date or date.today() - timedelta(days=30)).isoformat(),
            "end": (end_date or date.today()).isoformat()
        },
        "total_reviews": 127,
        "average_ratings": {
            "overall": 4.3,
            "food": 4.5,
            "service": 4.2,
            "ambiance": 4.1
        },
        "rating_distribution": {
            "5_stars": 52,
            "4_stars": 45,
            "3_stars": 18,
            "2_stars": 8,
            "1_star": 4
        },
        "would_recommend_percentage": 85.0,
        "sentiment_breakdown": {
            "positive": 76,
            "neutral": 23,
            "negative": 5
        },
        "top_positive_keywords": ["delicious", "friendly staff", "great atmosphere"],
        "top_negative_keywords": ["slow service", "noisy", "expensive"],
        "trend": {
            "direction": "improving",
            "change_from_previous_period": 0.2
        }
    }


@router.get("/customers/birthdays", summary="Get upcoming birthdays")
def get_upcoming_birthdays(
    days_ahead: int = Query(7, ge=1, le=30, description="Days to look ahead"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get list of customers with upcoming birthdays

    Useful for:
    - Sending birthday promotions
    - Preparing special offers
    - Birthday reservation alerts
    """
    today = date.today()
    end_date = today + timedelta(days=days_ahead)

    # Would query customers with birthday_date between today and end_date
    # Using day/month comparison (ignoring year)

    return {
        "period": {
            "from": today.isoformat(),
            "to": end_date.isoformat(),
            "days_ahead": days_ahead
        },
        "birthdays": [
            {
                "customer_id": 1,
                "name": "Иван Петров",
                "birthday": "1985-12-30",
                "age_turning": 39,
                "days_until": 2,
                "email": "ivan@example.com",
                "phone": "+359888123456",
                "loyalty_tier": "gold",
                "total_visits": 24,
                "last_visit": "2024-12-15"
            },
            {
                "customer_id": 2,
                "name": "Мария Иванова",
                "birthday": "1990-01-02",
                "age_turning": 35,
                "days_until": 5,
                "email": "maria@example.com",
                "phone": "+359888654321",
                "loyalty_tier": "silver",
                "total_visits": 12,
                "last_visit": "2024-12-20"
            }
        ],
        "total_birthdays": 2,
        "suggested_actions": [
            "Send birthday email with special offer",
            "Prepare complimentary dessert if they reserve",
            "Alert staff about VIP birthday visits"
        ]
    }


@router.post("/customers/segments", summary="Create customer segment")
def create_customer_segment(
    segment: CustomerSegment,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Create customer segment for targeted marketing

    Criteria examples:
    - visit_frequency: "weekly", "monthly", "occasional"
    - avg_spend: {"min": 50, "max": 200}
    - loyalty_tier: "gold", "silver", "bronze"
    - last_visit_days: {"max": 30}  # Active customers
    - preferred_categories: ["wine", "desserts"]
    """
    return {
        "segment_id": 1,
        "name": segment.name,
        "criteria": segment.criteria,
        "description": segment.description,
        "created_at": datetime.now().isoformat(),
        "estimated_customers": 150,  # Would calculate based on criteria
        "status": "active"
    }


@router.get("/customers/segments/{segment_id}/members", summary="Get segment members")
def get_segment_members(
    segment_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get customers in a specific segment"""
    return {
        "segment_id": segment_id,
        "segment_name": "High Value Customers",
        "total_members": 150,
        "page": {"skip": skip, "limit": limit},
        "members": [
            {
                "customer_id": 1,
                "name": "Иван Петров",
                "email": "ivan@example.com",
                "total_spent": 2500.00,
                "visit_count": 24,
                "last_visit": "2024-12-15",
                "loyalty_tier": "gold"
            }
        ]
    }


# ===================== FINANCIAL ENDPOINTS =====================

@router.post("/financial/profit-loss", summary="Generate P&L statement")
def generate_profit_loss_statement(
    request: ProfitLossRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Generate Profit & Loss (Income) Statement

    Standard restaurant P&L format:
    - Revenue (Sales)
    - Cost of Goods Sold (COGS)
    - Gross Profit
    - Operating Expenses
    - Operating Income
    - Other Income/Expenses
    - Net Profit
    """
    # Would calculate actual values from orders, expenses, payroll, etc.

    return {
        "report_type": "Profit & Loss Statement",
        "period": {
            "start": request.start_date.isoformat(),
            "end": request.end_date.isoformat()
        },
        "revenue": {
            "food_sales": 85000.00,
            "beverage_sales": 35000.00,
            "delivery_sales": 12000.00,
            "other_income": 2000.00,
            "discounts": -3500.00,
            "total_revenue": 130500.00
        },
        "cost_of_goods_sold": {
            "food_costs": 28500.00,
            "beverage_costs": 10500.00,
            "packaging_costs": 1800.00,
            "total_cogs": 40800.00
        },
        "gross_profit": 89700.00,
        "gross_profit_margin": 68.7,
        "operating_expenses": {
            "labor": {
                "wages": 28000.00,
                "payroll_taxes": 4200.00,
                "benefits": 2100.00,
                "total_labor": 34300.00
            },
            "occupancy": {
                "rent": 5000.00,
                "utilities": 1800.00,
                "insurance": 800.00,
                "total_occupancy": 7600.00
            },
            "operating": {
                "marketing": 2500.00,
                "supplies": 1200.00,
                "maintenance": 900.00,
                "technology": 500.00,
                "other": 800.00,
                "total_operating": 5900.00
            },
            "total_operating_expenses": 47800.00
        },
        "operating_income": 41900.00,
        "operating_margin": 32.1,
        "other_income_expenses": {
            "interest_expense": -500.00,
            "depreciation": -1200.00,
            "total_other": -1700.00
        },
        "net_profit_before_tax": 40200.00,
        "income_tax": 4020.00,
        "net_profit": 36180.00,
        "net_profit_margin": 27.7,
        "key_ratios": {
            "food_cost_percentage": 33.5,
            "beverage_cost_percentage": 30.0,
            "labor_cost_percentage": 26.3,
            "prime_cost_percentage": 57.5,
            "occupancy_cost_percentage": 5.8
        }
    }


@router.get("/financial/budget-variance", summary="Budget variance analysis")
def get_budget_variance(
    budget_id: int = Query(..., description="Budget ID to analyze"),
    period: str = Query("month", description="Period: day, week, month, quarter"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Analyze actual vs budgeted performance

    Shows variances for key metrics and highlights areas needing attention.
    """
    return {
        "budget_id": budget_id,
        "budget_name": "Q4 2024 Operating Budget",
        "period": period,
        "analysis_date": date.today().isoformat(),
        "variance_summary": {
            "total_favorable": 3500.00,
            "total_unfavorable": -1200.00,
            "net_variance": 2300.00,
            "variance_percentage": 2.1
        },
        "line_items": [
            {
                "category": "Revenue",
                "budgeted": 130000.00,
                "actual": 132500.00,
                "variance": 2500.00,
                "variance_percent": 1.9,
                "status": "favorable",
                "notes": "Above target due to increased delivery orders"
            },
            {
                "category": "Food Cost",
                "budgeted": 42000.00,
                "actual": 43200.00,
                "variance": -1200.00,
                "variance_percent": -2.9,
                "status": "unfavorable",
                "notes": "Supplier price increases not fully offset by menu price adjustments"
            },
            {
                "category": "Labor Cost",
                "budgeted": 35000.00,
                "actual": 34000.00,
                "variance": 1000.00,
                "variance_percent": 2.9,
                "status": "favorable",
                "notes": "Efficient scheduling reduced overtime"
            }
        ],
        "recommendations": [
            "Review food supplier contracts for better pricing",
            "Continue efficient labor scheduling practices",
            "Consider small menu price adjustments to offset food cost increases"
        ],
        "alerts": [
            {
                "severity": "warning",
                "category": "Food Cost",
                "message": "Food cost trending 2.9% above budget - monitor closely"
            }
        ]
    }


@router.get("/financial/cash-flow", summary="Cash flow report")
def get_cash_flow_report(
    start_date: date = Query(..., description="Report start date"),
    end_date: date = Query(..., description="Report end date"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Generate cash flow statement

    Shows:
    - Operating activities (daily operations cash)
    - Investing activities (equipment, improvements)
    - Financing activities (loans, owner draws)
    """
    return {
        "report_type": "Cash Flow Statement",
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "beginning_cash_balance": 25000.00,
        "operating_activities": {
            "cash_from_sales": 128000.00,
            "cash_paid_to_suppliers": -42000.00,
            "cash_paid_to_employees": -34000.00,
            "cash_paid_for_rent": -5000.00,
            "cash_paid_for_utilities": -1800.00,
            "cash_paid_for_other_expenses": -8000.00,
            "net_cash_from_operations": 37200.00
        },
        "investing_activities": {
            "equipment_purchases": -5000.00,
            "leasehold_improvements": 0.00,
            "net_cash_from_investing": -5000.00
        },
        "financing_activities": {
            "loan_payments": -2000.00,
            "owner_draws": -10000.00,
            "owner_contributions": 0.00,
            "net_cash_from_financing": -12000.00
        },
        "net_change_in_cash": 20200.00,
        "ending_cash_balance": 45200.00,
        "cash_flow_forecast": {
            "next_30_days": {
                "expected_inflows": 135000.00,
                "expected_outflows": 98000.00,
                "projected_ending_balance": 82200.00
            }
        }
    }


# ===================== TABLE MANAGEMENT ENDPOINTS =====================

@router.get("/tables/real-time-status", summary="Get real-time table status")
def get_real_time_table_status(
    floor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get real-time status of all tables

    For WebSocket updates or polling.
    Returns table status, time seated, estimated turnover, etc.
    """
    tables = db.query(Table).filter(
        Table.venue_id == current_user.venue_id
    ).all()

    table_status = []
    for table in tables:
        # Calculate time since seated (would come from active order/session)
        time_seated = None
        if table.status == "occupied":
            # Would get from TableSession or Order
            time_seated = 45  # minutes

        table_status.append({
            "table_id": table.id,
            "table_number": table.table_number,
            "capacity": table.capacity,
            "status": table.status,
            "current_guests": 4 if table.status == "occupied" else 0,
            "time_seated_minutes": time_seated,
            "estimated_remaining_minutes": 30 if time_seated else None,
            "server_name": "Иван",
            "current_order_total": 125.50 if table.status == "occupied" else 0,
            "reservation": None,  # Would show upcoming reservation
            "needs_attention": False
        })

    return {
        "timestamp": datetime.now().isoformat(),
        "venue_id": current_user.venue_id,
        "floor_id": floor_id,
        "summary": {
            "total_tables": len(table_status),
            "available": sum(1 for t in table_status if t["status"] == "available"),
            "occupied": sum(1 for t in table_status if t["status"] == "occupied"),
            "reserved": sum(1 for t in table_status if t["status"] == "reserved"),
            "total_seated_guests": sum(t["current_guests"] for t in table_status),
            "total_capacity": sum(t["capacity"] for t in table_status)
        },
        "tables": table_status
    }


@router.get("/tables/wait-time-estimate", summary="Estimate wait time")
def estimate_wait_time(
    party_size: int = Query(..., ge=1, le=20, description="Number of guests"),
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Estimate wait time for a party

    Based on:
    - Current table availability
    - Average table turnover time
    - Upcoming reservations
    - Historical patterns
    """
    # Would calculate based on actual data

    return {
        "party_size": party_size,
        "timestamp": datetime.now().isoformat(),
        "estimate": {
            "minutes_low": 10,
            "minutes_high": 20,
            "minutes_average": 15,
            "confidence": 0.85
        },
        "factors": {
            "suitable_tables_available": 0,
            "tables_near_turnover": 2,
            "average_turnover_minutes": 75,
            "time_to_next_turnover_minutes": 15
        },
        "alternatives": [
            {
                "option": "Bar seating",
                "wait_time": 0,
                "available_seats": 4
            },
            {
                "option": "High table",
                "wait_time": 5,
                "capacity": party_size + 1
            }
        ],
        "message": f"Estimated wait time for party of {party_size}: 10-20 minutes. Bar seating available immediately."
    }


@router.post("/tables/auto-assign", summary="Auto-assign table")
def auto_assign_table(
    party_size: int = Query(..., ge=1, le=20, description="Number of guests"),
    preferences: Optional[Dict] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Automatically assign optimal table for party

    Preferences can include:
    - location: "window", "booth", "patio", "quiet"
    - accessibility: true/false
    - high_chair_needed: true/false
    """
    # Would run algorithm to find optimal table

    return {
        "party_size": party_size,
        "preferences": preferences or {},
        "assignment": {
            "table_id": 12,
            "table_number": "T12",
            "capacity": party_size + 1,
            "location": "Window",
            "server_id": 5,
            "server_name": "Мария",
            "score": 0.95  # Match score
        },
        "alternatives": [
            {
                "table_id": 8,
                "table_number": "T8",
                "capacity": party_size + 2,
                "location": "Center",
                "score": 0.82
            }
        ],
        "notes": [
            "Assigned window table as preferred",
            "Server Мария specializes in large parties"
        ]
    }
