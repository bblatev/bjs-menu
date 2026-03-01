"""Chat, labor compliance, A/B testing, reviews, SSO & workers"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared schemas and helpers
from app.api.routes.gap_features._shared import *

router = APIRouter()

@router.post("/labor/compliance/rules")
@limiter.limit("30/minute")
async def create_compliance_rule(
    request: Request,
    body: ComplianceRuleRequest,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Create a labor compliance rule."""
    from app.services.team_chat_service import LaborComplianceService

    service = LaborComplianceService(db)
    rule = await service.create_compliance_rule(
        venue_id=venue_id,
        rule_type=body.rule_type,
        name=body.name,
        description=body.description,
        conditions=body.conditions,
        action=body.action
    )
    return rule


@router.post("/labor/compliance/check")
@limiter.limit("30/minute")
async def check_shift_compliance(
    request: Request,
    staff_id: str,
    shift_start: datetime,
    shift_end: datetime,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Check if a proposed shift complies with labor rules."""
    from app.services.team_chat_service import LaborComplianceService

    service = LaborComplianceService(db)
    violations = await service.check_shift_compliance(
        venue_id=venue_id,
        staff_id=staff_id,
        shift_start=shift_start,
        shift_end=shift_end
    )
    return {"violations": violations, "compliant": len(violations) == 0}


@router.get("/labor/compliance/violations")
@limiter.limit("60/minute")
async def get_violations(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Get labor compliance violations."""
    from app.services.team_chat_service import LaborComplianceService

    service = LaborComplianceService(db)
    violations = await service.get_violations(
        venue_id=venue_id,
        start_date=start_date,
        end_date=end_date,
        status=status
    )
    return {"violations": violations}


# ==================== A/B TESTING ENDPOINTS ====================

@router.post("/experiments")
@limiter.limit("30/minute")
async def create_experiment(
    request: Request,
    body: ExperimentRequest,
    db: Session = Depends(get_db),
    current_user: Staff = Depends(get_current_user),
    venue_id: int = Depends(get_current_venue)
):
    """Create an A/B experiment."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiment = await service.create_experiment(
        venue_id=venue_id,
        name=body.name,
        description=body.description,
        experiment_type=body.experiment_type,
        variants=body.variants,
        target_metric=body.target_metric,
        traffic_percentage=body.traffic_percentage,
        start_date=body.start_date,
        end_date=body.end_date,
        created_by=current_user.id
    )
    return {"experiment_id": str(experiment.id), "status": experiment.status.value}


@router.get("/experiments")
@limiter.limit("60/minute")
async def list_experiments(
    request: Request,
    status: Optional[str] = None,
    experiment_type: Optional[str] = None,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """List experiments."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiments = await service.list_experiments(
        venue_id=venue_id,
        status=status,
        experiment_type=experiment_type
    )
    return {
        "experiments": [
            {
                "id": str(e.id),
                "name": e.name,
                "experiment_type": e.experiment_type,
                "status": e.status.value,
                "target_metric": e.target_metric,
                "started_at": e.started_at.isoformat() if e.started_at else None
            }
            for e in experiments
        ]
    }


@router.post("/experiments/{experiment_id}/start")
@limiter.limit("30/minute")
async def start_experiment(
    request: Request,
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """Start an experiment."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiment = await service.start_experiment(experiment_id)
    return {"status": experiment.status.value}


@router.post("/experiments/{experiment_id}/pause")
@limiter.limit("30/minute")
async def pause_experiment(
    request: Request,
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """Pause an experiment."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiment = await service.pause_experiment(experiment_id)
    return {"status": experiment.status.value}


@router.post("/experiments/{experiment_id}/complete")
@limiter.limit("30/minute")
async def complete_experiment(
    request: Request,
    experiment_id: str,
    winner_variant: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Complete an experiment."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    experiment = await service.complete_experiment(experiment_id, winner_variant)
    return {"status": experiment.status.value, "winner": experiment.winner_variant}


@router.get("/experiments/{experiment_id}/variant")
@limiter.limit("60/minute")
async def get_variant(
    request: Request,
    experiment_id: str,
    user_id: str = Query("", description="User ID"),
    user_type: str = Query("customer", description="User type"),
    db: Session = Depends(get_db)
):
    """Get the variant assigned to a user."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    variant = await service.get_user_variant(experiment_id, user_id, user_type)
    return {"variant": variant}


@router.post("/experiments/{experiment_id}/convert")
@limiter.limit("30/minute")
async def record_conversion(
    request: Request,
    experiment_id: str,
    body: ConversionRequest,
    db: Session = Depends(get_db)
):
    """Record a conversion event."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    success = await service.record_conversion(
        experiment_id=experiment_id,
        user_id=body.user_id,
        metric_name=body.metric_name,
        metric_value=body.metric_value,
        order_id=body.order_id,
        metadata=body.metadata
    )
    return {"recorded": success}


@router.get("/experiments/{experiment_id}/results")
@limiter.limit("60/minute")
async def get_experiment_results(
    request: Request,
    experiment_id: str,
    db: Session = Depends(get_db)
):
    """Get experiment results and statistics."""
    from app.services.ab_testing_service import ABTestingService

    service = ABTestingService(db)
    results = await service.get_experiment_results(experiment_id)
    return results


# ==================== REVIEW AUTOMATION ENDPOINTS ====================

@router.post("/reviews/links")
@limiter.limit("30/minute")
async def create_review_link(
    request: Request,
    body: ReviewLinkRequest,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Create a review link."""
    from app.services.ab_testing_service import ReviewAutomationService

    service = ReviewAutomationService(db)
    link = await service.create_review_link(
        venue_id=venue_id,
        platform=body.platform,
        link_url=body.link_url
    )
    return link


@router.get("/reviews/links")
@limiter.limit("60/minute")
async def get_review_links(
    request: Request,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Get review links."""
    from app.services.ab_testing_service import ReviewAutomationService

    service = ReviewAutomationService(db)
    links = await service.get_review_links(venue_id)
    return {"links": links}


@router.post("/reviews/requests")
@limiter.limit("30/minute")
async def send_review_request(
    request: Request,
    body: ReviewRequestRequest,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Send a review request."""
    from app.services.ab_testing_service import ReviewAutomationService

    service = ReviewAutomationService(db)
    result = await service.send_review_request(
        venue_id=venue_id,
        order_id=body.order_id,
        customer_id=body.customer_id,
        method=body.method,
        delay_hours=body.delay_hours
    )
    return result


@router.get("/reviews/analytics")
@limiter.limit("60/minute")
async def get_review_analytics(
    request: Request,
    days: int = 30,
    db: Session = Depends(get_db),
    venue_id: int = Depends(get_current_venue)
):
    """Get review request analytics."""
    from app.services.ab_testing_service import ReviewAutomationService

    service = ReviewAutomationService(db)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    analytics = await service.get_review_analytics(venue_id, start_date, end_date)
    return analytics


# ==================== SSO ENDPOINTS ====================

@router.post("/sso/configurations")
@limiter.limit("30/minute")
async def create_sso_config(
    request: Request,
    body: SSOConfigRequest,
    tenant_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """Create SSO configuration."""
    try:
        from app.services.sso_service import SSOService
    except ImportError:
        raise HTTPException(status_code=501, detail="SSO service is not available. Required dependencies are not installed.")

    service = SSOService(db)
    config = await service.create_sso_config(
        tenant_id=tenant_id,
        provider_type=body.provider_type,
        display_name=body.display_name,
        config=body.config,
        domain_whitelist=body.domain_whitelist,
        auto_provision_users=body.auto_provision_users,
        default_role=body.default_role
    )
    return {"config_id": str(config.id), "provider": config.provider_type.value}


@router.get("/sso/configurations")
@limiter.limit("60/minute")
async def get_sso_config(
    request: Request,
    tenant_id: str = Query("", description="Tenant ID"),
    db: Session = Depends(get_db)
):
    """Get SSO configuration."""
    try:
        from app.services.sso_service import SSOService
    except ImportError:
        raise HTTPException(status_code=501, detail="SSO service is not available. Required dependencies are not installed.")

    service = SSOService(db)
    config = await service.get_sso_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    return {
        "id": str(config.id),
        "provider_type": config.provider_type.value,
        "display_name": config.display_name,
        "domain_whitelist": config.domain_whitelist,
        "auto_provision_users": config.auto_provision_users,
        "default_role": config.default_role
    }


@router.get("/sso/login")
@limiter.limit("60/minute")
async def initiate_sso_login(
    request: Request,
    tenant_id: str = Query("", description="Tenant ID"),
    redirect_uri: str = Query("", description="Redirect URI after login"),
    db: Session = Depends(get_db)
):
    """Initiate SSO login flow."""
    if redirect_uri and validate_redirect_uri is not None and not validate_redirect_uri(redirect_uri):
        raise HTTPException(status_code=400, detail="Invalid redirect URI")

    try:
        from app.services.sso_service import SSOService
    except ImportError:
        raise HTTPException(status_code=501, detail="SSO service is not available. Required dependencies are not installed.")

    service = SSOService(db)
    config = await service.get_sso_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.provider_type.value == "saml":
        result = await service.initiate_saml_login(config)
    else:
        result = await service.initiate_oauth_login(config, redirect_uri)

    return result


@router.post("/sso/callback")
@limiter.limit("30/minute")
async def handle_sso_callback(
    request: Request,
    tenant_id: str,
    code: Optional[str] = None,
    saml_response: Optional[str] = Body(None, alias="SAMLResponse"),
    redirect_uri: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle SSO callback."""
    if redirect_uri and validate_redirect_uri is not None and not validate_redirect_uri(redirect_uri):
        raise HTTPException(status_code=400, detail="Invalid redirect URI")

    try:
        from app.services.sso_service import SSOService
    except ImportError:
        raise HTTPException(status_code=501, detail="SSO service is not available. Required dependencies are not installed.")

    service = SSOService(db)
    config = await service.get_sso_config(tenant_id)
    if not config:
        raise HTTPException(status_code=404, detail="SSO configuration not found")

    if config.provider_type.value == "saml" and saml_response:
        result = await service.handle_saml_callback(config, saml_response)
    elif code and redirect_uri:
        result = await service.handle_oauth_callback(config, code, redirect_uri)
    else:
        raise HTTPException(status_code=400, detail="Invalid callback parameters")

    # Provision or find user
    user_id, is_new = await service.provision_sso_user(
        config,
        result["user_info"]
    )

    # Create session
    tokens = result.get("tokens", {})
    session = await service.create_sso_session(
        sso_config_id=config.id,
        user_id=user_id,
        provider_user_id=result["user_info"].get("sub", ""),
        tokens=tokens,
        user_info=result["user_info"]
    )

    return {
        "session_id": str(session.id),
        "user_id": str(user_id),
        "is_new_user": is_new,
        "user_info": result["user_info"]
    }


@router.post("/sso/logout")
@limiter.limit("30/minute")
async def sso_logout(
    request: Request,
    session_id: str,
    db: Session = Depends(get_db)
):
    """End SSO session."""
    try:
        from app.services.sso_service import SSOService
    except ImportError:
        raise HTTPException(status_code=501, detail="SSO service is not available. Required dependencies are not installed.")

    service = SSOService(db)
    success = await service.end_sso_session(session_id)
    return {"status": "logged_out" if success else "session_not_found"}


# ==================== BACKGROUND WORKERS ====================

@router.get("/system/workers/stats")
@limiter.limit("60/minute")
async def get_worker_stats(
    request: Request,
    current_user: Staff = Depends(get_current_user)
):
    """
    Get background worker statistics.
    Requires admin privileges.
    """
    if current_user.role not in ["owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.services.background_workers import worker_manager
    return worker_manager.get_stats()


@router.post("/system/workers/schedule")
@limiter.limit("30/minute")
async def schedule_task(
    request: Request,
    task_type: str = Body(...),
    name: str = Body(...),
    payload: Dict[str, Any] = Body(default={}),
    delay_seconds: int = Body(default=0),
    priority: str = Body(default="normal"),
    current_user: Staff = Depends(get_current_user),
    venue = Depends(get_current_venue)
):
    """
    Schedule a background task.
    Requires admin privileges.
    """
    if current_user.role not in ["owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.services.background_workers import schedule_task as bg_schedule, TaskPriority

    priority_map = {
        "low": TaskPriority.LOW,
        "normal": TaskPriority.NORMAL,
        "high": TaskPriority.HIGH,
        "critical": TaskPriority.CRITICAL
    }

    task_id = await bg_schedule(
        task_type=task_type,
        name=name,
        payload=payload,
        venue_id=venue.id,
        delay_seconds=delay_seconds,
        priority=priority_map.get(priority, TaskPriority.NORMAL)
    )

    return {"task_id": task_id, "status": "scheduled"}


@router.get("/system/workers/task/{task_id}")
@limiter.limit("60/minute")
async def get_task_status(
    request: Request,
    task_id: str,
    current_user: Staff = Depends(get_current_user)
):
    """Get status of a background task."""
    if current_user.role not in ["owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    from app.services.background_workers import worker_manager

    task = worker_manager.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "id": task.id,
        "name": task.name,
        "task_type": task.task_type,
        "status": task.status.value,
        "priority": task.priority.value,
        "scheduled_at": task.scheduled_at.isoformat() if task.scheduled_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "result": task.result
    }


@router.post("/system/workers/trigger/{task_type}")
@limiter.limit("30/minute")
async def trigger_task(
    request: Request,
    task_type: str,
    current_user: Staff = Depends(get_current_user),
    venue = Depends(get_current_venue)
):
    """
    Immediately trigger a specific task type.
    Requires admin privileges.
    """
    if current_user.role not in ["owner"]:
        raise HTTPException(status_code=403, detail="Admin access required")

    valid_tasks = [
        "process_review_requests",
        "check_experiment_significance",
        "check_compliance",
        "send_break_reminders",
        "check_device_health",
        "retry_failed_webhooks",
        "sync_7shifts",
        "sync_homebase",
        "sync_marginedge",
        "sync_accounting"
    ]

    if task_type not in valid_tasks:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid task type. Valid types: {', '.join(valid_tasks)}"
        )

    from app.services.background_workers import schedule_task as bg_schedule, TaskPriority

    task_id = await bg_schedule(
        task_type=task_type,
        name=f"Manual trigger: {task_type}",
        payload={"venue_id": venue.id},
        venue_id=venue.id,
        delay_seconds=0,
        priority=TaskPriority.HIGH
    )

    return {"task_id": task_id, "status": "triggered"}
