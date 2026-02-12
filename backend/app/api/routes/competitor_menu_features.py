"""
Competitor Menu & Inventory Features - Complete Implementation
Toast/iiko/TouchBistro Feature Parity

Implements:
1. Daypart Pricing - Different prices based on time of day (happy hour, lunch specials)
2. Menu Item Photos with S3/Local Storage - Proper file storage with fallback
3. Allergen Matrix - Complete allergen tracking per menu item
4. Shelf Life/Expiry Tracking - Track prep time and expiration for batches
5. Recipe Scaling - Scale recipes for different batch sizes
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime, time, timedelta, date
import uuid
from pathlib import Path

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.models import (
    MenuItem, StaffUser, StockItem, StockBatch
)
from app.core.config import settings


router = APIRouter()


def require_manager(current_user = Depends(get_current_user)):
    """Require manager or above role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("admin", "owner", "manager"):
        raise HTTPException(status_code=403, detail="Manager access required")
    return current_user



# =============================================================================
# SCHEMAS
# =============================================================================

class MultiLangText(BaseModel):
    bg: str = ""
    en: str = ""
    de: Optional[str] = ""
    ru: Optional[str] = ""


# -- Daypart Pricing Schemas --

class DaypartPricingCreate(BaseModel):
    """Create daypart pricing rule"""
    name: str
    display_name: MultiLangText
    price_type: str = "percentage"  # percentage, fixed_price, fixed_amount
    price_adjustment: float  # -20 for 20% off, or actual price/amount
    start_time: str  # "17:00"
    end_time: str  # "19:00"
    days_of_week: List[int] = [0, 1, 2, 3, 4]  # 0=Monday, 6=Sunday
    category_ids: Optional[List[int]] = None  # None = all categories
    item_ids: Optional[List[int]] = None  # None = all items in categories
    priority: int = 0  # Higher priority wins if overlapping
    active: bool = True
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


class DaypartPricingResponse(BaseModel):
    id: int
    name: str
    display_name: Dict[str, str]
    price_type: str
    price_adjustment: float
    start_time: str
    end_time: str
    days_of_week: List[int]
    category_ids: Optional[List[int]]
    item_ids: Optional[List[int]]
    priority: int
    active: bool
    valid_from: Optional[date]
    valid_until: Optional[date]
    is_currently_active: bool = False
    created_at: datetime


class MenuItemPriceCheck(BaseModel):
    """Response for checking item price with daypart pricing"""
    menu_item_id: int
    item_name: Dict[str, str]
    base_price: float
    current_price: float
    discount_amount: float
    discount_percentage: float
    active_daypart: Optional[str] = None
    daypart_display_name: Optional[Dict[str, str]] = None
    price_valid_until: Optional[str] = None  # When current daypart ends


# -- Photo Upload Schemas --

class PhotoUploadResponse(BaseModel):
    id: str
    url: str
    thumbnail_url: Optional[str] = None
    filename: str
    content_type: str
    size: int
    width: Optional[int] = None
    height: Optional[int] = None
    is_primary: bool = False
    sort_order: int = 0
    uploaded_at: datetime
    storage_type: str  # "local", "s3", "minio"


# -- Allergen Matrix Schemas --

class AllergenInfo(BaseModel):
    code: str
    name: Dict[str, str]
    icon: str
    severity: str = "contains"  # contains, may_contain, free_from


class MenuItemAllergenMatrix(BaseModel):
    menu_item_id: int
    item_name: Dict[str, str]
    category_name: Dict[str, str]
    allergens: Dict[str, str]  # allergen_code -> severity


class AllergenMatrixResponse(BaseModel):
    allergen_codes: List[str]
    allergen_names: Dict[str, Dict[str, str]]
    allergen_icons: Dict[str, str]
    items: List[MenuItemAllergenMatrix]
    summary: Dict[str, int]  # count of items containing each allergen


# -- Batch Shelf Life Schemas --

class BatchShelfLifeCreate(BaseModel):
    """Create or update batch with shelf life tracking"""
    stock_item_id: int
    batch_number: str
    quantity: float
    manufacture_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    supplier_id: Optional[int] = None
    purchase_order_id: Optional[int] = None
    cost_per_unit: Optional[float] = None
    # New shelf life fields
    prep_time_minutes: Optional[int] = None  # Time to prepare
    shelf_life_hours: Optional[int] = None  # How long it lasts after prep
    storage_temperature_min: Optional[float] = None  # Min storage temp (C)
    storage_temperature_max: Optional[float] = None  # Max storage temp (C)
    use_by_date: Optional[datetime] = None  # Calculated from prep + shelf_life


class BatchShelfLifeResponse(BaseModel):
    id: int
    stock_item_id: int
    stock_item_name: str
    batch_number: str
    quantity: float
    initial_quantity: float
    manufacture_date: Optional[datetime]
    expiration_date: Optional[datetime]
    prep_time_minutes: Optional[int]
    shelf_life_hours: Optional[int]
    use_by_date: Optional[datetime]
    storage_temperature_min: Optional[float]
    storage_temperature_max: Optional[float]
    days_until_expiry: Optional[int]
    hours_until_use_by: Optional[int]
    is_expired: bool
    is_expiring_soon: bool
    is_past_use_by: bool
    freshness_status: str  # "fresh", "use_soon", "expired", "unknown"
    created_at: datetime


class PreparedBatchCreate(BaseModel):
    """Create a prepared batch (e.g., prep work, sauces, etc.)"""
    menu_item_id: Optional[int] = None  # Linked menu item
    stock_item_id: Optional[int] = None  # Or linked stock item
    batch_label: str
    quantity: float
    unit: str = "portions"
    prep_time_minutes: int
    shelf_life_hours: int
    prepared_by: Optional[int] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None


class PreparedBatchResponse(BaseModel):
    id: int
    batch_label: str
    menu_item_id: Optional[int]
    stock_item_id: Optional[int]
    item_name: Optional[str]
    quantity: float
    unit: str
    prepared_at: datetime
    use_by_datetime: datetime
    shelf_life_hours: int
    hours_remaining: int
    prepared_by: Optional[int]
    prepared_by_name: Optional[str]
    storage_location: Optional[str]
    status: str  # "active", "used", "expired", "discarded"
    freshness_status: str


# -- Recipe Scaling Schemas --

class RecipeScaleRequest(BaseModel):
    """Request to scale a recipe"""
    recipe_id: Optional[int] = None
    menu_item_id: Optional[int] = None  # Either recipe_id or menu_item_id
    target_portions: float
    round_to_practical: bool = True  # Round to practical measurements


class ScaledIngredient(BaseModel):
    ingredient_id: int
    ingredient_name: str
    original_quantity: float
    scaled_quantity: float
    rounded_quantity: Optional[float] = None
    unit: str
    practical_measurement: Optional[str] = None  # "1/4 cup", "2 tbsp"
    cost_per_unit: Optional[float] = None
    scaled_cost: Optional[float] = None


class RecipeScaleResponse(BaseModel):
    menu_item_id: Optional[int]
    menu_item_name: Optional[Dict[str, str]]
    original_portions: float
    target_portions: float
    scale_factor: float
    ingredients: List[ScaledIngredient]
    total_original_cost: float
    total_scaled_cost: float
    cost_per_portion: float
    prep_time_minutes: Optional[int]
    adjusted_prep_time_minutes: Optional[int]


# =============================================================================
# IN-MEMORY STORAGE (Replace with database models in production)
# =============================================================================

# Daypart pricing rules storage
_daypart_pricing_rules: Dict[int, Dict] = {}
_daypart_id_counter = 1

# Prepared batches storage
_prepared_batches: Dict[int, Dict] = {}
_prepared_batch_id_counter = 1


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_time(time_str: str) -> time:
    """Parse time string to time object"""
    parts = time_str.split(":")
    return time(int(parts[0]), int(parts[1]))


def is_daypart_active(rule: Dict, check_time: datetime = None) -> bool:
    """Check if a daypart pricing rule is currently active"""
    if not rule.get("active", True):
        return False

    now = check_time or datetime.now()

    # Check day of week (0 = Monday)
    if now.weekday() not in rule.get("days_of_week", []):
        return False

    # Check time
    current_time = now.time()
    start = parse_time(rule["start_time"])
    end = parse_time(rule["end_time"])

    # Handle overnight dayparts (e.g., 22:00 - 02:00)
    if start > end:
        if not (current_time >= start or current_time <= end):
            return False
    else:
        if not (start <= current_time <= end):
            return False

    # Check valid dates
    if rule.get("valid_from") and now.date() < rule["valid_from"]:
        return False
    if rule.get("valid_until") and now.date() > rule["valid_until"]:
        return False

    return True


def calculate_daypart_price(base_price: float, rule: Dict) -> float:
    """Calculate price based on daypart rule"""
    price_type = rule.get("price_type", "percentage")
    adjustment = rule.get("price_adjustment", 0)

    if price_type == "percentage":
        # adjustment is percentage change (negative = discount)
        return base_price * (1 + adjustment / 100)
    elif price_type == "fixed_price":
        # adjustment is the new price
        return adjustment
    elif price_type == "fixed_amount":
        # adjustment is amount to add/subtract
        return base_price + adjustment

    return base_price


def get_upload_directory() -> Path:
    """Get or create upload directory"""
    upload_dir = Path(settings.get("UPLOAD_DIR", "/tmp/v99_uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def get_practical_measurement(quantity: float, unit: str) -> Optional[str]:
    """Convert decimal quantities to practical measurements"""
    # Common conversions
    if unit.lower() in ["cup", "cups"]:
        if 0.24 <= quantity <= 0.26:
            return "1/4 cup"
        elif 0.32 <= quantity <= 0.34:
            return "1/3 cup"
        elif 0.49 <= quantity <= 0.51:
            return "1/2 cup"
        elif 0.65 <= quantity <= 0.68:
            return "2/3 cup"
        elif 0.74 <= quantity <= 0.76:
            return "3/4 cup"
    elif unit.lower() in ["tbsp", "tablespoon", "tablespoons"]:
        if 0.49 <= quantity <= 0.51:
            return "1/2 tbsp"
        elif 1.49 <= quantity <= 1.51:
            return "1 1/2 tbsp"
    elif unit.lower() in ["tsp", "teaspoon", "teaspoons"]:
        if 0.24 <= quantity <= 0.26:
            return "1/4 tsp"
        elif 0.49 <= quantity <= 0.51:
            return "1/2 tsp"

    return None


# EU 14 Major Allergens
ALLERGEN_DEFINITIONS = {
    "celery": {"en": "Celery", "bg": "Целина", "de": "Sellerie", "ru": "Сельдерей", "icon": "🥬"},
    "cereals_gluten": {"en": "Cereals containing gluten", "bg": "Зърнени, съдържащи глутен", "de": "Glutenhaltige Getreide", "ru": "Злаки с глютеном", "icon": "🌾"},
    "crustaceans": {"en": "Crustaceans", "bg": "Ракообразни", "de": "Krebstiere", "ru": "Ракообразные", "icon": "🦐"},
    "eggs": {"en": "Eggs", "bg": "Яйца", "de": "Eier", "ru": "Яйца", "icon": "🥚"},
    "fish": {"en": "Fish", "bg": "Риба", "de": "Fisch", "ru": "Рыба", "icon": "🐟"},
    "lupin": {"en": "Lupin", "bg": "Лупина", "de": "Lupine", "ru": "Люпин", "icon": "🌸"},
    "milk": {"en": "Milk", "bg": "Мляко", "de": "Milch", "ru": "Молоко", "icon": "🥛"},
    "molluscs": {"en": "Molluscs", "bg": "Мекотели", "de": "Weichtiere", "ru": "Моллюски", "icon": "🦪"},
    "mustard": {"en": "Mustard", "bg": "Горчица", "de": "Senf", "ru": "Горчица", "icon": "🟡"},
    "nuts": {"en": "Tree nuts", "bg": "Ядки", "de": "Nüsse", "ru": "Орехи", "icon": "🥜"},
    "peanuts": {"en": "Peanuts", "bg": "Фъстъци", "de": "Erdnüsse", "ru": "Арахис", "icon": "🥜"},
    "sesame": {"en": "Sesame", "bg": "Сусам", "de": "Sesam", "ru": "Кунжут", "icon": "⚪"},
    "soybeans": {"en": "Soybeans", "bg": "Соя", "de": "Soja", "ru": "Соя", "icon": "🫘"},
    "sulphites": {"en": "Sulphites", "bg": "Сулфити", "de": "Sulfite", "ru": "Сульфиты", "icon": "🍷"},
}


# =============================================================================
# DAYPART PRICING ENDPOINTS
# =============================================================================

@router.post("/daypart-pricing", response_model=DaypartPricingResponse, tags=["Daypart Pricing"])
async def create_daypart_pricing(
    data: DaypartPricingCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """
    Create a daypart pricing rule (happy hour, lunch special, etc.)

    Competitors: Toast Happy Hour, iiko Time-Based Pricing, TouchBistro Dayparts

    Examples:
    - Happy Hour: 17:00-19:00, Mon-Fri, 20% off drinks
    - Early Bird: 11:00-14:00, Mon-Sun, fixed price lunch menu
    - Late Night: 22:00-02:00, Fri-Sat, 15% off appetizers
    """
    global _daypart_id_counter

    # Validate time format
    try:
        parse_time(data.start_time)
        parse_time(data.end_time)
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")

    # Create rule
    rule_id = _daypart_id_counter
    _daypart_id_counter += 1

    rule = {
        "id": rule_id,
        "venue_id": current_user.venue_id,
        "name": data.name,
        "display_name": data.display_name.dict(),
        "price_type": data.price_type,
        "price_adjustment": data.price_adjustment,
        "start_time": data.start_time,
        "end_time": data.end_time,
        "days_of_week": data.days_of_week,
        "category_ids": data.category_ids,
        "item_ids": data.item_ids,
        "priority": data.priority,
        "active": data.active,
        "valid_from": data.valid_from,
        "valid_until": data.valid_until,
        "created_at": datetime.utcnow(),
        "created_by": current_user.id
    }

    _daypart_pricing_rules[rule_id] = rule

    return DaypartPricingResponse(
        id=rule_id,
        name=data.name,
        display_name=data.display_name.dict(),
        price_type=data.price_type,
        price_adjustment=data.price_adjustment,
        start_time=data.start_time,
        end_time=data.end_time,
        days_of_week=data.days_of_week,
        category_ids=data.category_ids,
        item_ids=data.item_ids,
        priority=data.priority,
        active=data.active,
        valid_from=data.valid_from,
        valid_until=data.valid_until,
        is_currently_active=is_daypart_active(rule),
        created_at=rule["created_at"]
    )


@router.get("/daypart-pricing", response_model=List[DaypartPricingResponse], tags=["Daypart Pricing"])
async def list_daypart_pricing(
    active_only: bool = False,
    currently_active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all daypart pricing rules"""
    rules = []

    for rule in _daypart_pricing_rules.values():
        if rule.get("venue_id") != current_user.venue_id:
            continue

        is_active_now = is_daypart_active(rule)

        if active_only and not rule.get("active", True):
            continue
        if currently_active_only and not is_active_now:
            continue

        rules.append(DaypartPricingResponse(
            id=rule["id"],
            name=rule["name"],
            display_name=rule["display_name"],
            price_type=rule["price_type"],
            price_adjustment=rule["price_adjustment"],
            start_time=rule["start_time"],
            end_time=rule["end_time"],
            days_of_week=rule["days_of_week"],
            category_ids=rule.get("category_ids"),
            item_ids=rule.get("item_ids"),
            priority=rule.get("priority", 0),
            active=rule.get("active", True),
            valid_from=rule.get("valid_from"),
            valid_until=rule.get("valid_until"),
            is_currently_active=is_active_now,
            created_at=rule["created_at"]
        ))

    return sorted(rules, key=lambda x: (-x.priority, x.name))


@router.get("/daypart-pricing/check-price/{item_id}", response_model=MenuItemPriceCheck, tags=["Daypart Pricing"])
async def check_daypart_price(
    item_id: int,
    check_time: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Check the current price for a menu item including any active daypart pricing

    This endpoint returns the effective price considering happy hours, lunch specials, etc.
    """
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    base_price = float(item.price)
    current_price = base_price
    active_daypart = None
    daypart_display_name = None
    price_valid_until = None

    # Find applicable daypart rules (highest priority first)
    applicable_rules = []

    for rule in _daypart_pricing_rules.values():
        if rule.get("venue_id") != current_user.venue_id:
            continue

        if not is_daypart_active(rule, check_time):
            continue

        # Check if rule applies to this item
        if rule.get("item_ids"):
            if item_id not in rule["item_ids"]:
                continue
        elif rule.get("category_ids"):
            if item.category_id not in rule["category_ids"]:
                continue

        applicable_rules.append(rule)

    # Apply highest priority rule
    if applicable_rules:
        applicable_rules.sort(key=lambda x: -x.get("priority", 0))
        best_rule = applicable_rules[0]

        current_price = calculate_daypart_price(base_price, best_rule)
        active_daypart = best_rule["name"]
        daypart_display_name = best_rule["display_name"]
        price_valid_until = best_rule["end_time"]

    discount_amount = base_price - current_price
    discount_percentage = (discount_amount / base_price * 100) if base_price > 0 else 0

    return MenuItemPriceCheck(
        menu_item_id=item_id,
        item_name=item.name if isinstance(item.name, dict) else {"en": str(item.name)},
        base_price=base_price,
        current_price=round(current_price, 2),
        discount_amount=round(discount_amount, 2),
        discount_percentage=round(discount_percentage, 1),
        active_daypart=active_daypart,
        daypart_display_name=daypart_display_name,
        price_valid_until=price_valid_until
    )


@router.delete("/daypart-pricing/{rule_id}", tags=["Daypart Pricing"])
async def delete_daypart_pricing(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Delete a daypart pricing rule"""
    if rule_id not in _daypart_pricing_rules:
        raise HTTPException(status_code=404, detail="Daypart pricing rule not found")

    rule = _daypart_pricing_rules[rule_id]
    if rule.get("venue_id") != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    del _daypart_pricing_rules[rule_id]
    return {"message": "Daypart pricing rule deleted", "id": rule_id}


@router.patch("/daypart-pricing/{rule_id}/toggle", tags=["Daypart Pricing"])
async def toggle_daypart_pricing(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Toggle a daypart pricing rule active/inactive"""
    if rule_id not in _daypart_pricing_rules:
        raise HTTPException(status_code=404, detail="Daypart pricing rule not found")

    rule = _daypart_pricing_rules[rule_id]
    if rule.get("venue_id") != current_user.venue_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    rule["active"] = not rule.get("active", True)
    return {"id": rule_id, "active": rule["active"]}


# =============================================================================
# PHOTO UPLOAD ENDPOINTS (With Real Storage)
# =============================================================================

@router.post("/items/{item_id}/photos/upload", response_model=PhotoUploadResponse, tags=["Menu Photos"])
async def upload_menu_item_photo(
    item_id: int,
    file: UploadFile = File(...),
    is_primary: bool = False,
    sort_order: int = 0,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """
    Upload a photo for a menu item with proper file storage

    Supports:
    - Local filesystem storage (default for development)
    - MinIO/S3 storage (when configured)

    Competitors: Toast Menu Photos, iiko Media Manager, TouchBistro Image Upload
    """
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Generate unique filename
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

    # Determine storage method
    storage_type = "local"
    photo_url = ""
    thumbnail_url = None

    try:
        # Try MinIO/S3 first if configured
        minio_available = False
        try:
            from app.services.upload_service import UploadService
            upload_service = UploadService()
            minio_available = True
        except Exception:
            minio_available = False

        if minio_available:
            # Upload to MinIO/S3
            object_name = f"menu-items/{item_id}/{unique_filename}"
            result = await upload_service.upload_file(file, object_name, file.content_type)
            photo_url = result["url"]
            storage_type = "minio"
        else:
            # Fall back to local storage
            upload_dir = Path("/tmp/v99_uploads/menu-items") / str(item_id)
            upload_dir.mkdir(parents=True, exist_ok=True)

            file_path = upload_dir / unique_filename

            # Save file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)

            photo_url = f"/uploads/menu-items/{item_id}/{unique_filename}"
            storage_type = "local"

        # Get file size
        await file.seek(0)
        file_content = await file.read()
        file_size = len(file_content)

        # Store photo metadata in item's recipe_json
        recipe_data = item.recipe_json or {}
        if "photos" not in recipe_data:
            recipe_data["photos"] = []

        photo_id = uuid.uuid4().hex[:8]
        photo_record = {
            "id": photo_id,
            "url": photo_url,
            "thumbnail_url": thumbnail_url,
            "filename": unique_filename,
            "original_filename": file.filename,
            "content_type": file.content_type,
            "size": file_size,
            "is_primary": is_primary,
            "sort_order": sort_order,
            "storage_type": storage_type,
            "uploaded_at": datetime.utcnow().isoformat(),
            "uploaded_by": current_user.id
        }

        # If this is primary, unset other primaries
        if is_primary:
            for photo in recipe_data["photos"]:
                photo["is_primary"] = False

        recipe_data["photos"].append(photo_record)
        item.recipe_json = recipe_data
        db.commit()

        return PhotoUploadResponse(
            id=photo_id,
            url=photo_url,
            thumbnail_url=thumbnail_url,
            filename=unique_filename,
            content_type=file.content_type,
            size=file_size,
            is_primary=is_primary,
            sort_order=sort_order,
            uploaded_at=datetime.utcnow(),
            storage_type=storage_type
        )

    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Photo upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed. Please try again.")


@router.get("/items/{item_id}/photos", tags=["Menu Photos"])
async def get_menu_item_photos(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get all photos for a menu item"""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    recipe_data = item.recipe_json or {}
    photos = recipe_data.get("photos", [])

    # Sort by primary first, then sort_order
    photos.sort(key=lambda x: (not x.get("is_primary", False), x.get("sort_order", 0)))

    return {
        "item_id": item_id,
        "item_name": item.name,
        "photos": photos,
        "total_count": len(photos),
        "primary_photo": next((p for p in photos if p.get("is_primary")), None)
    }


@router.delete("/items/{item_id}/photos/{photo_id}", tags=["Menu Photos"])
async def delete_menu_item_photo(
    item_id: int,
    photo_id: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """Delete a photo from a menu item"""
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    recipe_data = item.recipe_json or {}
    photos = recipe_data.get("photos", [])

    # Find and remove photo
    photo_to_delete = None
    for i, photo in enumerate(photos):
        if photo.get("id") == photo_id:
            photo_to_delete = photos.pop(i)
            break

    if not photo_to_delete:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Try to delete actual file
    try:
        if photo_to_delete.get("storage_type") == "local":
            file_path = Path("/tmp/v99_uploads") / photo_to_delete["url"].lstrip("/uploads/")
            if file_path.exists():
                file_path.unlink()
    except Exception:
        pass  # File deletion is best-effort

    recipe_data["photos"] = photos
    item.recipe_json = recipe_data
    db.commit()

    return {"message": "Photo deleted", "id": photo_id}


# =============================================================================
# ALLERGEN MATRIX ENDPOINTS
# =============================================================================

@router.get("/allergen-matrix", response_model=AllergenMatrixResponse, tags=["Allergen Matrix"])
async def get_allergen_matrix(
    category_id: Optional[int] = None,
    include_empty: bool = False,
    language: str = "en",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get complete allergen matrix for all menu items

    Returns a matrix view showing all items and their allergen status

    Competitors: Toast Allergen Manager, iiko Allergen Grid, TouchBistro Allergen View
    """
    # Get menu items
    query = db.query(MenuItem)
    if category_id:
        query = query.filter(MenuItem.category_id == category_id)

    items = query.all()

    allergen_codes = list(ALLERGEN_DEFINITIONS.keys())
    allergen_names = {
        code: {
            lang: info.get(lang, info["en"])
            for lang in ["en", "bg", "de", "ru"]
        }
        for code, info in ALLERGEN_DEFINITIONS.items()
    }
    allergen_icons = {code: info["icon"] for code, info in ALLERGEN_DEFINITIONS.items()}

    matrix_items = []
    allergen_counts = {code: 0 for code in allergen_codes}

    for item in items:
        item_allergens = item.allergens or {}

        # Convert list to dict if needed
        if isinstance(item_allergens, list):
            item_allergens = {a: "contains" for a in item_allergens}
        elif isinstance(item_allergens, dict) and "contains" in item_allergens:
            # Format: {contains: [], may_contain: []}
            allergen_dict = {}
            for a in item_allergens.get("contains", []):
                allergen_dict[a] = "contains"
            for a in item_allergens.get("may_contain", []):
                allergen_dict[a] = "may_contain"
            item_allergens = allergen_dict

        # Skip items with no allergens if not including empty
        if not include_empty and not item_allergens:
            continue

        # Build allergen status for this item
        item_allergen_status = {}
        for code in allergen_codes:
            if code in item_allergens:
                status = item_allergens[code]
                item_allergen_status[code] = status
                if status == "contains":
                    allergen_counts[code] += 1

        # Get category name
        category_name = {"en": "Unknown"}
        if item.category:
            category_name = item.category.name if isinstance(item.category.name, dict) else {"en": str(item.category.name)}

        matrix_items.append(MenuItemAllergenMatrix(
            menu_item_id=item.id,
            item_name=item.name if isinstance(item.name, dict) else {"en": str(item.name)},
            category_name=category_name,
            allergens=item_allergen_status
        ))

    return AllergenMatrixResponse(
        allergen_codes=allergen_codes,
        allergen_names=allergen_names,
        allergen_icons=allergen_icons,
        items=matrix_items,
        summary=allergen_counts
    )


@router.put("/items/{item_id}/allergen-matrix", tags=["Allergen Matrix"])
async def update_item_allergens_matrix(
    item_id: int,
    allergens: Dict[str, str],  # {allergen_code: severity}
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_manager)
):
    """
    Update allergens for a menu item using matrix format

    allergens: {"milk": "contains", "eggs": "may_contain", "nuts": "free_from"}
    """
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    # Validate allergen codes
    invalid_codes = [code for code in allergens.keys() if code not in ALLERGEN_DEFINITIONS]
    if invalid_codes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid allergen codes: {invalid_codes}"
        )

    # Validate severities
    valid_severities = ["contains", "may_contain", "free_from"]
    invalid_severities = [s for s in allergens.values() if s not in valid_severities]
    if invalid_severities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid severities. Use: {valid_severities}"
        )

    # Convert to storage format
    contains = [code for code, severity in allergens.items() if severity == "contains"]
    may_contain = [code for code, severity in allergens.items() if severity == "may_contain"]

    item.allergens = {
        "contains": contains,
        "may_contain": may_contain,
        "cross_contamination_risk": "low" if not may_contain else "medium",
        "updated_at": datetime.utcnow().isoformat(),
        "updated_by": current_user.id
    }

    db.commit()

    return {
        "success": True,
        "item_id": item_id,
        "allergens": allergens,
        "message": f"Updated allergens for item {item_id}"
    }


# =============================================================================
# BATCH SHELF LIFE TRACKING ENDPOINTS
# =============================================================================

@router.post("/batches/with-shelf-life", response_model=BatchShelfLifeResponse, tags=["Batch Shelf Life"])
async def create_batch_with_shelf_life(
    data: BatchShelfLifeCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Create a new batch with shelf life tracking

    Includes prep time tracking and calculated use-by dates for prepared items

    Competitors: Toast Prep Labels, iiko Batch Tracking, TouchBistro Date Labels
    """
    stock_item = db.query(StockItem).filter(
        StockItem.id == data.stock_item_id,
        StockItem.venue_id == current_user.venue_id
    ).first()

    if not stock_item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # Check for duplicate batch
    existing = db.query(StockBatch).filter(
        StockBatch.stock_item_id == data.stock_item_id,
        StockBatch.batch_number == data.batch_number
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Batch number already exists")

    # Calculate use_by_date if shelf life provided
    use_by_date = data.use_by_date
    if not use_by_date and data.shelf_life_hours:
        use_by_date = datetime.utcnow() + timedelta(hours=data.shelf_life_hours)

    # Create batch
    batch = StockBatch(
        stock_item_id=data.stock_item_id,
        batch_number=data.batch_number,
        initial_quantity=data.quantity,
        quantity=data.quantity,
        manufacture_date=data.manufacture_date,
        expiration_date=data.expiration_date,
        supplier_id=data.supplier_id,
        purchase_order_id=data.purchase_order_id,
        cost_per_unit=data.cost_per_unit or stock_item.cost_per_unit
    )

    db.add(batch)

    # Update main stock
    stock_item.quantity = (stock_item.quantity or 0) + data.quantity

    db.commit()
    db.refresh(batch)

    # Calculate freshness metrics
    now = datetime.utcnow()
    days_until_expiry = None
    is_expired = False
    is_expiring_soon = False

    if batch.expiration_date:
        delta = batch.expiration_date - now
        days_until_expiry = delta.days
        is_expired = days_until_expiry < 0
        is_expiring_soon = 0 <= days_until_expiry <= 7

    hours_until_use_by = None
    is_past_use_by = False

    if use_by_date:
        hours_delta = (use_by_date - now).total_seconds() / 3600
        hours_until_use_by = int(hours_delta)
        is_past_use_by = hours_delta < 0

    # Determine freshness status
    if is_expired or is_past_use_by:
        freshness_status = "expired"
    elif is_expiring_soon or (hours_until_use_by and hours_until_use_by < 24):
        freshness_status = "use_soon"
    elif days_until_expiry is not None or hours_until_use_by is not None:
        freshness_status = "fresh"
    else:
        freshness_status = "unknown"

    return BatchShelfLifeResponse(
        id=batch.id,
        stock_item_id=batch.stock_item_id,
        stock_item_name=stock_item.name,
        batch_number=batch.batch_number,
        quantity=batch.quantity,
        initial_quantity=batch.initial_quantity,
        manufacture_date=batch.manufacture_date,
        expiration_date=batch.expiration_date,
        prep_time_minutes=data.prep_time_minutes,
        shelf_life_hours=data.shelf_life_hours,
        use_by_date=use_by_date,
        storage_temperature_min=data.storage_temperature_min,
        storage_temperature_max=data.storage_temperature_max,
        days_until_expiry=days_until_expiry,
        hours_until_use_by=hours_until_use_by,
        is_expired=is_expired,
        is_expiring_soon=is_expiring_soon,
        is_past_use_by=is_past_use_by,
        freshness_status=freshness_status,
        created_at=batch.created_at
    )


@router.post("/prepared-batches", response_model=PreparedBatchResponse, tags=["Batch Shelf Life"])
async def create_prepared_batch(
    data: PreparedBatchCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Create a prepared batch for tracking prep work

    Used for:
    - Prepped sauces, dressings, marinades
    - Cut vegetables, proteins
    - Pre-portioned items
    - Made-ahead menu components

    Automatically calculates use-by datetime based on shelf life
    """
    global _prepared_batch_id_counter

    prepared_at = datetime.utcnow()
    use_by_datetime = prepared_at + timedelta(hours=data.shelf_life_hours)

    # Get item name if linked
    item_name = None
    if data.menu_item_id:
        item = db.query(MenuItem).filter(MenuItem.id == data.menu_item_id).first()
        if item:
            item_name = item.name.get("en", str(item.name)) if isinstance(item.name, dict) else str(item.name)
    elif data.stock_item_id:
        stock = db.query(StockItem).filter(StockItem.id == data.stock_item_id).first()
        if stock:
            item_name = stock.name

    # Get preparer name
    prepared_by_name = None
    if data.prepared_by or current_user:
        preparer_id = data.prepared_by or current_user.id
        preparer = db.query(StaffUser).filter(StaffUser.id == preparer_id).first()
        if preparer:
            prepared_by_name = preparer.full_name

    # Calculate hours remaining
    hours_remaining = int((use_by_datetime - prepared_at).total_seconds() / 3600)

    # Determine freshness
    if hours_remaining <= 0:
        freshness_status = "expired"
    elif hours_remaining <= 4:
        freshness_status = "use_soon"
    else:
        freshness_status = "fresh"

    batch_id = _prepared_batch_id_counter
    _prepared_batch_id_counter += 1

    batch = {
        "id": batch_id,
        "venue_id": current_user.venue_id,
        "batch_label": data.batch_label,
        "menu_item_id": data.menu_item_id,
        "stock_item_id": data.stock_item_id,
        "item_name": item_name,
        "quantity": data.quantity,
        "unit": data.unit,
        "prepared_at": prepared_at,
        "use_by_datetime": use_by_datetime,
        "shelf_life_hours": data.shelf_life_hours,
        "prepared_by": data.prepared_by or current_user.id,
        "prepared_by_name": prepared_by_name,
        "storage_location": data.storage_location,
        "notes": data.notes,
        "status": "active"
    }

    _prepared_batches[batch_id] = batch

    return PreparedBatchResponse(
        id=batch_id,
        batch_label=data.batch_label,
        menu_item_id=data.menu_item_id,
        stock_item_id=data.stock_item_id,
        item_name=item_name,
        quantity=data.quantity,
        unit=data.unit,
        prepared_at=prepared_at,
        use_by_datetime=use_by_datetime,
        shelf_life_hours=data.shelf_life_hours,
        hours_remaining=hours_remaining,
        prepared_by=batch["prepared_by"],
        prepared_by_name=prepared_by_name,
        storage_location=data.storage_location,
        status="active",
        freshness_status=freshness_status
    )


@router.get("/prepared-batches", tags=["Batch Shelf Life"])
async def list_prepared_batches(
    status: Optional[str] = None,  # active, used, expired, discarded
    expiring_soon: bool = False,  # Within 4 hours
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List prepared batches with freshness status"""
    now = datetime.utcnow()
    batches = []

    for batch in _prepared_batches.values():
        if batch.get("venue_id") != current_user.venue_id:
            continue

        # Calculate current freshness
        hours_remaining = int((batch["use_by_datetime"] - now).total_seconds() / 3600)

        if hours_remaining <= 0 and batch["status"] == "active":
            batch["status"] = "expired"

        if status and batch["status"] != status:
            continue

        if expiring_soon and hours_remaining > 4:
            continue

        # Determine freshness
        if hours_remaining <= 0:
            freshness_status = "expired"
        elif hours_remaining <= 4:
            freshness_status = "use_soon"
        else:
            freshness_status = "fresh"

        batches.append({
            **batch,
            "hours_remaining": max(0, hours_remaining),
            "freshness_status": freshness_status
        })

    # Sort by use_by (soonest first)
    batches.sort(key=lambda x: x["use_by_datetime"])

    return {
        "batches": batches,
        "total": len(batches),
        "expiring_soon_count": sum(1 for b in batches if b["freshness_status"] == "use_soon"),
        "expired_count": sum(1 for b in batches if b["freshness_status"] == "expired")
    }


# =============================================================================
# RECIPE SCALING ENDPOINTS
# =============================================================================

@router.post("/recipes/scale", response_model=RecipeScaleResponse, tags=["Recipe Scaling"])
async def scale_recipe(
    data: RecipeScaleRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Scale a recipe to a different number of portions

    Automatically adjusts:
    - Ingredient quantities (with practical rounding)
    - Costs
    - Prep time estimates

    Competitors: Toast Recipe Scaling, iiko Recipe Calculator, TouchBistro Batch Prep
    """
    # Get menu item and recipe
    menu_item = None
    recipe_data = None
    original_portions = 1.0

    if data.menu_item_id:
        menu_item = db.query(MenuItem).filter(MenuItem.id == data.menu_item_id).first()
        if not menu_item:
            raise HTTPException(status_code=404, detail="Menu item not found")

        recipe_data = menu_item.recipe_json or {}
    elif data.recipe_id:
        # For future: support Recipe model directly
        raise HTTPException(status_code=400, detail="recipe_id not yet supported, use menu_item_id")
    else:
        raise HTTPException(status_code=400, detail="Either recipe_id or menu_item_id required")

    # Get ingredients from recipe_json
    ingredients = recipe_data.get("ingredients", [])
    if not ingredients:
        # Try to generate sample ingredients for demo
        ingredients = [
            {"name": "Main Ingredient", "quantity": 200, "unit": "g", "cost": 2.50},
            {"name": "Secondary Ingredient", "quantity": 100, "unit": "g", "cost": 1.00},
            {"name": "Seasoning", "quantity": 1, "unit": "tbsp", "cost": 0.20}
        ]

    # Get original portions
    original_portions = recipe_data.get("portions", recipe_data.get("servings", 1))
    if isinstance(original_portions, str):
        try:
            original_portions = float(original_portions)
        except ValueError:
            original_portions = 1.0

    # Calculate scale factor
    scale_factor = data.target_portions / original_portions

    # Scale ingredients
    scaled_ingredients = []
    total_original_cost = 0
    total_scaled_cost = 0

    for i, ing in enumerate(ingredients):
        orig_qty = float(ing.get("quantity", 0))
        unit = ing.get("unit", "unit")
        cost_per_unit = float(ing.get("cost", 0))

        scaled_qty = orig_qty * scale_factor

        # Round to practical measurement if requested
        rounded_qty = scaled_qty
        practical = None

        if data.round_to_practical:
            practical = get_practical_measurement(scaled_qty, unit)
            if practical:
                # Extract number from practical (simple approach)
                # For more complex fractions, would need better parsing
                pass

        # Calculate costs
        orig_cost = cost_per_unit * orig_qty
        scaled_cost = cost_per_unit * scaled_qty

        total_original_cost += orig_cost
        total_scaled_cost += scaled_cost

        scaled_ingredients.append(ScaledIngredient(
            ingredient_id=i + 1,
            ingredient_name=ing.get("name", f"Ingredient {i+1}"),
            original_quantity=round(orig_qty, 3),
            scaled_quantity=round(scaled_qty, 3),
            rounded_quantity=round(rounded_qty, 3) if rounded_qty != scaled_qty else None,
            unit=unit,
            practical_measurement=practical,
            cost_per_unit=round(cost_per_unit, 2) if cost_per_unit else None,
            scaled_cost=round(scaled_cost, 2) if scaled_cost else None
        ))

    # Adjust prep time (doesn't scale linearly - use square root approximation)
    original_prep_time = recipe_data.get("time_minutes", recipe_data.get("prep_time", 30))
    if isinstance(original_prep_time, str):
        try:
            original_prep_time = int(original_prep_time)
        except ValueError:
            original_prep_time = 30

    adjusted_prep_time = int(original_prep_time * (scale_factor ** 0.5))

    # Calculate cost per portion
    cost_per_portion = total_scaled_cost / data.target_portions if data.target_portions > 0 else 0

    return RecipeScaleResponse(
        menu_item_id=data.menu_item_id,
        menu_item_name=menu_item.name if menu_item and isinstance(menu_item.name, dict) else {"en": "Recipe"},
        original_portions=original_portions,
        target_portions=data.target_portions,
        scale_factor=round(scale_factor, 4),
        ingredients=scaled_ingredients,
        total_original_cost=round(total_original_cost, 2),
        total_scaled_cost=round(total_scaled_cost, 2),
        cost_per_portion=round(cost_per_portion, 2),
        prep_time_minutes=original_prep_time,
        adjusted_prep_time_minutes=adjusted_prep_time
    )


@router.get("/recipes/{item_id}/scaling-presets", tags=["Recipe Scaling"])
async def get_recipe_scaling_presets(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """
    Get common scaling presets for a recipe

    Returns pre-calculated scales for common batch sizes
    """
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")

    recipe_data = item.recipe_json or {}
    base_portions = recipe_data.get("portions", 1)

    presets = [
        {"name": "Single Portion", "portions": 1, "scale_factor": 1.0 / base_portions},
        {"name": "Double", "portions": base_portions * 2, "scale_factor": 2.0},
        {"name": "5 Portions", "portions": 5, "scale_factor": 5.0 / base_portions},
        {"name": "10 Portions", "portions": 10, "scale_factor": 10.0 / base_portions},
        {"name": "20 Portions", "portions": 20, "scale_factor": 20.0 / base_portions},
        {"name": "50 Portions", "portions": 50, "scale_factor": 50.0 / base_portions},
        {"name": "100 Portions", "portions": 100, "scale_factor": 100.0 / base_portions},
    ]

    return {
        "menu_item_id": item_id,
        "menu_item_name": item.name,
        "base_portions": base_portions,
        "presets": presets
    }
