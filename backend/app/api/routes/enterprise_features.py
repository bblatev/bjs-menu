"""
Enterprise Features API Endpoints
Integration Marketplace, AI Invoice OCR, Mobile App Builder, Hotel PMS
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.db.session import get_db
from app.core.rbac import get_current_user
from app.core.rate_limit import limiter
from app.models import StaffUser


router = APIRouter()


def require_admin(current_user = Depends(get_current_user)):
    """Require admin/owner role."""
    if not hasattr(current_user, 'role'):
        return current_user
    if current_user.role not in ("admin", "owner", "manager"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user



# ==================== SCHEMAS ====================

class IntegrationConnectRequest(BaseModel):
    slug: str
    credentials: Dict[str, Any]
    settings: Optional[Dict[str, Any]] = None


class OCRJobCreate(BaseModel):
    file_url: str
    original_filename: str
    file_type: str
    file_size_bytes: int
    source_type: str = "upload"


class MobileAppCreate(BaseModel):
    app_name: str
    app_description: Optional[str] = None
    primary_color: str = "#FF6B35"
    secondary_color: str = "#004E89"


class MobileAppBranding(BaseModel):
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    accent_color: Optional[str] = None
    background_color: Optional[str] = None
    text_color: Optional[str] = None
    app_icon_url: Optional[str] = None
    splash_screen_url: Optional[str] = None
    logo_url: Optional[str] = None


class PushCampaignCreate(BaseModel):
    name: str
    title: str
    body: str
    target_audience: str = "all"
    image_url: Optional[str] = None
    action_url: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class PMSConnectRequest(BaseModel):
    provider: str
    api_endpoint: str
    credentials: Dict[str, Any]
    hotel_id: str
    hotel_name: str


class RoomChargeRequest(BaseModel):
    order_id: int
    guest_id: int
    amount: float
    description: str


class FBCreditCreate(BaseModel):
    guest_id: int
    amount: float
    credit_type: str = "complimentary"
    valid_days: int = 7


# ==================== INTEGRATION MARKETPLACE ====================

@router.get("/marketplace/integrations")
@limiter.limit("60/minute")
async def list_marketplace_integrations(
    request: Request,
    category: Optional[str] = None,
    search: Optional[str] = None,
    region: Optional[str] = None,
    popular_only: bool = False,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List all available integrations in marketplace (100+)"""
    from app.services.integration_marketplace_service import IntegrationMarketplaceService
    service = IntegrationMarketplaceService(db)
    return service.get_all_integrations(
        category=category,
        search=search,
        region=region,
        popular_only=popular_only
    )


@router.get("/marketplace/categories")
@limiter.limit("60/minute")
async def get_marketplace_categories(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get integration categories"""
    from app.services.integration_marketplace_service import IntegrationMarketplaceService
    service = IntegrationMarketplaceService(db)
    return service.get_categories()


@router.get("/marketplace/popular")
@limiter.limit("60/minute")
async def get_popular_integrations(
    request: Request,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get most popular integrations"""
    from app.services.integration_marketplace_service import IntegrationMarketplaceService
    service = IntegrationMarketplaceService(db)
    return service.get_popular_integrations(limit)


@router.get("/marketplace/integrations/{slug}")
@limiter.limit("60/minute")
async def get_integration_details(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get integration details by slug"""
    from app.services.integration_marketplace_service import IntegrationMarketplaceService
    service = IntegrationMarketplaceService(db)
    integration = service.get_integration_by_slug(slug)
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    return integration


@router.post("/marketplace/connect")
@limiter.limit("30/minute")
async def connect_marketplace_integration(
    request: Request,
    body: IntegrationConnectRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Connect to an integration from marketplace"""
    from app.services.integration_marketplace_service import IntegrationMarketplaceService
    service = IntegrationMarketplaceService(db)
    return service.connect_integration(
        venue_id=current_user.venue_id,
        slug=body.slug,
        credentials=body.credentials,
        settings=body.settings
    )


@router.post("/marketplace/{slug}/disconnect")
@limiter.limit("30/minute")
async def disconnect_marketplace_integration(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Disconnect from an integration"""
    from app.services.integration_marketplace_service import IntegrationMarketplaceService
    service = IntegrationMarketplaceService(db)
    return service.disconnect_integration(current_user.venue_id, slug)


@router.get("/marketplace/connected")
@limiter.limit("60/minute")
async def get_connected_marketplace_integrations(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get all connected integrations"""
    from app.services.integration_marketplace_service import IntegrationMarketplaceService
    service = IntegrationMarketplaceService(db)
    return service.get_connected_integrations(current_user.venue_id)


@router.get("/marketplace/stats")
@limiter.limit("60/minute")
async def get_marketplace_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get integration statistics"""
    from app.services.integration_marketplace_service import IntegrationMarketplaceService
    service = IntegrationMarketplaceService(db)
    return service.get_integration_stats(current_user.venue_id)


# ==================== AI INVOICE OCR ====================

@router.post("/invoice-ocr/jobs")
@limiter.limit("30/minute")
async def create_ocr_job(
    request: Request,
    body: OCRJobCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Create a new invoice OCR job"""
    from app.services.invoice_ocr_service import InvoiceOCRService
    service = InvoiceOCRService(db)
    return service.create_ocr_job(
        venue_id=current_user.venue_id,
        file_url=body.file_url,
        original_filename=body.original_filename,
        file_type=body.file_type,
        file_size_bytes=body.file_size_bytes,
        source_type=body.source_type,
        uploaded_by=current_user.id
    )


@router.post("/invoice-ocr/jobs/{job_id}/process")
@limiter.limit("30/minute")
async def process_ocr_job(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Process an invoice OCR job"""
    from app.services.invoice_ocr_service import InvoiceOCRService
    service = InvoiceOCRService(db)
    return service.process_invoice(job_id)


@router.get("/invoice-ocr/jobs/{job_id}")
@limiter.limit("60/minute")
async def get_ocr_job(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get OCR job details"""
    from app.services.invoice_ocr_service import InvoiceOCRService
    service = InvoiceOCRService(db)
    result = service.get_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")
    return result


@router.get("/invoice-ocr/jobs")
@limiter.limit("60/minute")
async def list_ocr_jobs(
    request: Request,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """List OCR jobs"""
    from app.services.invoice_ocr_service import InvoiceOCRService
    service = InvoiceOCRService(db)
    return service.list_jobs(
        venue_id=current_user.venue_id,
        status=status,
        limit=limit,
        offset=offset
    )


@router.post("/invoice-ocr/jobs/{job_id}/match-items")
@limiter.limit("30/minute")
async def match_ocr_line_items(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Auto-match extracted line items to stock items"""
    from app.services.invoice_ocr_service import InvoiceOCRService
    service = InvoiceOCRService(db)
    return service.match_line_items(job_id)


@router.post("/invoice-ocr/jobs/{job_id}/approve")
@limiter.limit("30/minute")
async def approve_ocr_job(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Approve OCR job and create invoice"""
    from app.services.invoice_ocr_service import InvoiceOCRService
    service = InvoiceOCRService(db)
    return service.approve_and_create_invoice(job_id, current_user.id)


@router.post("/invoice-ocr/jobs/{job_id}/reject")
@limiter.limit("30/minute")
async def reject_ocr_job(
    request: Request,
    job_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Reject OCR job"""
    from app.services.invoice_ocr_service import InvoiceOCRService
    service = InvoiceOCRService(db)
    return service.reject_job(job_id, current_user.id, reason)


@router.put("/invoice-ocr/jobs/{job_id}/field/{field}")
@limiter.limit("30/minute")
async def update_ocr_field(
    request: Request,
    job_id: int,
    field: str,
    value: Any,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Update extracted field after review"""
    from app.services.invoice_ocr_service import InvoiceOCRService
    service = InvoiceOCRService(db)
    return service.update_extracted_data(job_id, field, value, current_user.id)


@router.get("/invoice-ocr/stats")
@limiter.limit("60/minute")
async def get_ocr_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get OCR processing statistics"""
    from app.services.invoice_ocr_service import InvoiceOCRService
    service = InvoiceOCRService(db)
    return service.get_ocr_stats(current_user.venue_id)


# ==================== MOBILE APP BUILDER ====================

@router.post("/mobile-app")
@limiter.limit("30/minute")
async def create_mobile_app(
    request: Request,
    body: MobileAppCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Create a branded mobile app"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.create_app(
        venue_id=current_user.venue_id,
        app_name=body.app_name,
        app_description=body.app_description,
        primary_color=body.primary_color,
        secondary_color=body.secondary_color,
        created_by=current_user.id
    )


@router.get("/mobile-app")
@limiter.limit("60/minute")
async def get_mobile_app(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get mobile app configuration"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    result = service.get_app(current_user.venue_id)
    if not result:
        return {"exists": False, "message": "No app configured"}
    return result


@router.put("/mobile-app/branding")
@limiter.limit("30/minute")
async def update_mobile_app_branding(
    request: Request,
    branding: MobileAppBranding,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Update mobile app branding"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.update_branding(
        venue_id=current_user.venue_id,
        branding=branding.model_dump(exclude_none=True)
    )


@router.put("/mobile-app/features")
@limiter.limit("30/minute")
async def update_mobile_app_features(
    request: Request,
    features: List[str],
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Update enabled features"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.update_features(current_user.venue_id, features)


@router.get("/mobile-app/features/available")
@limiter.limit("60/minute")
async def get_available_app_features(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get all available mobile app features"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.get_available_features()


@router.post("/mobile-app/builds")
@limiter.limit("30/minute")
async def start_mobile_app_build(
    request: Request,
    platform: str,
    version: str,
    release_notes: str = "",
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Start a new app build"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.start_build(
        venue_id=current_user.venue_id,
        platform=platform,
        version=version,
        release_notes=release_notes,
        created_by=current_user.id
    )


@router.get("/mobile-app/builds")
@limiter.limit("60/minute")
async def get_mobile_app_builds(
    request: Request,
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get build history"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.get_builds(current_user.venue_id, limit)


@router.post("/mobile-app/builds/{build_id}/publish")
@limiter.limit("30/minute")
async def publish_mobile_app(
    request: Request,
    build_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Publish an app build"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.publish_app(current_user.venue_id, build_id)


@router.post("/mobile-app/push-campaigns")
@limiter.limit("30/minute")
async def create_push_campaign(
    request: Request,
    body: PushCampaignCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Create a push notification campaign"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.create_push_campaign(
        venue_id=current_user.venue_id,
        name=body.name,
        title=body.title,
        body=body.body,
        created_by=current_user.id,
        target_audience=body.target_audience,
        scheduled_at=body.scheduled_at,
        image_url=body.image_url,
        action_url=body.action_url
    )


@router.get("/mobile-app/push-campaigns")
@limiter.limit("60/minute")
async def get_push_campaigns(
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get push notification campaigns"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.get_push_campaigns(current_user.venue_id, limit)


@router.get("/mobile-app/analytics")
@limiter.limit("60/minute")
async def get_mobile_app_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get app analytics"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.get_app_analytics(current_user.venue_id)


@router.get("/mobile-app/screens")
@limiter.limit("60/minute")
async def get_custom_screens(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get custom app screens"""
    from app.services.mobile_app_builder_service import MobileAppBuilderService
    service = MobileAppBuilderService(db)
    return service.get_custom_screens(current_user.venue_id)


# ==================== HOTEL PMS INTEGRATION ====================

@router.get("/hotel-pms/providers")
@limiter.limit("60/minute")
async def get_pms_providers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get supported PMS providers"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.get_supported_providers()


@router.post("/hotel-pms/connect")
@limiter.limit("30/minute")
async def connect_hotel_pms(
    request: Request,
    body: PMSConnectRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Connect to hotel PMS"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.connect_pms(
        venue_id=current_user.venue_id,
        provider=body.provider,
        api_endpoint=body.api_endpoint,
        credentials=body.credentials,
        hotel_id=body.hotel_id,
        hotel_name=body.hotel_name
    )


@router.post("/hotel-pms/disconnect")
@limiter.limit("30/minute")
async def disconnect_hotel_pms(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Disconnect from hotel PMS"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.disconnect_pms(current_user.venue_id)


@router.get("/hotel-pms/connection")
@limiter.limit("60/minute")
async def get_pms_connection(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get current PMS connection details"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    result = service.get_connection(current_user.venue_id)
    if not result:
        return {"connected": False}
    return result


@router.get("/hotel-pms/health")
@limiter.limit("60/minute")
async def check_pms_health(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Check PMS connection health"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.health_check(current_user.venue_id)


@router.get("/hotel-pms/guests")
@limiter.limit("60/minute")
async def search_hotel_guests(
    request: Request,
    query: Optional[str] = None,
    room_number: Optional[str] = None,
    checked_in_only: bool = True,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Search hotel guests"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.search_guests(
        venue_id=current_user.venue_id,
        query=query,
        room_number=room_number,
        checked_in_only=checked_in_only
    )


@router.post("/hotel-pms/guests/sync")
@limiter.limit("30/minute")
async def sync_hotel_guests(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Sync guests from PMS"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.sync_guests(current_user.venue_id)


@router.post("/hotel-pms/room-charges")
@limiter.limit("30/minute")
async def post_room_charge(
    request: Request,
    body: RoomChargeRequest,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Post charge to guest room"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.post_room_charge(
        venue_id=current_user.venue_id,
        order_id=body.order_id,
        guest_id=body.guest_id,
        amount=body.amount,
        description=body.description,
        posted_by=current_user.id
    )


@router.get("/hotel-pms/room-charges")
@limiter.limit("60/minute")
async def get_room_charges(
    request: Request,
    guest_id: Optional[int] = None,
    order_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get room charges"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.get_room_charges(
        venue_id=current_user.venue_id,
        guest_id=guest_id,
        order_id=order_id,
        status=status,
        limit=limit
    )


@router.post("/hotel-pms/room-charges/{charge_id}/void")
@limiter.limit("30/minute")
async def void_room_charge(
    request: Request,
    charge_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Void a room charge"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.void_room_charge(
        venue_id=current_user.venue_id,
        charge_id=charge_id,
        reason=reason,
        voided_by=current_user.id
    )


@router.post("/hotel-pms/fb-credits")
@limiter.limit("30/minute")
async def create_fb_credit(
    request: Request,
    body: FBCreditCreate,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(require_admin)
):
    """Create F&B credit for guest"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.create_fb_credit(
        venue_id=current_user.venue_id,
        guest_id=body.guest_id,
        amount=body.amount,
        credit_type=body.credit_type,
        valid_days=body.valid_days
    )


@router.get("/hotel-pms/guests/{guest_id}/credits")
@limiter.limit("60/minute")
async def get_guest_credits(
    request: Request,
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get F&B credits for a guest"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.get_guest_credits(current_user.venue_id, guest_id)


@router.post("/hotel-pms/fb-credits/{credit_id}/apply")
@limiter.limit("30/minute")
async def apply_fb_credit(
    request: Request,
    credit_id: int,
    guest_id: int,
    amount: float,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Apply F&B credit to order"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.apply_fb_credit(
        venue_id=current_user.venue_id,
        guest_id=guest_id,
        credit_id=credit_id,
        amount=amount
    )


@router.get("/hotel-pms/stats")
@limiter.limit("60/minute")
async def get_pms_stats(
    request: Request,
    db: Session = Depends(get_db),
    current_user: StaffUser = Depends(get_current_user)
):
    """Get PMS integration statistics"""
    from app.services.hotel_pms_service import HotelPMSService
    service = HotelPMSService(db)
    return service.get_pms_stats(current_user.venue_id)
