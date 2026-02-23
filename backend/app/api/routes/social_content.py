"""Social media content generation and management routes."""

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db as DbSession
from app.core.rbac import get_current_user

router = APIRouter(prefix="/marketing/social-content", tags=["marketing", "social"])


@router.get("/generate")
def generate_content(
    request: Request,
    content_type: str = "daily_special",
    platform: str = "instagram",
    venue_name: str = "BJ's Bar",
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Generate social media content from templates."""
    from app.services.social_content_service import SocialContentService

    context = {
        "item_name": "Chef's Special",
        "description": "A delicious dish prepared with the freshest ingredients",
        "short_description": "Fresh and delicious!",
        "hours": "11 AM - 10 PM",
        "event_name": "Live Music Night",
        "event_date": "Saturday",
        "event_time": "8 PM",
        "promo_name": "Happy Hour Special",
        "valid_dates": "this week only",
        "hashtag_categories": ["restaurant", "special"],
    }

    return SocialContentService.generate_content(
        venue_name=venue_name,
        content_type=content_type,
        platform=platform,
        context=context,
    )


@router.post("")
def create_post(
    request: Request,
    data: dict,
    venue_id: int = 1,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Create a social media post draft."""
    from app.services.social_content_service import SocialContentService

    data["created_by"] = current_user.id
    return SocialContentService.create_post(db, venue_id, data)


@router.get("")
def get_posts(
    request: Request,
    venue_id: int = 1,
    status: str = None,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Get social media posts."""
    from app.services.social_content_service import SocialContentService
    return SocialContentService.get_posts(db, venue_id, status)


@router.post("/{post_id}/schedule")
def schedule_post(
    request: Request,
    post_id: int,
    data: dict,
    db: Session = Depends(DbSession),
    current_user=Depends(get_current_user),
):
    """Schedule a post for publishing."""
    from app.services.social_content_service import SocialContentService
    from datetime import datetime

    scheduled_at = datetime.fromisoformat(data["scheduled_at"])
    result = SocialContentService.schedule_post(db, post_id, scheduled_at)
    if not result:
        raise HTTPException(status_code=404, detail="Post not found")
    return result
