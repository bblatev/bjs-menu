"""AI social media content generation service."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session


# Content templates for different post types
TEMPLATES = {
    "daily_special": {
        "instagram": "🍽️ Today's Special: {item_name}\n\n{description}\n\nAvailable today only! Come in and try it before it's gone.\n\n📍 {venue_name}\n⏰ {hours}\n\n{hashtags}",
        "facebook": "Today's Special at {venue_name}!\n\n🍽️ {item_name}\n{description}\n\nJoin us today and enjoy this limited-time dish!\n\n{hashtags}",
        "twitter": "🍽️ Today's Special: {item_name}! {short_description}\n\nAvailable today only at {venue_name}! {hashtags}",
    },
    "event": {
        "instagram": "🎉 Upcoming Event!\n\n{event_name}\n📅 {event_date}\n⏰ {event_time}\n📍 {venue_name}\n\n{description}\n\nDon't miss out! Reserve your spot now.\n\n{hashtags}",
        "facebook": "🎉 {event_name} at {venue_name}!\n\n📅 {event_date} at {event_time}\n\n{description}\n\nBook your table now!\n\n{hashtags}",
    },
    "promotion": {
        "instagram": "🔥 Special Offer!\n\n{promo_name}\n{description}\n\nValid {valid_dates}\n\n📍 {venue_name}\n\n{hashtags}",
        "facebook": "🔥 {promo_name} at {venue_name}!\n\n{description}\n\nDon't miss this deal! Valid {valid_dates}.\n\n{hashtags}",
    },
    "behind_scenes": {
        "instagram": "👨‍🍳 Behind the scenes at {venue_name}!\n\n{description}\n\nOur team works hard to bring you the best dining experience.\n\n{hashtags}",
    },
}

DEFAULT_HASHTAGS = {
    "restaurant": ["#restaurant", "#foodie", "#delicious", "#instafood", "#yummy"],
    "bar": ["#bar", "#cocktails", "#drinks", "#nightlife", "#happyhour"],
    "special": ["#dailyspecial", "#chefspecial", "#limitedtime", "#tryitnow"],
    "event": ["#event", "#livemusic", "#nightout", "#weekend"],
}


class SocialContentService:
    """Generates and manages social media content."""

    @staticmethod
    def generate_content(
        venue_name: str,
        content_type: str,
        platform: str,
        context: dict,
    ) -> dict:
        """Generate social media content from templates."""
        templates = TEMPLATES.get(content_type, {})
        template = templates.get(platform)

        if not template:
            # Fallback generic template
            template = f"Check out what's happening at {venue_name}! {context.get('description', '')}"

        # Build hashtags
        hashtag_categories = context.get("hashtag_categories", ["restaurant"])
        hashtags = []
        for cat in hashtag_categories:
            hashtags.extend(DEFAULT_HASHTAGS.get(cat, []))
        # Add venue-specific hashtag
        venue_tag = "#" + venue_name.replace(" ", "").replace("'", "").lower()
        hashtags.insert(0, venue_tag)
        context["hashtags"] = " ".join(hashtags[:10])
        context["venue_name"] = venue_name

        # Fill template
        try:
            caption = template.format(**context)
        except KeyError:
            caption = template

        return {
            "platform": platform,
            "content_type": content_type,
            "caption": caption,
            "hashtags": hashtags[:10],
            "suggested_time": "11:30 AM" if content_type == "daily_special" else "6:00 PM",
        }

    @staticmethod
    def create_post(db: Session, venue_id: int, data: dict):
        """Create a social media post draft."""
        from app.models.v99_models import SocialPost

        post = SocialPost(
            venue_id=venue_id,
            platform=data["platform"],
            content_type=data.get("content_type", "promotion"),
            caption=data["caption"],
            hashtags=data.get("hashtags", []),
            image_url=data.get("image_url"),
            scheduled_at=data.get("scheduled_at"),
            status="draft" if not data.get("scheduled_at") else "scheduled",
            created_by=data.get("created_by"),
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return {
            "id": post.id,
            "platform": post.platform,
            "caption": post.caption,
            "status": post.status,
        }

    @staticmethod
    def get_posts(db: Session, venue_id: int, status: Optional[str] = None):
        """Get social media posts for a venue."""
        from app.models.v99_models import SocialPost

        query = db.query(SocialPost).filter(SocialPost.venue_id == venue_id)
        if status:
            query = query.filter(SocialPost.status == status)

        posts = query.order_by(SocialPost.created_at.desc()).limit(50).all()
        return [
            {
                "id": p.id,
                "platform": p.platform,
                "content_type": p.content_type,
                "caption": p.caption,
                "hashtags": p.hashtags,
                "status": p.status,
                "scheduled_at": str(p.scheduled_at) if p.scheduled_at else None,
                "published_at": str(p.published_at) if p.published_at else None,
                "engagement": {
                    "likes": p.engagement_likes,
                    "comments": p.engagement_comments,
                    "shares": p.engagement_shares,
                },
            }
            for p in posts
        ]

    @staticmethod
    def schedule_post(db: Session, post_id: int, scheduled_at: datetime):
        """Schedule a post for publishing."""
        from app.models.v99_models import SocialPost

        post = db.query(SocialPost).filter(SocialPost.id == post_id).first()
        if not post:
            return None

        post.scheduled_at = scheduled_at
        post.status = "scheduled"
        db.commit()
        return {"id": post.id, "status": "scheduled", "scheduled_at": str(scheduled_at)}
