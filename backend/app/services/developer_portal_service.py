"""
Developer Portal Service
Implements developer portal, API key management, and marketplace
Competitor: Toast Developer Portal, Square Developer Platform, Clover App Market
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import Session

from app.models.gap_features_models import (
    Developer, APIKey, APILog, MarketplaceApp, AppInstallation,
    AppReview, AppStatus, PricingType
)


class DeveloperPortalService:
    """
    Service for developer registration, API key management, and documentation access.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== DEVELOPER MANAGEMENT ====================

    async def register_developer(
        self,
        email: str,
        company_name: str,
        contact_name: str,
        website: Optional[str] = None,
        use_case: Optional[str] = None
    ) -> Developer:
        """Register a new developer account."""
        # Check if developer already exists
        result = await self.db.execute(
            select(Developer).where(Developer.email == email)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("Developer with this email already exists")

        developer = Developer(
            id=uuid4(),
            email=email,
            company_name=company_name,
            contact_name=contact_name,
            website=website,
            use_case=use_case,
            is_verified=False,
            is_active=True,
            tier="free",
            rate_limit_per_minute=60,
            rate_limit_per_day=10000,
            created_at=datetime.utcnow()
        )
        self.db.add(developer)
        await self.db.commit()
        await self.db.refresh(developer)
        return developer

    async def verify_developer(self, developer_id: UUID) -> bool:
        """Verify a developer account."""
        result = await self.db.execute(
            select(Developer).where(Developer.id == developer_id)
        )
        developer = result.scalar_one_or_none()
        if developer:
            developer.is_verified = True
            developer.verified_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False

    async def upgrade_developer_tier(
        self,
        developer_id: UUID,
        tier: str  # 'free', 'starter', 'professional', 'enterprise'
    ) -> Developer:
        """Upgrade developer's API tier."""
        tier_limits = {
            "free": {"per_minute": 60, "per_day": 10000},
            "starter": {"per_minute": 300, "per_day": 50000},
            "professional": {"per_minute": 1000, "per_day": 500000},
            "enterprise": {"per_minute": 5000, "per_day": 5000000}
        }

        result = await self.db.execute(
            select(Developer).where(Developer.id == developer_id)
        )
        developer = result.scalar_one_or_none()
        if not developer:
            raise ValueError("Developer not found")

        limits = tier_limits.get(tier, tier_limits["free"])
        developer.tier = tier
        developer.rate_limit_per_minute = limits["per_minute"]
        developer.rate_limit_per_day = limits["per_day"]
        await self.db.commit()
        await self.db.refresh(developer)
        return developer

    async def get_developer(self, developer_id: UUID) -> Optional[Developer]:
        """Get developer by ID."""
        result = await self.db.execute(
            select(Developer).where(Developer.id == developer_id)
        )
        return result.scalar_one_or_none()

    async def get_developer_by_email(self, email: str) -> Optional[Developer]:
        """Get developer by email."""
        result = await self.db.execute(
            select(Developer).where(Developer.email == email)
        )
        return result.scalar_one_or_none()

    # ==================== API KEY MANAGEMENT ====================

    async def create_api_key(
        self,
        developer_id: UUID,
        name: str,
        scopes: List[str],
        venue_id: Optional[UUID] = None,
        expires_in_days: Optional[int] = None
    ) -> Tuple[APIKey, str]:
        """
        Create a new API key.
        Returns the APIKey object and the raw key (only shown once).
        """
        # Verify developer exists
        developer = await self.get_developer(developer_id)
        if not developer:
            raise ValueError("Developer not found")

        if not developer.is_active:
            raise ValueError("Developer account is not active")

        # Check key limit based on tier
        key_limits = {"free": 2, "starter": 5, "professional": 20, "enterprise": 100}
        max_keys = key_limits.get(developer.tier, 2)

        result = await self.db.execute(
            select(func.count(APIKey.id)).where(
                and_(
                    APIKey.developer_id == developer_id,
                    APIKey.is_active == True
                )
            )
        )
        current_keys = result.scalar() or 0

        if current_keys >= max_keys:
            raise ValueError(f"Maximum API keys ({max_keys}) reached for {developer.tier} tier")

        # Generate API key
        raw_key = f"zver_{'live' if venue_id else 'test'}_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # Calculate expiry
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        api_key = APIKey(
            id=uuid4(),
            developer_id=developer_id,
            name=name,
            key_prefix=raw_key[:16],  # Store prefix for identification
            key_hash=key_hash,
            scopes=scopes,
            venue_id=venue_id,
            is_active=True,
            rate_limit_per_minute=developer.rate_limit_per_minute,
            rate_limit_per_day=developer.rate_limit_per_day,
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        self.db.add(api_key)
        await self.db.commit()
        await self.db.refresh(api_key)

        return api_key, raw_key

    async def validate_api_key(self, raw_key: str) -> Optional[APIKey]:
        """
        Validate an API key and return the associated APIKey object.
        """
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:16]

        result = await self.db.execute(
            select(APIKey).where(
                and_(
                    APIKey.key_prefix == key_prefix,
                    APIKey.key_hash == key_hash,
                    APIKey.is_active == True
                )
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            return None

        # Check expiry
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        # Update last used
        api_key.last_used_at = datetime.utcnow()
        await self.db.commit()

        return api_key

    async def revoke_api_key(self, api_key_id: UUID, developer_id: UUID) -> bool:
        """Revoke an API key."""
        result = await self.db.execute(
            select(APIKey).where(
                and_(
                    APIKey.id == api_key_id,
                    APIKey.developer_id == developer_id
                )
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key:
            api_key.is_active = False
            api_key.revoked_at = datetime.utcnow()
            await self.db.commit()
            return True
        return False

    async def list_api_keys(self, developer_id: UUID) -> List[APIKey]:
        """List all API keys for a developer."""
        result = await self.db.execute(
            select(APIKey).where(APIKey.developer_id == developer_id)
            .order_by(desc(APIKey.created_at))
        )
        return list(result.scalars().all())

    # ==================== API LOGGING ====================

    async def log_api_request(
        self,
        api_key_id: UUID,
        method: str,
        path: str,
        status_code: int,
        response_time_ms: int,
        request_body_size: int = 0,
        response_body_size: int = 0,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> APILog:
        """Log an API request."""
        log = APILog(
            id=uuid4(),
            api_key_id=api_key_id,
            method=method,
            path=path,
            status_code=status_code,
            response_time_ms=response_time_ms,
            request_body_size=request_body_size,
            response_body_size=response_body_size,
            error_message=error_message,
            ip_address=ip_address,
            created_at=datetime.utcnow()
        )
        self.db.add(log)
        await self.db.commit()
        return log

    async def get_api_usage_stats(
        self,
        developer_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get API usage statistics for a developer."""
        # Get all API keys for developer
        keys_result = await self.db.execute(
            select(APIKey.id).where(APIKey.developer_id == developer_id)
        )
        key_ids = [k for k in keys_result.scalars().all()]

        if not key_ids:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_response_time_ms": 0,
                "requests_by_endpoint": {},
                "requests_by_day": []
            }

        # Total requests
        result = await self.db.execute(
            select(func.count(APILog.id)).where(
                and_(
                    APILog.api_key_id.in_(key_ids),
                    APILog.created_at >= start_date,
                    APILog.created_at <= end_date
                )
            )
        )
        total_requests = result.scalar() or 0

        # Successful requests
        result = await self.db.execute(
            select(func.count(APILog.id)).where(
                and_(
                    APILog.api_key_id.in_(key_ids),
                    APILog.created_at >= start_date,
                    APILog.created_at <= end_date,
                    APILog.status_code < 400
                )
            )
        )
        successful_requests = result.scalar() or 0

        # Average response time
        result = await self.db.execute(
            select(func.avg(APILog.response_time_ms)).where(
                and_(
                    APILog.api_key_id.in_(key_ids),
                    APILog.created_at >= start_date,
                    APILog.created_at <= end_date
                )
            )
        )
        avg_response_time = result.scalar() or 0

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": total_requests - successful_requests,
            "avg_response_time_ms": round(avg_response_time, 2),
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat()
        }

    async def check_rate_limit(self, api_key: APIKey) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if API key has exceeded rate limits.
        Returns (is_allowed, rate_limit_info).
        """
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Check per-minute limit
        result = await self.db.execute(
            select(func.count(APILog.id)).where(
                and_(
                    APILog.api_key_id == api_key.id,
                    APILog.created_at >= minute_ago
                )
            )
        )
        requests_last_minute = result.scalar() or 0

        # Check per-day limit
        result = await self.db.execute(
            select(func.count(APILog.id)).where(
                and_(
                    APILog.api_key_id == api_key.id,
                    APILog.created_at >= day_start
                )
            )
        )
        requests_today = result.scalar() or 0

        is_allowed = (
            requests_last_minute < api_key.rate_limit_per_minute and
            requests_today < api_key.rate_limit_per_day
        )

        return is_allowed, {
            "requests_last_minute": requests_last_minute,
            "limit_per_minute": api_key.rate_limit_per_minute,
            "requests_today": requests_today,
            "limit_per_day": api_key.rate_limit_per_day,
            "remaining_minute": max(0, api_key.rate_limit_per_minute - requests_last_minute),
            "remaining_day": max(0, api_key.rate_limit_per_day - requests_today)
        }


class MarketplaceService:
    """
    Service for app marketplace management.
    Allows third-party developers to publish and distribute apps.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== APP MANAGEMENT ====================

    async def submit_app(
        self,
        developer_id: UUID,
        name: str,
        slug: str,
        short_description: str,
        full_description: str,
        category: str,
        icon_url: str,
        screenshots: List[str],
        webhook_url: Optional[str] = None,
        oauth_redirect_uri: Optional[str] = None,
        required_scopes: List[str] = None,
        pricing_type: str = "free",
        price_monthly: float = 0,
        price_yearly: float = 0
    ) -> MarketplaceApp:
        """Submit a new app for review."""
        # Check if slug is unique
        result = await self.db.execute(
            select(MarketplaceApp).where(MarketplaceApp.slug == slug)
        )
        if result.scalar_one_or_none():
            raise ValueError("App with this slug already exists")

        app = MarketplaceApp(
            id=uuid4(),
            developer_id=developer_id,
            name=name,
            slug=slug,
            short_description=short_description,
            full_description=full_description,
            category=category,
            icon_url=icon_url,
            screenshots=screenshots,
            webhook_url=webhook_url,
            oauth_redirect_uri=oauth_redirect_uri,
            required_scopes=required_scopes or [],
            pricing_type=PricingType(pricing_type),
            price_monthly=price_monthly,
            price_yearly=price_yearly,
            status=AppStatus.DRAFT,
            version="1.0.0",
            install_count=0,
            avg_rating=0,
            review_count=0,
            created_at=datetime.utcnow()
        )
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def submit_for_review(self, app_id: UUID, developer_id: UUID) -> MarketplaceApp:
        """Submit an app for review."""
        result = await self.db.execute(
            select(MarketplaceApp).where(
                and_(
                    MarketplaceApp.id == app_id,
                    MarketplaceApp.developer_id == developer_id
                )
            )
        )
        app = result.scalar_one_or_none()
        if not app:
            raise ValueError("App not found")

        if app.status not in [AppStatus.DRAFT, AppStatus.REJECTED]:
            raise ValueError(f"Cannot submit app with status {app.status}")

        app.status = AppStatus.PENDING_REVIEW
        app.submitted_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def approve_app(self, app_id: UUID) -> MarketplaceApp:
        """Approve an app (admin only)."""
        result = await self.db.execute(
            select(MarketplaceApp).where(MarketplaceApp.id == app_id)
        )
        app = result.scalar_one_or_none()
        if not app:
            raise ValueError("App not found")

        app.status = AppStatus.APPROVED
        app.published_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def reject_app(
        self,
        app_id: UUID,
        rejection_reason: str
    ) -> MarketplaceApp:
        """Reject an app (admin only)."""
        result = await self.db.execute(
            select(MarketplaceApp).where(MarketplaceApp.id == app_id)
        )
        app = result.scalar_one_or_none()
        if not app:
            raise ValueError("App not found")

        app.status = AppStatus.REJECTED
        app.rejection_reason = rejection_reason
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def list_apps(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "popular",  # 'popular', 'newest', 'rating'
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[MarketplaceApp], int]:
        """List published apps with filtering and sorting."""
        query = select(MarketplaceApp).where(
            MarketplaceApp.status == AppStatus.APPROVED
        )

        if category:
            query = query.where(MarketplaceApp.category == category)

        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    MarketplaceApp.name.ilike(search_term),
                    MarketplaceApp.short_description.ilike(search_term)
                )
            )

        # Sorting
        if sort_by == "popular":
            query = query.order_by(desc(MarketplaceApp.install_count))
        elif sort_by == "newest":
            query = query.order_by(desc(MarketplaceApp.published_at))
        elif sort_by == "rating":
            query = query.order_by(desc(MarketplaceApp.avg_rating))

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        apps = list(result.scalars().all())

        return apps, total

    async def get_app(self, app_id: UUID) -> Optional[MarketplaceApp]:
        """Get app by ID."""
        result = await self.db.execute(
            select(MarketplaceApp).where(MarketplaceApp.id == app_id)
        )
        return result.scalar_one_or_none()

    async def get_app_by_slug(self, slug: str) -> Optional[MarketplaceApp]:
        """Get app by slug."""
        result = await self.db.execute(
            select(MarketplaceApp).where(MarketplaceApp.slug == slug)
        )
        return result.scalar_one_or_none()

    # ==================== APP INSTALLATION ====================

    async def install_app(
        self,
        app_id: UUID,
        venue_id: UUID,
        installed_by: UUID,
        granted_scopes: List[str],
        billing_cycle: str = "monthly"
    ) -> AppInstallation:
        """Install an app for a venue."""
        # Check if already installed
        result = await self.db.execute(
            select(AppInstallation).where(
                and_(
                    AppInstallation.app_id == app_id,
                    AppInstallation.venue_id == venue_id,
                    AppInstallation.is_active == True
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("App is already installed")

        # Get app
        app = await self.get_app(app_id)
        if not app:
            raise ValueError("App not found")

        if app.status != AppStatus.APPROVED:
            raise ValueError("App is not available for installation")

        installation = AppInstallation(
            id=uuid4(),
            app_id=app_id,
            venue_id=venue_id,
            installed_by=installed_by,
            granted_scopes=granted_scopes,
            is_active=True,
            billing_cycle=billing_cycle,
            installed_at=datetime.utcnow()
        )
        self.db.add(installation)

        # Update install count
        app.install_count += 1

        await self.db.commit()
        await self.db.refresh(installation)
        return installation

    async def uninstall_app(
        self,
        app_id: UUID,
        venue_id: UUID
    ) -> bool:
        """Uninstall an app from a venue."""
        result = await self.db.execute(
            select(AppInstallation).where(
                and_(
                    AppInstallation.app_id == app_id,
                    AppInstallation.venue_id == venue_id,
                    AppInstallation.is_active == True
                )
            )
        )
        installation = result.scalar_one_or_none()
        if not installation:
            return False

        installation.is_active = False
        installation.uninstalled_at = datetime.utcnow()

        # Update install count
        app_result = await self.db.execute(
            select(MarketplaceApp).where(MarketplaceApp.id == app_id)
        )
        app = app_result.scalar_one_or_none()
        if app and app.install_count > 0:
            app.install_count -= 1

        await self.db.commit()
        return True

    async def get_installed_apps(
        self,
        venue_id: UUID
    ) -> List[Tuple[AppInstallation, MarketplaceApp]]:
        """Get all installed apps for a venue."""
        result = await self.db.execute(
            select(AppInstallation, MarketplaceApp)
            .join(MarketplaceApp, AppInstallation.app_id == MarketplaceApp.id)
            .where(
                and_(
                    AppInstallation.venue_id == venue_id,
                    AppInstallation.is_active == True
                )
            )
        )
        return list(result.all())

    # ==================== APP REVIEWS ====================

    async def add_review(
        self,
        app_id: UUID,
        venue_id: UUID,
        reviewer_id: UUID,
        rating: int,
        title: Optional[str] = None,
        body: Optional[str] = None
    ) -> AppReview:
        """Add a review for an app."""
        # Verify app is installed at venue
        result = await self.db.execute(
            select(AppInstallation).where(
                and_(
                    AppInstallation.app_id == app_id,
                    AppInstallation.venue_id == venue_id
                )
            )
        )
        if not result.scalar_one_or_none():
            raise ValueError("Cannot review an app that is not installed")

        # Check for existing review
        result = await self.db.execute(
            select(AppReview).where(
                and_(
                    AppReview.app_id == app_id,
                    AppReview.venue_id == venue_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            # Update existing review
            existing.rating = rating
            existing.title = title
            existing.body = body
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            await self._update_app_rating(app_id)
            await self.db.refresh(existing)
            return existing

        # Create new review
        review = AppReview(
            id=uuid4(),
            app_id=app_id,
            venue_id=venue_id,
            reviewer_id=reviewer_id,
            rating=rating,
            title=title,
            body=body,
            is_verified=True,
            created_at=datetime.utcnow()
        )
        self.db.add(review)
        await self.db.commit()
        await self._update_app_rating(app_id)
        await self.db.refresh(review)
        return review

    async def _update_app_rating(self, app_id: UUID) -> None:
        """Update app's average rating."""
        result = await self.db.execute(
            select(
                func.avg(AppReview.rating),
                func.count(AppReview.id)
            ).where(AppReview.app_id == app_id)
        )
        row = result.one()
        avg_rating = row[0] or 0
        review_count = row[1] or 0

        app_result = await self.db.execute(
            select(MarketplaceApp).where(MarketplaceApp.id == app_id)
        )
        app = app_result.scalar_one_or_none()
        if app:
            app.avg_rating = round(float(avg_rating), 2)
            app.review_count = review_count
            await self.db.commit()

    async def get_app_reviews(
        self,
        app_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> Tuple[List[AppReview], int]:
        """Get reviews for an app."""
        # Count total
        result = await self.db.execute(
            select(func.count(AppReview.id)).where(AppReview.app_id == app_id)
        )
        total = result.scalar() or 0

        # Get reviews
        result = await self.db.execute(
            select(AppReview)
            .where(AppReview.app_id == app_id)
            .order_by(desc(AppReview.created_at))
            .offset(offset)
            .limit(limit)
        )
        reviews = list(result.scalars().all())

        return reviews, total

    # ==================== WEBHOOKS ====================

    async def trigger_webhook(
        self,
        installation: AppInstallation,
        event_type: str,
        payload: Dict[str, Any]
    ) -> bool:
        """Trigger a webhook for an installed app."""
        import httpx

        app = await self.get_app(installation.app_id)
        if not app or not app.webhook_url:
            return False

        webhook_payload = {
            "event": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "venue_id": str(installation.venue_id),
            "installation_id": str(installation.id),
            "data": payload
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    app.webhook_url,
                    json=webhook_payload,
                    timeout=10.0
                )
                return response.status_code < 400
        except Exception:
            return False
