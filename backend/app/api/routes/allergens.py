"""
Allergen & Nutrition API Endpoints
Complete allergen tracking, nutrition info, and HACCP compliance
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.services.allergen_nutrition_service import AllergenNutritionService


router = APIRouter()


# ========== SCHEMAS ==========

class SetAllergensRequest(BaseModel):
    allergens: List[str]
    may_contain: Optional[List[str]] = None
    cross_contamination_risk: Optional[str] = None


class SetNutritionRequest(BaseModel):
    serving_size: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None
    sugar_g: Optional[float] = None
    sodium_mg: Optional[float] = None
    saturated_fat_g: Optional[float] = None
    cholesterol_mg: Optional[float] = None
    vitamins: Optional[dict] = None
    minerals: Optional[dict] = None


class SetDietaryTagsRequest(BaseModel):
    dietary_types: List[str]
    certifications: Optional[List[str]] = None


class CheckAllergenRequest(BaseModel):
    customer_allergens: List[str]


class LogTemperatureRequest(BaseModel):
    equipment_id: str
    equipment_type: str
    temperature_c: float
    is_acceptable: bool
    notes: Optional[str] = None


class LogHACCPEventRequest(BaseModel):
    event_type: str
    description: str
    is_compliant: bool
    corrective_action: Optional[str] = None
    attachments: Optional[List[str]] = None


class FilterMenuRequest(BaseModel):
    dietary_requirements: List[str]
    allergen_exclusions: Optional[List[str]] = None


# ========== ALLERGEN ENDPOINTS ==========

@router.post("/items/{menu_item_id}/allergens")
async def set_item_allergens(
    menu_item_id: int,
    request: SetAllergensRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Set allergen information for a menu item
    
    Allergens (EU 14 major):
    - celery, cereals_gluten, crustaceans, eggs, fish, lupin
    - milk, molluscs, mustard, nuts, peanuts, sesame, soybeans, sulphites
    """
    service = AllergenNutritionService(db)
    
    result = service.set_item_allergens(
        menu_item_id=menu_item_id,
        allergens=request.allergens,
        may_contain=request.may_contain,
        cross_contamination_risk=request.cross_contamination_risk,
        staff_id=current_user.id if current_user else None
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to set allergens")
        )
    
    return result


@router.get("/items/{menu_item_id}/allergens")
async def get_item_allergens(
    menu_item_id: int,
    language: str = "en",
    db: Session = Depends(get_db)
):
    """Get allergen information for a menu item"""
    service = AllergenNutritionService(db)
    result = service.get_item_allergens(menu_item_id, language)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result.get("error", "Item not found")
        )
    
    return result


@router.post("/orders/{order_id}/check-allergens")
async def check_order_allergens(
    order_id: int,
    request: CheckAllergenRequest,
    language: str = "en",
    db: Session = Depends(get_db)
):
    """
    Check an order against customer's allergens
    
    Returns warnings for any items containing customer's allergens
    """
    service = AllergenNutritionService(db)
    
    result = service.check_order_allergens(
        order_id=order_id,
        customer_allergens=request.customer_allergens,
        language=language
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to check allergens")
        )
    
    return result


# ========== NUTRITION ENDPOINTS ==========

@router.post("/items/{menu_item_id}/nutrition")
async def set_nutrition_info(
    menu_item_id: int,
    request: SetNutritionRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Set nutrition information for a menu item
    
    Includes calories, macros (protein, carbs, fat), and optional micronutrients
    """
    service = AllergenNutritionService(db)
    
    result = service.set_nutrition_info(
        menu_item_id=menu_item_id,
        serving_size=request.serving_size,
        calories=request.calories,
        protein_g=request.protein_g,
        carbs_g=request.carbs_g,
        fat_g=request.fat_g,
        fiber_g=request.fiber_g,
        sugar_g=request.sugar_g,
        sodium_mg=request.sodium_mg,
        saturated_fat_g=request.saturated_fat_g,
        cholesterol_mg=request.cholesterol_mg,
        vitamins=request.vitamins,
        minerals=request.minerals,
        staff_id=current_user.id if current_user else None
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to set nutrition")
        )
    
    return result


@router.get("/items/{menu_item_id}/nutrition")
async def get_nutrition_info(
    menu_item_id: int,
    include_recommendations: bool = True,
    db: Session = Depends(get_db)
):
    """Get nutrition information for a menu item"""
    service = AllergenNutritionService(db)
    return service.get_nutrition_info(menu_item_id, include_recommendations)


@router.get("/orders/{order_id}/nutrition")
async def calculate_order_nutrition(
    order_id: int,
    db: Session = Depends(get_db)
):
    """Calculate total nutrition for an entire order"""
    service = AllergenNutritionService(db)
    result = service.calculate_order_nutrition(order_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to calculate nutrition")
        )
    
    return result


# ========== DIETARY TAGS ENDPOINTS ==========

@router.post("/items/{menu_item_id}/dietary")
async def set_dietary_tags(
    menu_item_id: int,
    request: SetDietaryTagsRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Set dietary tags for a menu item
    
    Types: vegetarian, vegan, pescatarian, halal, kosher, gluten_free, dairy_free, etc.
    """
    service = AllergenNutritionService(db)
    
    result = service.set_dietary_tags(
        menu_item_id=menu_item_id,
        dietary_types=request.dietary_types,
        certifications=request.certifications,
        staff_id=current_user.id if current_user else None
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to set dietary tags")
        )
    
    return result


@router.post("/menu/filter")
async def filter_menu_by_dietary(
    request: FilterMenuRequest,
    venue_id: int = Query(1, description="Venue ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Filter menu items by dietary requirements and allergen exclusions"""
    service = AllergenNutritionService(db)

    # Use venue_id from current_user if available, otherwise use query param
    actual_venue_id = current_user.venue_id if current_user and hasattr(current_user, 'venue_id') else venue_id

    return service.filter_menu_by_dietary(
        venue_id=actual_venue_id,
        dietary_requirements=request.dietary_requirements,
        allergen_exclusions=request.allergen_exclusions
    )


# ========== HACCP COMPLIANCE ENDPOINTS ==========

@router.post("/haccp/temperature")
async def log_temperature_check(
    request: LogTemperatureRequest,
    venue_id: int = Query(1, description="Venue ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Log a temperature check for HACCP compliance

    Equipment types: fridge, freezer, hot_hold, prep_station
    """
    service = AllergenNutritionService(db)

    # Use venue_id from current_user if available, otherwise use query param
    actual_venue_id = current_user.venue_id if current_user and hasattr(current_user, 'venue_id') else venue_id

    result = service.log_temperature_check(
        venue_id=actual_venue_id,
        equipment_id=request.equipment_id,
        equipment_type=request.equipment_type,
        temperature_c=request.temperature_c,
        is_acceptable=request.is_acceptable,
        staff_id=current_user.id if current_user else None,
        notes=request.notes
    )

    return result


@router.post("/haccp/event")
async def log_haccp_event(
    request: LogHACCPEventRequest,
    venue_id: int = Query(1, description="Venue ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Log a HACCP compliance event

    Event types: delivery_check, cooking_temp, cooling_log, cleaning, pest_control
    """
    service = AllergenNutritionService(db)

    # Use venue_id from current_user if available, otherwise use query param
    actual_venue_id = current_user.venue_id if current_user and hasattr(current_user, 'venue_id') else venue_id

    result = service.log_haccp_event(
        venue_id=actual_venue_id,
        event_type=request.event_type,
        description=request.description,
        staff_id=current_user.id if current_user else None,
        is_compliant=request.is_compliant,
        corrective_action=request.corrective_action,
        attachments=request.attachments
    )

    return result


@router.get("/haccp/report")
async def get_haccp_report(
    start_date: datetime,
    end_date: datetime,
    venue_id: int = Query(1, description="Venue ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate HACCP compliance report for a date range"""
    service = AllergenNutritionService(db)

    # Use venue_id from current_user if available, otherwise use query param
    actual_venue_id = current_user.venue_id if current_user and hasattr(current_user, 'venue_id') else venue_id

    return service.get_haccp_report(venue_id=actual_venue_id, start_date=start_date, end_date=end_date)


# ========== UTILITY ENDPOINTS ==========

@router.get("/allergen-list")
async def get_allergen_list(
    language: str = "en"
):
    """Get list of all 14 major allergens with translations"""
    service = AllergenNutritionService(None)
    
    allergens = []
    for code, translations in service.ALLERGEN_TRANSLATIONS.items():
        allergens.append({
            "code": code,
            "name": translations.get(language, translations.get("en")),
            "icon": service.ALLERGEN_ICONS.get(code, "⚠️")
        })
    
    return {"allergens": allergens}


@router.get("/dietary-types")
async def get_dietary_types():
    """Get list of all dietary types"""
    return {
        "dietary_types": [
            {"code": "vegetarian", "name": "Vegetarian", "icon": "🥗"},
            {"code": "vegan", "name": "Vegan", "icon": "🌱"},
            {"code": "pescatarian", "name": "Pescatarian", "icon": "🐟"},
            {"code": "halal", "name": "Halal", "icon": "☪️"},
            {"code": "kosher", "name": "Kosher", "icon": "✡️"},
            {"code": "gluten_free", "name": "Gluten Free", "icon": "🌾"},
            {"code": "dairy_free", "name": "Dairy Free", "icon": "🥛"},
            {"code": "low_carb", "name": "Low Carb", "icon": "📉"},
            {"code": "keto", "name": "Keto", "icon": "🥓"},
            {"code": "paleo", "name": "Paleo", "icon": "🍖"}
        ]
    }
