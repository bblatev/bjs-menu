"""
Currency API Endpoints
Handles EUR/BGN dual currency operations and euro adoption
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from decimal import Decimal

from app.db.session import get_db
from app.services.currency_service import CurrencyService
from pydantic import BaseModel, Field, ConfigDict
from app.core.rate_limit import limiter


router = APIRouter()


# ==================== SCHEMAS ====================

class DualPriceResponse(BaseModel):
    """Price in both EUR and BGN"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "eur": 5.00,
            "bgn": 9.78,
            "eur_formatted": "€5.00",
            "bgn_formatted": "9.78 лв",

            "conversion_rate": 1.95583
        }
    })

    eur: float
    bgn: float
    eur_formatted: str
    bgn_formatted: str
    conversion_rate: float


class CurrencyStatusResponse(BaseModel):
    """Current currency status for venue"""
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "dual_pricing_active": True,
            "primary_currency": "BGN",
            "accepts_both_currencies": False,
            "conversion_rate": 1.95583,
            "euro_adoption_date": "2026-01-01",
            "dual_pricing_start": "2025-08-08",
            "dual_pricing_end": "2026-12-31",
            "dual_circulation_start": "2026-01-01",
            "dual_circulation_end": "2026-01-31"
        }
    })

    dual_pricing_active: bool
    primary_currency: str
    accepts_both_currencies: bool
    conversion_rate: float
    euro_adoption_date: str
    dual_pricing_start: str
    dual_pricing_end: str
    dual_circulation_start: str
    dual_circulation_end: str


class MenuItemDualPrice(BaseModel):
    """Menu item with dual pricing"""
    item_id: int
    name: dict
    price_eur: float
    price_bgn: float
    formatted: str
    original_currency: str


class OrderTotalsRequest(BaseModel):
    """Request for order total calculation"""
    items: List[dict] = Field(..., description="List of items with price and quantity")
    payment_currency: str = Field("BGN", description="Currency for payment (EUR or BGN)")
    vat_rate: Optional[float] = Field(0.09, description="VAT rate (default 9% for restaurants)")


class OrderTotalsResponse(BaseModel):
    """Order totals in both currencies"""
    subtotal_eur: float
    tax_eur: float
    total_eur: float
    subtotal_bgn: float
    tax_bgn: float
    total_bgn: float
    currency: str
    vat_rate: float


# ==================== ENDPOINTS ====================

@router.get("/")
@limiter.limit("60/minute")
async def get_currency_root(request: Request, db: Session = Depends(get_db)):
    """Currency management overview."""
    return {"module": "currency", "status": "active", "default_currency": "EUR", "supported_currencies": ["EUR", "BGN", "USD"], "endpoints": ["/convert", "/rates", "/settings"]}


@router.get(
    "/currency/status",
    response_model=CurrencyStatusResponse,
    summary="Get currency status",
    description="Get current currency status including dual pricing, primary currency, and euro adoption timeline"
)
@limiter.limit("60/minute")
def get_currency_status(
    request: Request,
    venue_id: int,
    db: Session = Depends(get_db)
):
    """
    Get complete currency status for venue
    
    - **venue_id**: Venue ID to check status for
    
    Returns information about:
    - Whether dual pricing is currently active
    - Primary currency (BGN or EUR)
    - Whether both currencies are accepted
    - Conversion rate
    - Important dates for euro adoption
    """
    service = CurrencyService(db)
    return service.get_currency_status(venue_id)


@router.get(
    "/currency/convert",
    response_model=DualPriceResponse,
    summary="Convert currency",
    description="Convert amount between EUR and BGN using official fixed rate"
)
@limiter.limit("60/minute")
def convert_currency(
    request: Request,
    amount: float = Query(..., description="Amount to convert", gt=0),
    from_currency: str = Query("BGN", description="Source currency (EUR or BGN)"),
    db: Session = Depends(get_db)
):
    """
    Convert amount between EUR and BGN
    
    - **amount**: Amount to convert (must be positive)
    - **from_currency**: Source currency ('EUR' or 'BGN')
    
    Returns the amount in both currencies with formatted strings.
    
    Uses official fixed rate: 1 EUR = 1.95583 BGN
    """
    if from_currency not in ['EUR', 'BGN']:
        raise HTTPException(
            status_code=400,
            detail="from_currency must be 'EUR' or 'BGN'"
        )
    
    service = CurrencyService(db)
    result = service.get_dual_price(Decimal(str(amount)), from_currency)
    
    return result


@router.get(
    "/menu/{item_id}/dual-price",
    response_model=MenuItemDualPrice,
    summary="Get menu item dual price",
    description="Get menu item price in both EUR and BGN"
)
@limiter.limit("60/minute")
def get_item_dual_price(
    request: Request,
    item_id: int = Path(..., description="Menu item ID"),
    db: Session = Depends(get_db)
):
    """
    Get menu item price in both EUR and BGN
    
    - **item_id**: Menu item ID
    
    Returns:
    - Price in both currencies
    - Formatted dual price string
    - Original currency the item was priced in
    """
    service = CurrencyService(db)
    result = service.get_menu_item_dual_price(item_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Menu item {item_id} not found"
        )
    
    return result


@router.post(
    "/currency/calculate-totals",
    response_model=OrderTotalsResponse,
    summary="Calculate order totals",
    description="Calculate order subtotal, tax, and total in both currencies"
)
@limiter.limit("30/minute")
def calculate_order_totals(
    request: Request,
    body: OrderTotalsRequest,
    db: Session = Depends(get_db)
):
    """
    Calculate order totals in both currencies
    
    - **items**: List of order items with price and quantity
    - **payment_currency**: Currency customer is paying in ('EUR' or 'BGN')
    - **vat_rate**: VAT rate (default 0.09 for 9%)
    
    Returns:
    - Subtotal, tax, and total in both EUR and BGN
    - Currency used for payment
    - VAT rate applied
    
    Example items format:
    ```json
    [
        {"price": 10.00, "quantity": 2},
        {"price": 5.50, "quantity": 1}
    ]
    ```
    """
    if body.payment_currency not in ['EUR', 'BGN']:
        raise HTTPException(
            status_code=400,
            detail="payment_currency must be 'EUR' or 'BGN'"
        )

    service = CurrencyService(db)

    totals = service.calculate_order_totals_dual(
        items=body.items,
        payment_currency=body.payment_currency,
        vat_rate=Decimal(str(body.vat_rate))
    )
    
    return totals


@router.get(
    "/currency/format-price",
    summary="Format price for display",
    description="Get formatted price string in dual currency format"
)
@limiter.limit("60/minute")
def format_price(
    request: Request,
    amount: float = Query(..., description="Amount to format", gt=0),
    currency: str = Query("BGN", description="Original currency (EUR or BGN)"),
    db: Session = Depends(get_db)
):
    """
    Format price for display in dual currency format
    
    - **amount**: Price amount
    - **currency**: Original currency
    
    Returns formatted string like "€5.00 / 9.78 лв"
    """
    if currency not in ['EUR', 'BGN']:
        raise HTTPException(
            status_code=400,
            detail="currency must be 'EUR' or 'BGN'"
        )
    
    service = CurrencyService(db)
    formatted = service.format_dual_price(Decimal(str(amount)), currency)
    
    return {
        "formatted": formatted,
        "amount": amount,
        "currency": currency
    }


@router.get(
    "/currency/timeline",
    summary="Get euro adoption timeline",
    description="Get key dates and milestones for Bulgaria's euro adoption"
)
@limiter.limit("60/minute")
def get_euro_timeline(request: Request):
    """
    Get complete timeline for Bulgaria's euro adoption
    
    Returns all important dates and milestones
    """
    return {
        "timeline": [
            {
                "date": "2025-08-08",
                "event": "Dual Pricing Starts",
                "description": "All businesses must display prices in both BGN and EUR with equal prominence",
                "mandatory": True
            },
            {
                "date": "2026-01-01",
                "event": "Euro Adoption",
                "description": "EUR becomes official currency of Bulgaria",
                "mandatory": True
            },
            {
                "date": "2026-01-01",
                "event": "Dual Circulation Starts",
                "description": "Both EUR and BGN accepted for payments (30 days)",
                "mandatory": True
            },
            {
                "date": "2026-01-31",
                "event": "Dual Circulation Ends",
                "description": "Only EUR accepted from this date forward",
                "mandatory": True
            },
            {
                "date": "2026-12-31",
                "event": "Dual Pricing Optional",
                "description": "After this date, dual pricing is no longer mandatory (but recommended)",
                "mandatory": False
            }
        ],
        "conversion_rate": {
            "rate": 1.95583,
            "formula": "1 EUR = 1.95583 BGN",
            "is_fixed": True,
            "description": "Official fixed conversion rate set by European Central Bank"
        }
    }
