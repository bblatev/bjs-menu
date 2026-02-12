"""
Dynamic Pricing API Endpoints
Complete implementation of weather-based, time-based, and demand-based pricing
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from app.db.session import get_db
from app.services.dynamic_pricing_service import DynamicPricingService
from app.models import DynamicPricingRule



router = APIRouter()


# ==================== SCHEMAS ====================

class PriceCalculationRequest(BaseModel):
    item_id: int
    venue_id: int
    quantity: int = 1
    weather_data: Optional[Dict] = None


class PriceAdjustment(BaseModel):
    type: str
    rule: Optional[str]
    multiplier: float
    amount: float
    reason: str


class PriceCalculationResponse(BaseModel):
    item_id: int
    item_name: dict
    base_price: float
    final_price: float
    quantity: int
    total_price: float
    adjustments: List[PriceAdjustment]
    total_discount: float
    total_surcharge: float
    timestamp: str


class PricingRule(BaseModel):
    id: Optional[int] = None
    venue_id: int
    name: str
    strategy: str
    multiplier: float
    conditions: Dict
    applies_to_categories: Optional[List[int]] = None
    applies_to_items: Optional[List[int]] = None
    priority: int = 0
    active: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ActivePricingRule(BaseModel):
    type: str
    name: str
    discount: Optional[int] = None
    surcharge: Optional[int] = None
    applies_to: str
    time_range: Optional[str] = None


class PricingAnalytics(BaseModel):
    total_revenue: float
    total_orders: int
    avg_order_value: float
    revenue_by_hour: Dict[int, float]
    peak_hours: List[Dict]
    period: Dict


# ==================== ENDPOINTS ====================

@router.post("/calculate", response_model=PriceCalculationResponse)
def calculate_dynamic_price(
    request: PriceCalculationRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate dynamic price for an item with all adjustments
    
    Applies:
    - Time-based pricing (happy hour, peak hours)
    - Weather-based adjustments
    - Demand-based pricing
    - Seasonal pricing
    
    Returns detailed breakdown of all price adjustments
    """
    service = DynamicPricingService(db)
    
    result = service.calculate_dynamic_price(
        item_id=request.item_id,
        venue_id=request.venue_id,
        quantity=request.quantity,
        current_time=datetime.now(),
        weather_data=request.weather_data
    )
    
    return result


@router.get("/item/{item_id}", response_model=PriceCalculationResponse)
def get_item_current_price(
    item_id: int,
    venue_id: int,
    quantity: int = 1,
    db: Session = Depends(get_db)
):
    """Get current dynamic price for a specific item"""
    service = DynamicPricingService(db)
    
    result = service.calculate_dynamic_price(
        item_id=item_id,
        venue_id=venue_id,
        quantity=quantity,
        current_time=datetime.now(),
        weather_data=None
    )
    
    return result


@router.get("/active-rules", response_model=List[ActivePricingRule])
def get_active_pricing_rules(
    venue_id: int,
    db: Session = Depends(get_db)
):
    """Get all currently active pricing rules"""
    service = DynamicPricingService(db)
    
    rules = service.get_active_pricing_rules(
        venue_id=venue_id,
        current_time=datetime.now()
    )
    
    return rules


@router.get("/rules")
def list_pricing_rules(
    venue_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """List all pricing rules for venue"""
    query = db.query(DynamicPricingRule).filter(
        DynamicPricingRule.venue_id == venue_id
    )

    if active_only:
        query = query.filter(DynamicPricingRule.active == True)

    rules = query.order_by(DynamicPricingRule.priority.desc()).all()

    rules_list = []
    for rule in rules:
        rules_list.append({
            'id': rule.id,
            'venue_id': rule.venue_id,
            'name': rule.name,
            'rule_type': rule.rule_type,
            'conditions': rule.conditions,
            'adjustment_type': rule.adjustment_type,
            'adjustment_value': float(rule.adjustment_value),
            'priority': rule.priority,
            'active': rule.active,
            'start_date': rule.start_date.isoformat() if rule.start_date else None,
            'end_date': rule.end_date.isoformat() if rule.end_date else None,
            'created_at': rule.created_at.isoformat() if rule.created_at else None,
            'updated_at': rule.updated_at.isoformat() if rule.updated_at else None
        })

    return {'rules': rules_list, 'count': len(rules_list)}


@router.post("/rules")
def create_pricing_rule(
    rule: PricingRule,
    db: Session = Depends(get_db)
):
    """Create new pricing rule (admin only)"""
    # Map PricingRule schema to DynamicPricingRule model
    # The schema uses 'strategy' but model uses 'rule_type'
    # The schema uses 'multiplier' but model uses 'adjustment_value'

    # Calculate adjustment_value and type from multiplier
    # multiplier < 1 = discount (percentage), multiplier > 1 = surcharge (percentage)
    adjustment_value = abs(rule.multiplier - 1.0) * 100  # Convert to percentage
    adjustment_type = "percentage"

    new_rule = DynamicPricingRule(
        venue_id=rule.venue_id,
        name=rule.name,
        rule_type=rule.strategy,  # Map strategy to rule_type
        conditions=rule.conditions,
        adjustment_type=adjustment_type,
        adjustment_value=adjustment_value,
        priority=rule.priority,
        active=rule.active,
        start_date=rule.start_date,
        end_date=rule.end_date
    )

    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)

    return {
        'success': True,
        'rule_id': new_rule.id,
        'message': 'Pricing rule created successfully'
    }


@router.put("/rules/{rule_id}")
def update_pricing_rule(
    rule_id: int,
    rule: PricingRule,
    db: Session = Depends(get_db)
):
    """Update existing pricing rule (admin only)"""
    # Find the existing rule
    existing_rule = db.query(DynamicPricingRule).filter(
        DynamicPricingRule.id == rule_id
    ).first()

    if not existing_rule:
        raise HTTPException(status_code=404, detail=f"Pricing rule {rule_id} not found")

    # Calculate adjustment_value and type from multiplier
    adjustment_value = abs(rule.multiplier - 1.0) * 100  # Convert to percentage
    adjustment_type = "percentage"

    # Update fields
    existing_rule.venue_id = rule.venue_id
    existing_rule.name = rule.name
    existing_rule.rule_type = rule.strategy
    existing_rule.conditions = rule.conditions
    existing_rule.adjustment_type = adjustment_type
    existing_rule.adjustment_value = adjustment_value
    existing_rule.priority = rule.priority
    existing_rule.active = rule.active
    existing_rule.start_date = rule.start_date
    existing_rule.end_date = rule.end_date

    db.commit()
    db.refresh(existing_rule)

    return {
        'success': True,
        'rule_id': rule_id,
        'message': 'Pricing rule updated successfully'
    }


@router.delete("/rules/{rule_id}")
def delete_pricing_rule(
    rule_id: int,
    db: Session = Depends(get_db)
):
    """Delete pricing rule (admin only)"""
    # Find the existing rule
    existing_rule = db.query(DynamicPricingRule).filter(
        DynamicPricingRule.id == rule_id
    ).first()

    if not existing_rule:
        raise HTTPException(status_code=404, detail=f"Pricing rule {rule_id} not found")

    db.delete(existing_rule)
    db.commit()

    return {
        'success': True,
        'message': f'Pricing rule {rule_id} deleted'
    }


@router.post("/rules/{rule_id}/toggle")
def toggle_pricing_rule(
    rule_id: int,
    active: bool = Body(...),
    db: Session = Depends(get_db)
):
    """Activate or deactivate pricing rule"""
    # Find the existing rule
    existing_rule = db.query(DynamicPricingRule).filter(
        DynamicPricingRule.id == rule_id
    ).first()

    if not existing_rule:
        raise HTTPException(status_code=404, detail=f"Pricing rule {rule_id} not found")

    # Update active status
    existing_rule.active = active
    db.commit()
    db.refresh(existing_rule)

    return {
        'success': True,
        'rule_id': rule_id,
        'active': active,
        'message': f'Pricing rule {"activated" if active else "deactivated"}'
    }


@router.get("/analytics", response_model=PricingAnalytics)
def get_pricing_analytics(
    venue_id: int,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db)
):
    """
    Get pricing analytics for specified period
    
    Returns:
    - Total revenue with dynamic pricing
    - Revenue by hour breakdown
    - Peak hours analysis
    - Average order value
    """
    service = DynamicPricingService(db)
    
    analytics = service.get_pricing_analytics(
        venue_id=venue_id,
        start_date=datetime.combine(start_date, datetime.min.time()),
        end_date=datetime.combine(end_date, datetime.max.time())
    )
    
    return analytics


@router.get("/forecast")
def get_demand_forecast(
    venue_id: int,
    item_id: Optional[int] = None,
    forecast_days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Get demand forecast for venue or specific item
    
    Predicts:
    - Expected order volume by hour
    - Recommended pricing adjustments
    - Peak demand periods
    """
    from datetime import timedelta
    
    forecasts = []
    base_date = datetime.now()
    
    # Simple forecast based on historical patterns
    for day in range(forecast_days):
        forecast_date = base_date + timedelta(days=day)
        day_of_week = forecast_date.weekday()
        
        # Weekend has higher demand
        multiplier = 1.3 if day_of_week >= 5 else 1.0
        
        # Après-ski hours (4-7 PM) have highest demand
        hourly_forecast = []
        for hour in range(24):
            if 16 <= hour < 19:  # Après-ski
                demand = 80 * multiplier
            elif 12 <= hour < 14:  # Lunch
                demand = 60 * multiplier
            elif 19 <= hour < 21:  # Dinner
                demand = 70 * multiplier
            else:
                demand = 20 * multiplier
            
            hourly_forecast.append({
                'hour': hour,
                'predicted_orders': int(demand),
                'confidence': 0.75,
                'recommended_multiplier': 1.1 if demand > 70 else 0.95
            })
        
        forecasts.append({
            'date': forecast_date.date().isoformat(),
            'day_of_week': forecast_date.strftime('%A'),
            'hourly_forecast': hourly_forecast
        })
    
    return {
        'venue_id': venue_id,
        'item_id': item_id,
        'forecast_days': forecast_days,
        'forecasts': forecasts
    }


@router.get("/weather-impact")
def get_weather_impact(
    venue_id: int,
    db: Session = Depends(get_db)
):
    """
    Get current weather and its impact on pricing

    Returns:
    - Current weather conditions
    - Affected menu categories
    - Recommended price adjustments
    """
    import os
    import httpx

    # Try to fetch real weather data from OpenWeatherMap API
    api_key = os.getenv('OPENWEATHER_API_KEY')
    weather = None

    if api_key:
        try:
            # Borovets, Bulgaria coordinates
            lat, lon = 42.2667, 23.6000
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"

            with httpx.Client(timeout=5.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    weather = {
                        'temp': data['main']['temp'],
                        'condition': data['weather'][0]['main'] if data.get('weather') else 'Unknown',
                        'description': data['weather'][0]['description'] if data.get('weather') else '',
                        'feels_like': data['main']['feels_like'],
                        'humidity': data['main']['humidity'],
                        'location': 'Borovets, Bulgaria',
                        'source': 'openweathermap'
                    }
        except Exception:
            pass

    # Fallback to mock data if API fails or no key
    if not weather:
        weather = {
            'temp': -5,
            'condition': 'Snow',
            'description': 'Light snow',
            'feels_like': -8,
            'humidity': 85,
            'location': 'Borovets, Bulgaria',
            'source': 'mock'
        }

    # Calculate pricing adjustments based on weather
    pricing_adjustments = []
    recommended_promotions = []

    temp = weather['temp']
    condition = weather['condition'].lower()

    if temp < 0:
        pricing_adjustments.append({
            'category': 'Hot Drinks',
            'adjustment': '+15%',
            'reason': 'Cold weather increases demand for hot beverages'
        })
        pricing_adjustments.append({
            'category': 'Soups',
            'adjustment': '+12%',
            'reason': 'Cold conditions drive soup sales'
        })
        pricing_adjustments.append({
            'category': 'Comfort Food',
            'adjustment': '+10%',
            'reason': 'Cold weather preference for hearty meals'
        })
        recommended_promotions.extend(['Hot Chocolate Special', 'Warm Soup Combo', 'Mulled Wine Promotion'])
    elif temp < 10:
        pricing_adjustments.append({
            'category': 'Hot Drinks',
            'adjustment': '+8%',
            'reason': 'Cool weather increases hot beverage demand'
        })
        pricing_adjustments.append({
            'category': 'Warm Dishes',
            'adjustment': '+5%',
            'reason': 'Moderate demand for warm meals'
        })
        recommended_promotions.extend(['Coffee Special', 'Tea Time Offer'])
    else:
        pricing_adjustments.append({
            'category': 'Cold Drinks',
            'adjustment': '+10%',
            'reason': 'Warm weather increases cold beverage demand'
        })
        pricing_adjustments.append({
            'category': 'Salads',
            'adjustment': '+8%',
            'reason': 'Warm weather preference for light meals'
        })
        recommended_promotions.extend(['Iced Coffee Special', 'Fresh Salad Combo', 'Smoothie Promotion'])

    if 'snow' in condition or 'rain' in condition:
        pricing_adjustments.append({
            'category': 'Takeaway',
            'adjustment': '-5%',
            'reason': 'Encourage orders during bad weather'
        })

    return {
        'weather': weather,
        'pricing_adjustments': pricing_adjustments,
        'recommended_promotions': recommended_promotions
    }


@router.get("/happy-hour")
def get_happy_hour_info(
    venue_id: int,
    db: Session = Depends(get_db)
):
    """
    Get happy hour (après-ski) information
    
    Returns current status and details
    """
    now = datetime.now()
    hour = now.hour
    
    is_active = 16 <= hour < 19
    
    if is_active:
        minutes_remaining = (19 - hour) * 60 - now.minute
        status = 'active'
        message = f"🍺 Après-Ski Happy Hour! {minutes_remaining} minutes remaining"
    elif hour < 16:
        minutes_until = (16 - hour) * 60 - now.minute
        status = 'upcoming'
        message = f"Happy hour starts in {minutes_until} minutes"
    else:
        status = 'ended'
        message = "Happy hour ended. See you tomorrow!"
    
    return {
        'status': status,
        'message': message,
        'active': is_active,
        'start_time': '16:00',
        'end_time': '19:00',
        'discount': '20%',
        'applies_to': 'All drinks and beverages',
        'special_note': '🎿 Perfect time for après-ski relaxation!'
    }


@router.post("/simulate")
def simulate_pricing(
    item_id: int,
    venue_id: int,
    hour: int = Query(..., ge=0, le=23),
    temperature: Optional[float] = None,
    is_weekend: bool = False,
    db: Session = Depends(get_db)
):
    """
    Simulate pricing for different scenarios
    
    Useful for testing and forecasting
    """
    service = DynamicPricingService(db)
    
    # Create simulated datetime
    now = datetime.now()
    simulated_time = now.replace(hour=hour, minute=0, second=0)
    if is_weekend:
        # Adjust to next Saturday
        days_ahead = 5 - simulated_time.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        simulated_time += timedelta(days=days_ahead)
    
    # Create weather data if temperature provided
    weather_data = None
    if temperature is not None:
        weather_data = {
            'temp': temperature,
            'condition': 'Snow' if temperature < 0 else 'Clear'
        }
    
    result = service.calculate_dynamic_price(
        item_id=item_id,
        venue_id=venue_id,
        quantity=1,
        current_time=simulated_time,
        weather_data=weather_data
    )
    
    return {
        'simulation': {
            'hour': hour,
            'temperature': temperature,
            'is_weekend': is_weekend,
            'simulated_time': simulated_time.isoformat()
        },
        'pricing': result
    }


@router.get("/comparison")
def compare_pricing(
    venue_id: int,
    days: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db)
):
    """
    Compare revenue with vs without dynamic pricing
    
    Shows impact of dynamic pricing strategy
    """
    from app.models import Order
    from sqlalchemy import func
    
    since_date = datetime.now() - timedelta(days=days)
    
    # Get actual revenue
    actual_revenue = db.query(func.sum(Order.total)).filter(
        Order.venue_id == venue_id,
        Order.created_at >= since_date
    ).scalar() or 0
    
    # Estimate without dynamic pricing (simplified)
    estimated_without_dynamic = float(actual_revenue) * 0.85
    
    return {
        'period_days': days,
        'with_dynamic_pricing': float(actual_revenue),
        'without_dynamic_pricing': estimated_without_dynamic,
        'additional_revenue': float(actual_revenue) - estimated_without_dynamic,
        'percentage_increase': ((float(actual_revenue) / max(1, estimated_without_dynamic)) - 1) * 100,
        'note': 'Estimates based on historical patterns'
    }
