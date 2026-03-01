"""V9 AI, Legal, Training, Crisis, Platform & QR"""
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

from app.core.rbac import get_current_user
from app.core.rate_limit import limiter

# Import all services and schemas from shared
from app.api.routes.v9_endpoints._shared import *

router = APIRouter()

# ==================== AI - MODEL MANAGEMENT ====================

@router.post("/ai/models", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def register_ai_model(
    request: Request,
    model_name: str,
    model_type: str,
    model_version: str,
    configuration: Dict[str, Any],
    description: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Register a new AI model"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AIModelService.register_model(db, venue_id, model_name, model_type, model_version, configuration, description)


@router.post("/ai/models/{model_id}/activate", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def activate_ai_model(
    request: Request,
    model_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Activate an AI model"""
    return AIModelService.activate_model(db, model_id)


@router.get("/ai/models/active", response_model=List[Dict[str, Any]], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_active_ai_models(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all active AI models for a venue"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AIModelService.get_active_models(db, venue_id)


@router.put("/ai/models/{model_id}/accuracy", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def update_model_accuracy(
    request: Request,
    model_id: int,
    accuracy_score: Decimal,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update model accuracy score after evaluation"""
    return AIModelService.update_model_accuracy(db, model_id, accuracy_score)


# ==================== AI - PREDICTIONS ====================

@router.post("/ai/predictions", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def log_prediction(
    request: Request,
    model_id: int,
    prediction_type: str,
    input_data: Dict[str, Any],
    predicted_value: Any,
    confidence_score: Decimal,
    target_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Log an AI prediction"""
    return PredictionService.log_prediction(db, model_id, prediction_type, input_data, predicted_value, confidence_score, target_date)


@router.post("/ai/predictions/{prediction_id}/actual", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def record_actual_value(
    request: Request,
    prediction_id: int,
    actual_value: Any,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Record actual value for a prediction to measure accuracy"""
    return PredictionService.record_actual_value(db, prediction_id, actual_value)


@router.get("/ai/predictions/accuracy-report", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_prediction_accuracy_report(
    request: Request,
    model_id: Optional[int] = None,
    prediction_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get prediction accuracy report"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PredictionService.get_prediction_accuracy_report(db, venue_id, model_id, prediction_type, start_date, end_date)


# ==================== AI - AUTOMATION RULES ====================

@router.post("/ai/automation-rules", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def create_automation_rule(
    request: Request,
    rule_name: str,
    trigger_type: str,
    trigger_config: Dict[str, Any],
    action_type: str,
    action_config: Dict[str, Any],
    enabled: bool = True,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create an automation rule"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AutomationRuleService.create_automation_rule(db, venue_id, rule_name, trigger_type, trigger_config, action_type, action_config, enabled)


@router.get("/ai/automation-rules", response_model=List[Dict[str, Any]], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_automation_rules(
    request: Request,
    enabled_only: bool = False,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all automation rules for a venue"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AutomationRuleService.get_automation_rules(db, venue_id, enabled_only)


@router.put("/ai/automation-rules/{rule_id}/toggle", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def toggle_automation_rule(
    request: Request,
    rule_id: int,
    enabled: bool,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Enable or disable an automation rule"""
    return AutomationRuleService.toggle_automation_rule(db, rule_id, enabled)


@router.post("/ai/automation-rules/check", response_model=List[Dict[str, Any]], tags=["V9 - AI & Automation"])
@limiter.limit("30/minute")
async def check_and_execute_automations(
    request: Request,
    trigger_type: str,
    trigger_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check and execute matching automation rules"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return AutomationRuleService.check_and_execute_automations(db, venue_id, trigger_type, trigger_data)


# ==================== AI - MENU OPTIMIZATION ====================

@router.get("/ai/menu-optimization", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_menu_optimization_suggestions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered menu optimization suggestions based on real sales data"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return MenuOptimizationService.get_menu_optimization_suggestions(db, venue_id)


# ==================== AI - STAFFING RECOMMENDATIONS ====================

@router.get("/ai/staffing-recommendations", response_model=Dict[str, Any], tags=["V9 - AI & Automation"])
@limiter.limit("60/minute")
async def get_staffing_recommendations(
    request: Request,
    target_date: Optional[date] = Query(None, description="Target date (defaults to today)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get AI-powered staffing recommendations based on historical data"""
    if target_date is None:
        target_date = date.today()
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return StaffingRecommendationService.get_staffing_recommendations(db, venue_id, target_date)


# ==================== LEGAL - INCIDENT REPORTS ====================

@router.post("/legal/incidents", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def create_incident_report(
    request: Request,
    incident_type: str,
    incident_date: datetime,
    location: str,
    description: str,
    severity: str,
    persons_involved: Optional[List[Dict[str, Any]]] = None,
    witnesses: Optional[List[Dict[str, Any]]] = None,
    immediate_actions: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create an incident report"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    reported_by = current_user.id
    if LegalRiskService is None:
        raise HTTPException(status_code=501, detail="Legal risk service is not available. Required dependencies are not installed.")
    return LegalRiskService.create_incident_report(
        db, venue_id, reported_by, incident_type, incident_date, location,
        description, severity, persons_involved, witnesses, immediate_actions
    )


@router.post("/legal/incidents/{report_id}/evidence", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def add_incident_evidence(
    request: Request,
    report_id: int,
    evidence_type: str,
    file_path: str,
    description: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add evidence to an incident report"""
    uploaded_by = current_user.id
    if LegalRiskService is None:
        raise HTTPException(status_code=501, detail="Legal risk service is not available. Required dependencies are not installed.")
    return LegalRiskService.add_evidence(db, report_id, evidence_type, file_path, description, uploaded_by)


@router.put("/legal/incidents/{report_id}/status", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def update_incident_status(
    request: Request,
    report_id: int,
    status: str,
    notes: Optional[str] = None,
    resolution: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update incident report status"""
    updated_by = current_user.id
    if LegalRiskService is None:
        raise HTTPException(status_code=501, detail="Legal risk service is not available. Required dependencies are not installed.")
    return LegalRiskService.update_incident_status(db, report_id, status, updated_by, notes, resolution)


@router.get("/legal/incidents", response_model=List[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_incident_reports(
    request: Request,
    status: Optional[str] = None,
    incident_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get incident reports with filters"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if LegalRiskService is None:
        raise HTTPException(status_code=501, detail="Legal risk service is not available. Required dependencies are not installed.")
    return LegalRiskService.get_incident_reports(db, venue_id, status, incident_type, start_date, end_date)


@router.post("/legal/incidents/{report_id}/insurance", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def link_insurance_claim(
    request: Request,
    report_id: int,
    claim_number: str,
    claim_details: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Link an insurance claim to an incident report"""
    if LegalRiskService is None:
        raise HTTPException(status_code=501, detail="Legal risk service is not available. Required dependencies are not installed.")
    return LegalRiskService.link_insurance_claim(db, report_id, claim_number, claim_details)


# ==================== TRAINING ====================

@router.post("/training/modules", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def create_training_module(
    request: Request,
    module_name: str,
    module_type: str,
    description: str,
    content: Dict[str, Any],
    duration_minutes: int,
    required_roles: List[str],
    passing_score: int = 80,
    certification_valid_days: Optional[int] = 365,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a training module"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if TrainingService is None:
        raise HTTPException(status_code=501, detail="Training service is not available. Required dependencies are not installed.")
    return TrainingService.create_training_module(
        db, venue_id, module_name, module_type, description, content,
        duration_minutes, required_roles, passing_score, certification_valid_days
    )


@router.get("/training/modules", response_model=List[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_training_modules(
    request: Request,
    module_type: Optional[str] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get training modules with filters"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if TrainingService is None:
        raise HTTPException(status_code=501, detail="Training service is not available. Required dependencies are not installed.")
    return TrainingService.get_training_modules(db, venue_id, module_type, role)


@router.post("/training/start/{module_id}", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def start_training(
    request: Request,
    module_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Start a training session for a staff member"""
    if TrainingService is None:
        raise HTTPException(status_code=501, detail="Training service is not available. Required dependencies are not installed.")
    return TrainingService.start_training(db, staff_id, module_id)


@router.post("/training/complete/{record_id}", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def complete_training(
    request: Request,
    record_id: int,
    score: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Complete a training session with score"""
    if TrainingService is None:
        raise HTTPException(status_code=501, detail="Training service is not available. Required dependencies are not installed.")
    return TrainingService.complete_training(db, record_id, score)


@router.get("/training/status/{staff_id}", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_staff_training_status(
    request: Request,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get training status for a staff member"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if TrainingService is None:
        raise HTTPException(status_code=501, detail="Training service is not available. Required dependencies are not installed.")
    return TrainingService.get_staff_training_status(db, staff_id, venue_id)


@router.get("/training/expiring-certifications", response_model=List[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_expiring_certifications(
    request: Request,
    days_ahead: int = 30,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get certifications expiring soon"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if TrainingService is None:
        raise HTTPException(status_code=501, detail="Training service is not available. Required dependencies are not installed.")
    return TrainingService.get_expiring_certifications(db, venue_id, days_ahead)


# ==================== CRISIS MANAGEMENT ====================

@router.post("/crisis/modes", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def create_crisis_mode(
    request: Request,
    mode_name: str,
    mode_type: str,
    description: str,
    simplified_menu_ids: List[int],
    margin_protection_percentage: Decimal,
    operational_changes: Dict[str, Any],
    auto_activation_conditions: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a crisis mode configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if CrisisManagementService is None:
        raise HTTPException(status_code=501, detail="Crisis management service is not available. Required dependencies are not installed.")
    return CrisisManagementService.create_crisis_mode(
        db, venue_id, mode_name, mode_type, description, simplified_menu_ids,
        margin_protection_percentage, operational_changes, auto_activation_conditions
    )


@router.post("/crisis/modes/{crisis_mode_id}/activate", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def activate_crisis_mode(
    request: Request,
    crisis_mode_id: int,
    reason: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Activate a crisis mode"""
    activated_by = current_user.id
    if CrisisManagementService is None:
        raise HTTPException(status_code=501, detail="Crisis management service is not available. Required dependencies are not installed.")
    return CrisisManagementService.activate_crisis_mode(db, crisis_mode_id, activated_by, reason)


@router.post("/crisis/deactivate", response_model=Dict[str, Any], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def deactivate_crisis_mode(
    request: Request,
    reason: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Deactivate the current crisis mode"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    deactivated_by = current_user.id
    if CrisisManagementService is None:
        raise HTTPException(status_code=501, detail="Crisis management service is not available. Required dependencies are not installed.")
    return CrisisManagementService.deactivate_crisis_mode(db, venue_id, deactivated_by, reason)


@router.get("/crisis/active", response_model=Optional[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_active_crisis_mode(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get the currently active crisis mode"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if CrisisManagementService is None:
        raise HTTPException(status_code=501, detail="Crisis management service is not available. Required dependencies are not installed.")
    return CrisisManagementService.get_active_crisis_mode(db, venue_id)


@router.get("/crisis/modes", response_model=List[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("60/minute")
async def get_crisis_modes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all crisis mode configurations"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if CrisisManagementService is None:
        raise HTTPException(status_code=501, detail="Crisis management service is not available. Required dependencies are not installed.")
    return CrisisManagementService.get_crisis_modes(db, venue_id)


@router.post("/crisis/check-auto-activation", response_model=Optional[Dict[str, Any]], tags=["V9 - Legal & Training"])
@limiter.limit("30/minute")
async def check_crisis_auto_activation(
    request: Request,
    current_conditions: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check if any crisis mode should be auto-activated"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    if CrisisManagementService is None:
        raise HTTPException(status_code=501, detail="Crisis management service is not available. Required dependencies are not installed.")
    return CrisisManagementService.check_auto_activation(db, venue_id, current_conditions)


# ==================== PLATFORM - FEATURE FLAGS ====================

@router.post("/platform/feature-flags", response_model=Dict[str, Any], tags=["V9 - Platform"])
@limiter.limit("30/minute")
async def create_feature_flag(
    request: Request,
    feature_key: str,
    feature_name: str,
    description: str,
    enabled: bool = False,
    rollout_percentage: int = 0,
    conditions: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a feature flag"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.create_feature_flag(db, venue_id, feature_key, feature_name, description, enabled, rollout_percentage, conditions)


@router.get("/platform/feature-flags/check/{feature_key}", response_model=Dict[str, Any], tags=["V9 - Platform"])
@limiter.limit("60/minute")
async def check_feature(
    request: Request,
    feature_key: str,
    user_id: Optional[int] = None,
    context: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Check if a feature is enabled for a user/context"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.check_feature(db, venue_id, feature_key, user_id, context)


@router.put("/platform/feature-flags/{flag_id}", response_model=Dict[str, Any], tags=["V9 - Platform"])
@limiter.limit("30/minute")
async def update_feature_flag(
    request: Request,
    flag_id: int,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Update a feature flag"""
    return PlatformService.update_feature_flag(db, flag_id, updates)


@router.get("/platform/feature-flags", response_model=List[Dict[str, Any]], tags=["V9 - Platform"])
@limiter.limit("60/minute")
async def get_feature_flags(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all feature flags for a venue"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.get_feature_flags(db, venue_id)


# ==================== PLATFORM - WHITE LABEL ====================

@router.post("/platform/white-label", response_model=Dict[str, Any], tags=["V9 - Platform"])
@limiter.limit("30/minute")
async def set_white_label_config(
    request: Request,
    brand_name: str,
    logo_url: Optional[str] = None,
    primary_color: str = "#2563eb",
    secondary_color: str = "#1e40af",
    accent_color: str = "#f59e0b",
    font_family: str = "Inter",
    custom_css: Optional[str] = None,
    custom_domain: Optional[str] = None,
    email_from_name: Optional[str] = None,
    email_from_address: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Set white-label configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.set_white_label_config(
        db, venue_id, brand_name, logo_url, primary_color, secondary_color,
        accent_color, font_family, custom_css, custom_domain, email_from_name, email_from_address
    )


@router.get("/platform/white-label", response_model=Optional[Dict[str, Any]], tags=["V9 - Platform"])
@limiter.limit("60/minute")
async def get_white_label_config(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get white-label configuration"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return PlatformService.get_white_label_config(db, venue_id)


# ==================== QR - PAY AT TABLE ====================

@router.post("/qr/payment-session", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def create_qr_payment_session(
    request: Request,
    order_id: int,
    table_number: str,
    total_amount: Decimal,
    tip_suggestions: Optional[List[int]] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a QR payment session"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.create_qr_payment_session(db, venue_id, order_id, table_number, total_amount, tip_suggestions)


@router.get("/qr/payment-session/{session_code}", response_model=Optional[Dict[str, Any]], tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def get_payment_session(
    request: Request,
    session_code: str,
    db: Session = Depends(get_db)
):
    """Get payment session by code (no auth required for guest access)"""
    return QRSelfServiceService.get_payment_session(db, session_code)


@router.post("/qr/payment-session/{session_id}/split", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def configure_split_payment(
    request: Request,
    session_id: int,
    split_type: str,
    split_count: int,
    db: Session = Depends(get_db)
):
    """Configure split payment for a session"""
    return QRSelfServiceService.configure_split_payment(db, session_id, split_type, split_count)


@router.post("/qr/payment-session/{session_id}/pay", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def record_qr_payment(
    request: Request,
    session_id: int,
    amount: Decimal,
    tip_amount: Decimal,
    payment_method: str,
    payer_name: Optional[str] = None,
    transaction_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Record a payment in a QR session"""
    return QRSelfServiceService.record_payment(db, session_id, amount, tip_amount, payment_method, payer_name, transaction_id)


# ==================== QR - SCAN TO REORDER ====================

@router.post("/qr/reorder-session", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def create_reorder_session(
    request: Request,
    original_order_id: int,
    table_number: str,
    guest_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a scan-to-reorder session"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.create_reorder_session(db, venue_id, guest_id, original_order_id, table_number)


@router.get("/qr/reorder-session/{session_code}", response_model=Optional[Dict[str, Any]], tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def get_reorder_items(
    request: Request,
    session_code: str,
    db: Session = Depends(get_db)
):
    """Get items from original order for reordering (no auth for guest access)"""
    return QRSelfServiceService.get_reorder_items(db, session_code)


@router.post("/qr/reorder-session/{session_id}/confirm", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def confirm_reorder(
    request: Request,
    session_id: int,
    selected_item_ids: List[int],
    modifications: Optional[Dict[int, str]] = None,
    db: Session = Depends(get_db)
):
    """Confirm reorder with selected items"""
    return QRSelfServiceService.confirm_reorder(db, session_id, selected_item_ids, modifications)


# ==================== QR - TABLE QR CODES ====================

@router.get("/qr/table/{table_number}", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def generate_table_qr(
    request: Request,
    table_number: str,
    qr_type: str = "menu",
    current_user: dict = Depends(get_current_user)
):
    """Generate QR code data for a table"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.generate_table_qr(venue_id, table_number, qr_type)


# ==================== KIOSK - SELF SERVICE ====================

@router.get("/kiosk/menu", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("60/minute")
async def get_kiosk_menu(
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get menu formatted for self-service kiosk"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.get_kiosk_menu(db, venue_id)


@router.post("/kiosk/order", response_model=Dict[str, Any], tags=["V9 - QR & Self-Service"])
@limiter.limit("30/minute")
async def submit_kiosk_order(
    request: Request,
    items: List[Dict[str, Any]],
    payment_method: str,
    guest_name: Optional[str] = None,
    special_instructions: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Submit order from self-service kiosk"""
    venue_id = current_user.venue_id
    if not venue_id:
        raise HTTPException(status_code=400, detail="User has no venue assigned")
    return QRSelfServiceService.submit_kiosk_order(db, venue_id, items, payment_method, guest_name, special_instructions)


# ============================================================================
# MERGED FROM v9_endpoints_part2.py (unique endpoints and helpers only)
# ============================================================================


# ==================== CRM - SEGMENT CUSTOMERS ====================

@router.get("/crm/segments/{segment}/customers", response_model=List[Dict[str, Any]], tags=["V9 - CRM"])
@limiter.limit("60/minute")
async def get_segment_customers(
    request: Request,
    segment: str,
    venue_id: int = Query(1, description="Venue/location ID"),
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get customers in a specific segment"""
    from app.models.advanced_features_v9 import CustomerLifetimeValue

    customers = db.query(CustomerLifetimeValue).filter(
        CustomerLifetimeValue.venue_id == venue_id,
        CustomerLifetimeValue.segment == segment
    ).limit(limit).all()

    return [{
        "guest_id": c.guest_id,
        "segment": c.segment,
        "lifetime_value": float(c.lifetime_value) if c.lifetime_value else 0,
        "visit_count": c.visit_count,
        "average_order_value": float(c.average_order_value) if c.average_order_value else 0,
        "churn_risk_score": float(c.churn_risk_score) if c.churn_risk_score else 0,
        "last_visit_date": c.last_visit_date.isoformat() if c.last_visit_date else None
    } for c in customers]


# ==================== BACKGROUND TASK HELPERS (from part2) ====================

async def send_temperature_alert(result: dict):
    """Send temperature alert notification for HACCP compliance"""
    import logging
    logger = logging.getLogger(__name__)

    device_id = result.get("device_id", "unknown")
    temperature = result.get("temperature")
    status = result.get("status", "unknown")
    zone = result.get("zone", "unknown")

    # Log the temperature alert
    if status == "critical":
        logger.critical(
            f"HACCP CRITICAL: Temperature violation in {zone}! "
            f"Device {device_id}: {temperature}°C - Immediate action required"
        )
    elif status == "warning":
        logger.warning(
            f"HACCP WARNING: Temperature approaching limits in {zone}. "
            f"Device {device_id}: {temperature}°C"
        )
    else:
        logger.info(
            f"Temperature reading: Device {device_id} in {zone}: {temperature}°C - {status}"
        )

    # In production, this would:
    # 1. Store alert in TemperatureLog for audit trail
    # 2. Send push notification to kitchen manager
    # 3. Create incident report if critical
    # 4. Log to HACCP compliance system


async def generate_nra_file(export_id: int):
    """Generate NRA export file in background for Bulgarian tax compliance"""
    import logging
    import xml.etree.ElementTree as ET
    from datetime import datetime
    import os
    import hashlib

    logger = logging.getLogger(__name__)

    logger.info(f"Starting NRA export file generation for export_id: {export_id}")

    try:
        from app.db.session import SessionLocal, get_db
        from app.models import Order, OrderItem, Venue
        from app.models.advanced_features_v9 import NRAExportLog

        db = SessionLocal()

        try:
            # Get export record
            export_record = db.query(NRAExportLog).filter(NRAExportLog.id == export_id).first()
            if not export_record:
                raise ValueError(f"Export record {export_id} not found")

            venue = db.query(Venue).filter(Venue.id == export_record.venue_id).first()
            if not venue:
                raise ValueError(f"Venue {export_record.venue_id} not found")

            venue_name = venue.name
            venue_vat = None
            if hasattr(venue, 'tax_id') and venue.tax_id:
                venue_vat = venue.tax_id
            elif hasattr(venue, 'vat_number') and venue.vat_number:
                venue_vat = venue.vat_number
            elif hasattr(venue, 'eik') and venue.eik:
                venue_vat = venue.eik

            if not venue_vat:
                raise ValueError(
                    f"Venue {venue.name} does not have a tax ID (EIK/BULSTAT) configured. "
                    "Please configure the venue's tax_id before generating NRA exports."
                )

            # Query fiscal transactions for the period
            orders = db.query(Order).filter(
                Order.created_at >= export_record.period_start,
                Order.created_at <= export_record.period_end,
                Order.payment_status == 'paid'
            ).all()

            # Create NRA XML structure (Bulgarian NRA AUDIT.XML format)
            root = ET.Element("AUDIT")
            root.set("xmlns", "http://www.nra.bg/schemas/audit")
            root.set("version", "2.0")

            # Header section
            header = ET.SubElement(root, "HEADER")
            ET.SubElement(header, "EIKPOD").text = venue_vat
            ET.SubElement(header, "COMPANY_NAME").text = venue_name
            ET.SubElement(header, "PERIOD_START").text = export_record.period_start.strftime("%Y-%m-%d")
            ET.SubElement(header, "PERIOD_END").text = export_record.period_end.strftime("%Y-%m-%d")
            ET.SubElement(header, "EXPORT_DATE").text = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            ET.SubElement(header, "EXPORT_TIME").text = datetime.now(timezone.utc).strftime("%H:%M:%S")

            # Transactions section
            transactions = ET.SubElement(root, "TRANSACTIONS")

            # VAT totals
            vat_totals = {"20": 0.0, "9": 0.0, "0": 0.0}
            total_amount = 0.0
            total_vat = 0.0

            for order in orders:
                transaction = ET.SubElement(transactions, "TRANSACTION")

                # UNP - Unique sale number
                unp = f"{venue_vat[:9]}-{order.id:010d}-{order.created_at.strftime('%Y%m%d%H%M%S')}"
                ET.SubElement(transaction, "UNP").text = unp

                # Transaction details
                ET.SubElement(transaction, "DATE").text = order.created_at.strftime("%Y-%m-%d")
                ET.SubElement(transaction, "TIME").text = order.created_at.strftime("%H:%M:%S")
                ET.SubElement(transaction, "ORDER_NUMBER").text = order.order_number or str(order.id)
                ET.SubElement(transaction, "OPERATOR_CODE").text = str(order.waiter_id or 1)

                # Payment method
                payment_type = "1" if order.payment_method == "cash" else "2"  # 1=cash, 2=card
                ET.SubElement(transaction, "PAYMENT_TYPE").text = payment_type

                # Items
                items_elem = ET.SubElement(transaction, "ITEMS")
                order_total = 0.0

                order_items = db.query(OrderItem).filter(OrderItem.order_id == order.id).all()
                for oi in order_items:
                    item = ET.SubElement(items_elem, "ITEM")
                    ET.SubElement(item, "NAME").text = str(oi.menu_item_id)
                    ET.SubElement(item, "QUANTITY").text = str(oi.quantity)
                    ET.SubElement(item, "UNIT_PRICE").text = f"{oi.unit_price:.2f}"
                    ET.SubElement(item, "SUBTOTAL").text = f"{oi.subtotal:.2f}"

                    # Standard VAT rate 20% for Bulgaria
                    vat_rate = "20"
                    vat_amount = oi.subtotal * 0.20 / 1.20
                    ET.SubElement(item, "VAT_RATE").text = vat_rate
                    ET.SubElement(item, "VAT_AMOUNT").text = f"{vat_amount:.2f}"

                    vat_totals[vat_rate] += vat_amount
                    order_total += oi.subtotal

                # Transaction totals
                ET.SubElement(transaction, "TOTAL").text = f"{order.total:.2f}"
                ET.SubElement(transaction, "TIP").text = f"{order.tip_amount:.2f}"
                total_amount += order.total

            # Summary section
            summary = ET.SubElement(root, "SUMMARY")
            ET.SubElement(summary, "TOTAL_TRANSACTIONS").text = str(len(orders))
            ET.SubElement(summary, "TOTAL_AMOUNT").text = f"{total_amount:.2f}"

            # VAT breakdown
            vat_summary = ET.SubElement(summary, "VAT_SUMMARY")
            for rate, amount in vat_totals.items():
                vat_line = ET.SubElement(vat_summary, "VAT_LINE")
                ET.SubElement(vat_line, "RATE").text = rate
                ET.SubElement(vat_line, "AMOUNT").text = f"{amount:.2f}"
                total_vat += amount

            ET.SubElement(summary, "TOTAL_VAT").text = f"{total_vat:.2f}"

            # Generate XML string
            xml_string = ET.tostring(root, encoding='unicode', method='xml')
            xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_string

            # Calculate checksum
            checksum = hashlib.sha256(xml_content.encode('utf-8')).hexdigest()

            # Save file
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"NRA_EXPORT_{export_id}_{timestamp}.xml"

            # Save to exports directory
            export_dir = os.path.join(os.getcwd(), "exports", "nra")
            os.makedirs(export_dir, exist_ok=True)
            file_path = os.path.join(export_dir, filename)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)

            # Update export record
            export_record.file_name = filename
            export_record.file_path = file_path
            export_record.file_size_bytes = len(xml_content.encode('utf-8'))
            export_record.file_checksum = checksum
            export_record.status = "generated"
            export_record.generated_at = datetime.now(timezone.utc)

            db.commit()

            logger.info(f"NRA export file generated: {filename} ({len(orders)} transactions, {total_amount:.2f} BGN)")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to generate NRA export {export_id}: {str(e)}")
        raise
