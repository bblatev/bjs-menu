"""
Legal, Risk, Training & Crisis Management Service - Sections AK, AP, AR
Incident reports, training management, and crisis mode operations
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import uuid


class LegalRiskService:
    """Service for incident reports, legal compliance, and risk management."""
    
    # ==================== INCIDENT REPORTS ====================
    
    @staticmethod
    def create_incident_report(
        db: Session,
        venue_id: int,
        reported_by: int,
        incident_type: str,  # "injury", "property_damage", "theft", "food_safety", "altercation", "other"
        incident_date: datetime,
        location: str,
        description: str,
        severity: str,  # "minor", "moderate", "severe", "critical"
        persons_involved: Optional[List[Dict[str, Any]]] = None,
        witnesses: Optional[List[Dict[str, Any]]] = None,
        immediate_actions: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create an incident report."""
        from app.models.advanced_features_v9 import IncidentReport
        
        report = IncidentReport(
            venue_id=venue_id,
            reported_by=reported_by,
            incident_type=incident_type,
            incident_date=incident_date,
            location=location,
            description=description,
            severity=severity,
            persons_involved=persons_involved or [],
            witnesses=witnesses or [],
            immediate_actions=immediate_actions,
            status="open",
            evidence=[],
            follow_up_actions=[],
            insurance_claim_number=None,
            resolution=None
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        
        return {
            "id": report.id,
            "incident_type": incident_type,
            "severity": severity,
            "status": "open",
            "created_at": report.created_at.isoformat(),
            "message": "Incident report created successfully"
        }
    
    @staticmethod
    def add_evidence(
        db: Session,
        report_id: int,
        evidence_type: str,  # "photo", "video", "document", "statement"
        file_path: str,
        description: str,
        uploaded_by: int
    ) -> Dict[str, Any]:
        """Add evidence to an incident report."""
        from app.models.advanced_features_v9 import IncidentReport
        
        report = db.query(IncidentReport).filter(
            IncidentReport.id == report_id
        ).first()
        
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        evidence = {
            "id": str(uuid.uuid4()),
            "type": evidence_type,
            "file_path": file_path,
            "description": description,
            "uploaded_by": uploaded_by,
            "uploaded_at": datetime.utcnow().isoformat()
        }
        
        current_evidence = report.evidence or []
        current_evidence.append(evidence)
        report.evidence = current_evidence
        report.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "report_id": report_id,
            "evidence_id": evidence["id"],
            "message": "Evidence added successfully"
        }
    
    @staticmethod
    def update_incident_status(
        db: Session,
        report_id: int,
        status: str,
        updated_by: int,
        notes: Optional[str] = None,
        resolution: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update incident report status."""
        from app.models.advanced_features_v9 import IncidentReport
        
        report = db.query(IncidentReport).filter(
            IncidentReport.id == report_id
        ).first()
        
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        report.status = status
        if resolution:
            report.resolution = resolution
            report.resolved_at = datetime.utcnow()
            report.resolved_by = updated_by
        
        # Add to follow-up actions
        follow_up = {
            "action": f"Status changed to {status}",
            "notes": notes,
            "by": updated_by,
            "at": datetime.utcnow().isoformat()
        }
        current_actions = report.follow_up_actions or []
        current_actions.append(follow_up)
        report.follow_up_actions = current_actions
        report.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "report_id": report_id,
            "status": status,
            "resolution": resolution,
            "message": "Status updated"
        }
    
    @staticmethod
    def get_incident_reports(
        db: Session,
        venue_id: int,
        status: Optional[str] = None,
        incident_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get incident reports with filters."""
        from app.models.advanced_features_v9 import IncidentReport
        
        query = db.query(IncidentReport).filter(
            IncidentReport.venue_id == venue_id
        )
        
        if status:
            query = query.filter(IncidentReport.status == status)
        if incident_type:
            query = query.filter(IncidentReport.incident_type == incident_type)
        if start_date:
            query = query.filter(IncidentReport.incident_date >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.filter(IncidentReport.incident_date <= datetime.combine(end_date, datetime.max.time()))
        
        reports = query.order_by(IncidentReport.incident_date.desc()).all()
        
        return [{
            "id": r.id,
            "incident_type": r.incident_type,
            "severity": r.severity,
            "status": r.status,
            "incident_date": r.incident_date.isoformat(),
            "location": r.location,
            "description": r.description[:100] + "..." if len(r.description) > 100 else r.description,
            "evidence_count": len(r.evidence) if r.evidence else 0
        } for r in reports]
    
    @staticmethod
    def link_insurance_claim(
        db: Session,
        report_id: int,
        claim_number: str,
        claim_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Link an insurance claim to an incident report."""
        from app.models.advanced_features_v9 import IncidentReport
        
        report = db.query(IncidentReport).filter(
            IncidentReport.id == report_id
        ).first()
        
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        report.insurance_claim_number = claim_number
        report.insurance_claim_details = claim_details
        report.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "report_id": report_id,
            "claim_number": claim_number,
            "message": "Insurance claim linked"
        }


class TrainingService:
    """Service for staff training and certification management."""
    
    # ==================== TRAINING MODULES ====================
    
    @staticmethod
    def create_training_module(
        db: Session,
        venue_id: int,
        module_name: str,
        module_type: str,  # "onboarding", "safety", "service", "product", "compliance", "advanced"
        description: str,
        content: Dict[str, Any],
        duration_minutes: int,
        required_roles: List[str],
        passing_score: int = 80,
        certification_valid_days: Optional[int] = 365
    ) -> Dict[str, Any]:
        """Create a training module."""
        from app.models.advanced_features_v9 import TrainingModule
        
        module = TrainingModule(
            venue_id=venue_id,
            module_name=module_name,
            module_type=module_type,
            description=description,
            content=content,
            duration_minutes=duration_minutes,
            required_roles=required_roles,
            passing_score=passing_score,
            certification_valid_days=certification_valid_days,
            is_active=True
        )
        db.add(module)
        db.commit()
        db.refresh(module)
        
        return {
            "id": module.id,
            "module_name": module_name,
            "module_type": module_type,
            "duration_minutes": duration_minutes,
            "required_roles": required_roles,
            "message": "Training module created"
        }
    
    @staticmethod
    def get_training_modules(
        db: Session,
        venue_id: int,
        module_type: Optional[str] = None,
        role: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get training modules with filters."""
        from app.models.advanced_features_v9 import TrainingModule
        
        query = db.query(TrainingModule).filter(
            TrainingModule.tenant_id == venue_id,
            TrainingModule.is_active if hasattr(TrainingModule, "is_active") else True == True
        )
        
        if module_type:
            query = query.filter(TrainingModule.module_type == module_type)
        
        modules = query.all()
        
        # Filter by role if specified
        if role:
            modules = [m for m in modules if role in m.required_roles]
        
        return [{
            "id": m.id,
            "module_name": m.module_name,
            "module_type": m.module_type,
            "description": m.description,
            "duration_minutes": m.duration_minutes,
            "required_roles": m.required_roles,
            "passing_score": m.passing_score,
            "certification_valid_days": m.certification_valid_days
        } for m in modules]
    
    # ==================== STAFF TRAINING RECORDS ====================
    
    @staticmethod
    def start_training(
        db: Session,
        staff_id: int,
        module_id: int
    ) -> Dict[str, Any]:
        """Start a training session for a staff member."""
        from app.models.advanced_features_v9 import TrainingModule, StaffTrainingRecord
        
        module = db.query(TrainingModule).filter(
            TrainingModule.id == module_id
        ).first()
        
        if not module:
            raise ValueError(f"Module {module_id} not found")
        
        # Check if already completed and valid
        existing = db.query(StaffTrainingRecord).filter(
            StaffTrainingRecord.staff_id == staff_id,
            StaffTrainingRecord.module_id == module_id,
            StaffTrainingRecord.status == "completed"
        ).first()
        
        if existing and existing.certification_expires:
            if existing.certification_expires > datetime.utcnow():
                return {
                    "message": "Training already completed and certification is valid",
                    "expires": existing.certification_expires.isoformat()
                }
        
        # Create new record
        record = StaffTrainingRecord(
            staff_id=staff_id,
            module_id=module_id,
            venue_id=module.venue_id,
            status="in_progress",
            started_at=datetime.utcnow(),
            score=None,
            completed_at=None,
            certification_expires=None
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        return {
            "record_id": record.id,
            "module_name": module.module_name,
            "status": "in_progress",
            "started_at": record.started_at.isoformat()
        }
    
    @staticmethod
    def complete_training(
        db: Session,
        record_id: int,
        score: int
    ) -> Dict[str, Any]:
        """Complete a training session with score."""
        from app.models.advanced_features_v9 import TrainingModule, StaffTrainingRecord
        
        record = db.query(StaffTrainingRecord).filter(
            StaffTrainingRecord.id == record_id
        ).first()
        
        if not record:
            raise ValueError(f"Training record {record_id} not found")
        
        module = db.query(TrainingModule).filter(
            TrainingModule.id == record.module_id
        ).first()
        
        record.score = score
        record.completed_at = datetime.utcnow()
        
        if score >= module.passing_score:
            record.status = "completed"
            if module.certification_valid_days:
                record.certification_expires = datetime.utcnow() + timedelta(days=module.certification_valid_days)
        else:
            record.status = "failed"
        
        record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(record)
        
        return {
            "record_id": record.id,
            "score": score,
            "passing_score": module.passing_score,
            "passed": score >= module.passing_score,
            "status": record.status,
            "certification_expires": record.certification_expires.isoformat() if record.certification_expires else None
        }
    
    @staticmethod
    def get_staff_training_status(
        db: Session,
        staff_id: int,
        venue_id: int
    ) -> Dict[str, Any]:
        """Get training status for a staff member."""
        from app.models.advanced_features_v9 import TrainingModule, StaffTrainingRecord
        
        # Get all modules
        modules = db.query(TrainingModule).filter(
            TrainingModule.tenant_id == venue_id,
            TrainingModule.is_active if hasattr(TrainingModule, "is_active") else True == True
        ).all()
        
        # Get all records for this staff
        records = db.query(StaffTrainingRecord).filter(
            StaffTrainingRecord.staff_id == staff_id
        ).all()
        
        records_by_module = {r.module_id: r for r in records}
        
        completed = []
        in_progress = []
        required = []
        expiring_soon = []
        
        now = datetime.utcnow()
        soon = now + timedelta(days=30)
        
        for module in modules:
            record = records_by_module.get(module.id)
            
            if record:
                if record.status == "completed":
                    completed.append({
                        "module_id": module.id,
                        "module_name": module.module_name,
                        "score": record.score,
                        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
                        "expires": record.certification_expires.isoformat() if record.certification_expires else None
                    })
                    
                    if record.certification_expires and record.certification_expires < soon:
                        expiring_soon.append({
                            "module_id": module.id,
                            "module_name": module.module_name,
                            "expires": record.certification_expires.isoformat()
                        })
                elif record.status == "in_progress":
                    in_progress.append({
                        "module_id": module.id,
                        "module_name": module.module_name,
                        "started_at": record.started_at.isoformat() if record.started_at else None
                    })
            else:
                required.append({
                    "module_id": module.id,
                    "module_name": module.module_name,
                    "module_type": module.module_type,
                    "duration_minutes": module.duration_minutes
                })
        
        return {
            "staff_id": staff_id,
            "completed": completed,
            "in_progress": in_progress,
            "required": required,
            "expiring_soon": expiring_soon,
            "compliance_percentage": round(len(completed) / len(modules) * 100, 1) if modules else 100
        }
    
    @staticmethod
    def get_expiring_certifications(
        db: Session,
        venue_id: int,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get certifications expiring soon."""
        from app.models.advanced_features_v9 import StaffTrainingRecord, TrainingModule
        
        threshold = datetime.utcnow() + timedelta(days=days_ahead)
        
        expiring = db.query(StaffTrainingRecord).join(TrainingModule).filter(
            TrainingModule.tenant_id == venue_id,
            StaffTrainingRecord.status == "completed",
            StaffTrainingRecord.certification_expires <= threshold,
            StaffTrainingRecord.certification_expires > datetime.utcnow()
        ).all()
        
        return [{
            "staff_id": r.staff_id,
            "module_id": r.module_id,
            "expires": r.certification_expires.isoformat(),
            "days_until_expiry": (r.certification_expires - datetime.utcnow()).days
        } for r in expiring]


class CrisisManagementService:
    """Service for crisis mode operations and emergency procedures."""
    
    # ==================== CRISIS MODE ====================
    
    @staticmethod
    def create_crisis_mode(
        db: Session,
        venue_id: int,
        mode_name: str,
        mode_type: str,  # "pandemic", "economic", "supply_shortage", "staffing_crisis", "natural_disaster", "custom"
        description: str,
        simplified_menu_ids: List[int],
        margin_protection_percentage: Decimal,
        operational_changes: Dict[str, Any],
        auto_activate_conditions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a crisis mode configuration."""
        from app.models.advanced_features_v9 import CrisisMode
        
        crisis = CrisisMode(
            venue_id=venue_id,
            mode_name=mode_name,
            mode_type=mode_type,
            description=description,
            simplified_menu_ids=simplified_menu_ids,
            margin_protection_percentage=margin_protection_percentage,
            operational_changes=operational_changes,
            auto_activate_conditions=auto_activate_conditions,
            is_active=False
        )
        db.add(crisis)
        db.commit()
        db.refresh(crisis)
        
        return {
            "id": crisis.id,
            "mode_name": mode_name,
            "mode_type": mode_type,
            "is_active": False,
            "message": "Crisis mode configuration created"
        }
    
    @staticmethod
    def activate_crisis_mode(
        db: Session,
        crisis_mode_id: int,
        activated_by: int,
        reason: str
    ) -> Dict[str, Any]:
        """Activate a crisis mode."""
        from app.models.advanced_features_v9 import CrisisMode
        
        crisis = db.query(CrisisMode).filter(
            CrisisMode.id == crisis_mode_id
        ).first()
        
        if not crisis:
            raise ValueError(f"Crisis mode {crisis_mode_id} not found")
        
        # Deactivate any other active crisis mode for this venue
        db.query(CrisisMode).filter(
            CrisisMode.venue_id == crisis.venue_id,
            CrisisMode.is_active == True
        ).update({"is_active": False})
        
        crisis.is_active = True
        crisis.activated_at = datetime.utcnow()
        crisis.activated_by = activated_by
        crisis.activation_reason = reason
        crisis.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "id": crisis.id,
            "mode_name": crisis.mode_name,
            "is_active": True,
            "activated_at": crisis.activated_at.isoformat(),
            "operational_changes": crisis.operational_changes,
            "simplified_menu_ids": crisis.simplified_menu_ids,
            "message": f"Crisis mode '{crisis.mode_name}' activated"
        }
    
    @staticmethod
    def deactivate_crisis_mode(
        db: Session,
        venue_id: int,
        deactivated_by: int,
        reason: str
    ) -> Dict[str, Any]:
        """Deactivate the current crisis mode."""
        from app.models.advanced_features_v9 import CrisisMode
        
        active = db.query(CrisisMode).filter(
            CrisisMode.venue_id == venue_id,
            CrisisMode.is_active == True
        ).first()
        
        if not active:
            return {"message": "No active crisis mode to deactivate"}
        
        active.is_active = False
        active.deactivated_at = datetime.utcnow()
        active.deactivated_by = deactivated_by
        active.deactivation_reason = reason
        active.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "id": active.id,
            "mode_name": active.mode_name,
            "is_active": False,
            "deactivated_at": active.deactivated_at.isoformat(),
            "message": f"Crisis mode '{active.mode_name}' deactivated"
        }
    
    @staticmethod
    def get_active_crisis_mode(
        db: Session,
        venue_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get the currently active crisis mode."""
        from app.models.advanced_features_v9 import CrisisMode
        
        active = db.query(CrisisMode).filter(
            CrisisMode.venue_id == venue_id,
            CrisisMode.is_active == True
        ).first()
        
        if not active:
            return None
        
        return {
            "id": active.id,
            "mode_name": active.mode_name,
            "mode_type": active.mode_type,
            "description": active.description,
            "activated_at": active.activated_at.isoformat() if active.activated_at else None,
            "activation_reason": active.activation_reason,
            "simplified_menu_ids": active.simplified_menu_ids,
            "margin_protection_percentage": float(active.margin_protection_percentage),
            "operational_changes": active.operational_changes
        }
    
    @staticmethod
    def get_crisis_modes(
        db: Session,
        venue_id: int
    ) -> List[Dict[str, Any]]:
        """Get all crisis mode configurations."""
        from app.models.advanced_features_v9 import CrisisMode
        
        modes = db.query(CrisisMode).filter(
            CrisisMode.venue_id == venue_id
        ).all()
        
        return [{
            "id": m.id,
            "mode_name": m.mode_name,
            "mode_type": m.mode_type,
            "description": m.description,
            "is_active": m.is_active,
            "simplified_menu_count": len(m.simplified_menu_ids) if m.simplified_menu_ids else 0,
            "margin_protection": float(m.margin_protection_percentage)
        } for m in modes]
    
    @staticmethod
    def check_auto_activation(
        db: Session,
        venue_id: int,
        current_conditions: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Check if any crisis mode should be auto-activated."""
        from app.models.advanced_features_v9 import CrisisMode
        
        modes = db.query(CrisisMode).filter(
            CrisisMode.venue_id == venue_id,
            CrisisMode.is_active == False,
            CrisisMode.auto_activate_conditions.isnot(None)
        ).all()
        
        for mode in modes:
            conditions = mode.auto_activate_conditions
            if not conditions:
                continue
            
            # Check each condition
            all_met = True
            for key, threshold in conditions.items():
                current_value = current_conditions.get(key)
                if current_value is None:
                    all_met = False
                    break
                
                # Simple threshold comparison
                if isinstance(threshold, dict):
                    if threshold.get("operator") == "lt" and current_value >= threshold.get("value"):
                        all_met = False
                    elif threshold.get("operator") == "gt" and current_value <= threshold.get("value"):
                        all_met = False
                else:
                    if current_value < threshold:
                        all_met = False
            
            if all_met:
                return {
                    "crisis_mode_id": mode.id,
                    "mode_name": mode.mode_name,
                    "conditions_met": conditions,
                    "recommendation": "Consider activating this crisis mode"
                }
        
        return None
