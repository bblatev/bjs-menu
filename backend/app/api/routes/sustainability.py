"""
Sustainability API Endpoints
Carbon footprint tracking, waste management, and sustainability reporting
"""

from fastapi import APIRouter, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from pydantic import BaseModel

from app.db.session import get_db
from app.services.sustainability_service import SustainabilityService
from app.core.rate_limit import limiter



router = APIRouter()


# ==================== SCHEMAS ====================

class CarbonFootprint(BaseModel):
    item_id: int
    item_name: dict
    co2_kg_per_serving: float
    ingredients_breakdown: dict
    transport_impact: float
    category: str
    rating: dict


class OrderFootprint(BaseModel):
    order_id: int
    total_co2_kg: float
    items_breakdown: List[dict]
    equivalents: dict
    rating: dict


class WasteLogRequest(BaseModel):
    venue_id: int
    item_id: Optional[int] = None
    stock_item_id: Optional[int] = None
    quantity: float
    unit: str
    reason: str
    cost: Optional[Decimal] = None
    logged_by_staff_id: int


class SustainabilityReport(BaseModel):
    period: dict
    carbon_footprint: dict
    waste: dict
    total_orders: int
    sustainability_score: dict


# ==================== ENDPOINTS ====================

@router.get("/")
@limiter.limit("60/minute")
async def get_sustainability_root(request: Request, db: Session = Depends(get_db)):
    """Sustainability module overview."""
    return {"module": "sustainability", "status": "active", "endpoints": ["/carbon-footprint/menu", "/waste/statistics", "/report"]}


@router.get("/carbon-footprint/menu", response_model=List[CarbonFootprint])
@limiter.limit("60/minute")
def get_menu_carbon_footprints(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """
    Get carbon footprint for all menu items
    
    Shows CO2 emissions per serving for each item,
    sorted from lowest to highest impact
    """
    service = SustainabilityService(db)
    
    footprints = service.get_menu_carbon_footprints(venue_id)
    
    return footprints


@router.get("/carbon-footprint/item/{item_id}", response_model=CarbonFootprint)
@limiter.limit("60/minute")
def get_item_carbon_footprint(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db)
):
    """Get carbon footprint for specific menu item"""
    service = SustainabilityService(db)
    
    footprint = service.calculate_item_carbon_footprint(item_id)
    
    if not footprint:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Item not found")
    
    return footprint


@router.get("/carbon-footprint/order/{order_id}", response_model=OrderFootprint)
@limiter.limit("60/minute")
def get_order_carbon_footprint(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db)
):
    """
    Get total carbon footprint for an order
    
    Shows:
    - Total CO2 emissions
    - Breakdown by item
    - Equivalent metrics (trees, km driving, etc.)
    """
    service = SustainabilityService(db)
    
    footprint = service.calculate_order_carbon_footprint(order_id)
    
    if not footprint:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")
    
    return footprint


@router.post("/waste/log")
@limiter.limit("30/minute")
def log_waste_event(
    request: Request,
    waste: WasteLogRequest,
    db: Session = Depends(get_db)
):
    """
    Log a waste event
    
    Records:
    - What was wasted
    - How much
    - Why (spoilage, error, return)
    - Cost impact
    """
    service = SustainabilityService(db)
    
    result = service.log_waste(
        venue_id=waste.venue_id,
        item_id=waste.item_id,
        stock_item_id=waste.stock_item_id,
        quantity=waste.quantity,
        unit=waste.unit,
        reason=waste.reason,
        cost=waste.cost,
        logged_by_staff_id=waste.logged_by_staff_id
    )
    
    return {
        'success': True,
        'waste_log': result
    }


@router.get("/waste/statistics")
@limiter.limit("60/minute")
def get_waste_statistics(
    request: Request,
    venue_id: int,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get waste statistics for period
    
    Returns:
    - Total waste by weight and cost
    - Breakdown by reason (spoilage, errors, returns)
    - Waste by category
    - Reduction recommendations
    """
    service = SustainabilityService(db)
    
    stats = service.get_waste_statistics(
        venue_id=venue_id,
        start_date=datetime.combine(start_date, datetime.min.time()),
        end_date=datetime.combine(end_date, datetime.max.time())
    )
    
    return stats


@router.get("/report", response_model=SustainabilityReport)
@limiter.limit("60/minute")
def get_sustainability_report(
    request: Request,
    venue_id: int,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db)
):
    """
    Generate comprehensive sustainability report
    
    Includes:
    - Carbon footprint analysis
    - Waste statistics
    - Overall sustainability score (A-D grade)
    - Improvement recommendations
    """
    service = SustainabilityService(db)
    
    report = service.get_sustainability_report(
        venue_id=venue_id,
        start_date=datetime.combine(start_date, datetime.min.time()),
        end_date=datetime.combine(end_date, datetime.max.time())
    )
    
    return report


@router.get("/vendors/sustainable")
@limiter.limit("60/minute")
def get_sustainable_vendors(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """
    Get list of sustainable/certified vendors
    
    Shows vendors with certifications like:
    - Organic
    - Fair Trade
    - Local
    - Free Range
    """
    service = SustainabilityService(db)
    
    vendors = service.get_sustainable_vendors(venue_id)
    
    return {
        'vendors': vendors,
        'count': len(vendors)
    }


@router.post("/energy/log")
@limiter.limit("30/minute")
def log_energy_usage(
    request: Request,
    venue_id: int,
    date: date = Body(...),
    kwh_used: float = Body(...),
    source: str = Body(...),
    cost: Optional[Decimal] = Body(None),
    db: Session = Depends(get_db)
):
    """
    Log daily energy usage
    
    Track electricity consumption by source:
    - Grid
    - Solar
    - Other renewables
    """
    service = SustainabilityService(db)
    
    result = service.log_energy_usage(
        venue_id=venue_id,
        date=datetime.combine(date, datetime.min.time()),
        kwh_used=kwh_used,
        source=source,
        cost=cost
    )
    
    return {
        'success': True,
        'energy_log': result
    }


@router.get("/energy/statistics")
@limiter.limit("60/minute")
def get_energy_statistics(
    request: Request,
    venue_id: int,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get energy usage statistics
    
    Returns:
    - Total kWh consumed
    - Cost breakdown
    - CO2 emissions from energy use
    - Usage by source (grid vs solar)
    """
    service = SustainabilityService(db)
    
    stats = service.get_energy_statistics(
        venue_id=venue_id,
        start_date=datetime.combine(start_date, datetime.min.time()),
        end_date=datetime.combine(end_date, datetime.max.time())
    )
    
    return stats


@router.get("/recommendations")
@limiter.limit("60/minute")
def get_sustainability_recommendations(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """
    Get personalized sustainability recommendations
    
    AI-generated suggestions for:
    - Menu optimization
    - Waste reduction
    - Energy efficiency
    - Sustainable sourcing
    """
    service = SustainabilityService(db)
    
    recommendations = service.get_sustainability_recommendations(venue_id)
    
    return {
        'recommendations': recommendations,
        'count': len(recommendations)
    }


@router.get("/dashboard")
@limiter.limit("60/minute")
def get_sustainability_dashboard(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """
    Get sustainability dashboard data
    
    Quick overview of all sustainability metrics
    """
    service = SustainabilityService(db)
    
    # Get last 30 days report
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    report = service.get_sustainability_report(
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date
    )
    
    energy_stats = service.get_energy_statistics(
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date
    )
    
    recommendations = service.get_sustainability_recommendations(venue_id)
    
    return {
        'overview': {
            'sustainability_score': report['sustainability_score'],
            'total_co2_kg': report['carbon_footprint']['total_kg'],
            'total_waste_kg': report['waste']['totals']['weight_kg'],
            'energy_kwh': energy_stats['totals']['kwh']
        },
        'carbon_footprint': report['carbon_footprint'],
        'waste': report['waste'],
        'energy': energy_stats,
        'top_recommendations': recommendations[:3],
        'period_days': 30
    }


@router.get("/compare")
@limiter.limit("60/minute")
def compare_sustainability(
    request: Request,
    venue_id: int,
    period1_start: date = Query(...),
    period1_end: date = Query(...),
    period2_start: date = Query(...),
    period2_end: date = Query(...),
    db: Session = Depends(get_db)
):
    """
    Compare sustainability metrics between two periods
    
    Useful for tracking improvement over time
    """
    service = SustainabilityService(db)
    
    report1 = service.get_sustainability_report(
        venue_id=venue_id,
        start_date=datetime.combine(period1_start, datetime.min.time()),
        end_date=datetime.combine(period1_end, datetime.max.time())
    )
    
    report2 = service.get_sustainability_report(
        venue_id=venue_id,
        start_date=datetime.combine(period2_start, datetime.min.time()),
        end_date=datetime.combine(period2_end, datetime.max.time())
    )
    
    # Calculate changes
    co2_change = ((report2['carbon_footprint']['total_kg'] / 
                   max(1, report1['carbon_footprint']['total_kg'])) - 1) * 100
    
    waste_change = ((report2['waste']['totals']['weight_kg'] / 
                    max(1, report1['waste']['totals']['weight_kg'])) - 1) * 100
    
    score_change = (report2['sustainability_score']['score'] - 
                   report1['sustainability_score']['score'])
    
    return {
        'period1': {
            'start': period1_start.isoformat(),
            'end': period1_end.isoformat(),
            'report': report1
        },
        'period2': {
            'start': period2_start.isoformat(),
            'end': period2_end.isoformat(),
            'report': report2
        },
        'changes': {
            'co2_change_percent': round(co2_change, 1),
            'waste_change_percent': round(waste_change, 1),
            'score_change': score_change,
            'improvement': score_change > 0
        }
    }


@router.get("/certificates")
@limiter.limit("60/minute")
def get_sustainability_certificates(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """
    Get sustainability certifications and badges
    
    Based on achieved metrics:
    - Green Restaurant Badge
    - Waste Reduction Certificate
    - Carbon Neutral Progress
    """
    service = SustainabilityService(db)
    
    # Get current report
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    report = service.get_sustainability_report(
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date
    )
    
    score = report['sustainability_score']['score']
    
    certificates = []
    
    if score >= 80:
        certificates.append({
            'name': '🌟 Green Restaurant Excellence',
            'description': 'Outstanding sustainability performance',
            'earned': True,
            'date_earned': datetime.now().date().isoformat()
        })
    
    if score >= 60:
        certificates.append({
            'name': '🌱 Eco-Friendly Certified',
            'description': 'Commitment to sustainable practices',
            'earned': True,
            'date_earned': datetime.now().date().isoformat()
        })
    
    if report['waste']['totals']['weight_kg'] < 100:
        certificates.append({
            'name': '♻️ Waste Warrior',
            'description': 'Exceptional waste reduction',
            'earned': True,
            'date_earned': datetime.now().date().isoformat()
        })
    
    certificates.append({
        'name': '🌍 Carbon Neutral 2026',
        'description': 'Working towards carbon neutrality',
        'earned': False,
        'progress': min(100, score)
    })
    
    return {
        'certificates': certificates,
        'total_earned': len([c for c in certificates if c.get('earned')]),
        'sustainability_score': score
    }
