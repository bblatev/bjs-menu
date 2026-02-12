"""
HACCP Food Safety Service - BJS V6
===================================
Temperature monitoring, digital logs, supplier tracking, allergen alerts, expiry tracking
with full database integration.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import logging

logger = logging.getLogger(__name__)


class HazardType(str, Enum):
    BIOLOGICAL = "biological"
    CHEMICAL = "chemical"
    PHYSICAL = "physical"
    ALLERGEN = "allergen"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TemperatureZone(str, Enum):
    COLD_STORAGE = "cold_storage"
    FREEZER = "freezer"
    HOT_HOLDING = "hot_holding"
    COOKING = "cooking"
    AMBIENT = "ambient"


# Pydantic models for API responses
class CCPResponse(BaseModel):
    id: int
    name: str
    location: str
    hazard_type: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class TemperatureReadingResponse(BaseModel):
    id: int
    ccp_id: int
    temperature: float
    within_limits: bool
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HACCPFoodSafetyService:
    """Digital HACCP and food safety compliance with database persistence."""

    TEMP_LIMITS = {
        TemperatureZone.COLD_STORAGE: {"min": 0, "max": 4},
        TemperatureZone.FREEZER: {"min": -25, "max": -18},
        TemperatureZone.HOT_HOLDING: {"min": 63, "max": 100},
        TemperatureZone.COOKING: {"min": 75, "max": 100},
    }

    def __init__(self, db_session: Session = None):
        self.db = db_session

    # ==================== CRITICAL CONTROL POINTS ====================

    def create_ccp(self, venue_id: int, name: str, location: str,
                   hazard_type: str, **kwargs) -> Dict[str, Any]:
        """Create a Critical Control Point."""
        from app.models.v6_features_models import CriticalControlPoint

        if not self.db:
            logger.warning("No database session - returning mock response")
            return {"id": 1, "name": name, "venue_id": venue_id}

        if isinstance(hazard_type, HazardType):
            hazard_type = hazard_type.value

        ccp = CriticalControlPoint(
            venue_id=venue_id,
            name=name,
            location=location,
            hazard_type=hazard_type,
            critical_limit_min=kwargs.get('critical_limit_min'),
            critical_limit_max=kwargs.get('critical_limit_max'),
            target_value=kwargs.get('target_value'),
            unit=kwargs.get('unit', 'C'),
            monitoring_frequency_minutes=kwargs.get('monitoring_frequency_minutes', 60),
            sensor_id=kwargs.get('sensor_id'),
            auto_monitoring=kwargs.get('auto_monitoring', False)
        )

        self.db.add(ccp)
        self.db.commit()
        self.db.refresh(ccp)

        logger.info(f"Created CCP {ccp.id}: {name} at {location}")

        return {
            "success": True,
            "id": ccp.id,
            "name": ccp.name,
            "location": ccp.location,
            "hazard_type": ccp.hazard_type,
            "status": ccp.status
        }

    def update_ccp(self, ccp_id: int, **kwargs) -> Dict[str, Any]:
        """Update a Critical Control Point."""
        from app.models.v6_features_models import CriticalControlPoint

        if not self.db:
            return {"success": False, "error": "No database session"}

        ccp = self.db.query(CriticalControlPoint).filter(
            CriticalControlPoint.id == ccp_id
        ).first()

        if not ccp:
            return {"success": False, "error": "CCP not found"}

        allowed = ['name', 'location', 'hazard_type', 'critical_limit_min',
                   'critical_limit_max', 'target_value', 'unit',
                   'monitoring_frequency_minutes', 'sensor_id', 'auto_monitoring', 'active']

        for key, value in kwargs.items():
            if key in allowed and value is not None:
                if key == 'hazard_type' and isinstance(value, HazardType):
                    value = value.value
                setattr(ccp, key, value)

        self.db.commit()
        self.db.refresh(ccp)

        return {"success": True, "id": ccp.id, "name": ccp.name}

    def get_ccps(self, venue_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all CCPs for a venue."""
        from app.models.v6_features_models import CriticalControlPoint

        if not self.db:
            return []

        query = self.db.query(CriticalControlPoint).filter(
            CriticalControlPoint.venue_id == venue_id
        )

        if active_only:
            query = query.filter(CriticalControlPoint.active == True)

        ccps = query.all()

        return [
            {
                "id": c.id,
                "name": c.name,
                "location": c.location,
                "hazard_type": c.hazard_type,
                "critical_limit_min": c.critical_limit_min,
                "critical_limit_max": c.critical_limit_max,
                "target_value": c.target_value,
                "unit": c.unit,
                "monitoring_frequency_minutes": c.monitoring_frequency_minutes,
                "last_reading": c.last_reading,
                "last_reading_at": c.last_reading_at.isoformat() if c.last_reading_at else None,
                "status": c.status,
                "sensor_id": c.sensor_id,
                "auto_monitoring": c.auto_monitoring
            }
            for c in ccps
        ]

    def get_ccp(self, ccp_id: int) -> Optional[Dict[str, Any]]:
        """Get a single CCP."""
        from app.models.v6_features_models import CriticalControlPoint

        if not self.db:
            return None

        ccp = self.db.query(CriticalControlPoint).filter(
            CriticalControlPoint.id == ccp_id
        ).first()

        if not ccp:
            return None

        return {
            "id": ccp.id,
            "venue_id": ccp.venue_id,
            "name": ccp.name,
            "location": ccp.location,
            "hazard_type": ccp.hazard_type,
            "critical_limit_min": ccp.critical_limit_min,
            "critical_limit_max": ccp.critical_limit_max,
            "target_value": ccp.target_value,
            "unit": ccp.unit,
            "monitoring_frequency_minutes": ccp.monitoring_frequency_minutes,
            "last_reading": ccp.last_reading,
            "last_reading_at": ccp.last_reading_at.isoformat() if ccp.last_reading_at else None,
            "status": ccp.status
        }

    # ==================== TEMPERATURE MONITORING ====================

    def record_temperature(self, venue_id: int, ccp_id: int, temperature: float,
                           zone: str, recorded_by: str) -> Dict[str, Any]:
        """Record a temperature reading."""
        from app.models.v6_features_models import TemperatureReading, CriticalControlPoint

        if not self.db:
            return {"success": False, "error": "No database session"}

        ccp = self.db.query(CriticalControlPoint).filter(
            CriticalControlPoint.id == ccp_id
        ).first()

        if isinstance(zone, TemperatureZone):
            zone = zone.value

        limits = self.TEMP_LIMITS.get(TemperatureZone(zone) if zone in [z.value for z in TemperatureZone] else None,
                                       {"min": -50, "max": 100})

        # Check against CCP limits if set, otherwise use zone limits
        if ccp and ccp.critical_limit_min is not None and ccp.critical_limit_max is not None:
            within_limits = ccp.critical_limit_min <= temperature <= ccp.critical_limit_max
        else:
            within_limits = limits["min"] <= temperature <= limits["max"]

        reading = TemperatureReading(
            venue_id=venue_id,
            ccp_id=ccp_id,
            location=ccp.location if ccp else "",
            zone=zone,
            temperature=temperature,
            recorded_by=recorded_by,
            recorded_at=datetime.utcnow(),
            within_limits=within_limits
        )

        self.db.add(reading)

        # Update CCP
        if ccp:
            ccp.last_reading = temperature
            ccp.last_reading_at = datetime.utcnow()
            ccp.status = "normal" if within_limits else "critical"

        self.db.commit()
        self.db.refresh(reading)

        logger.info(f"Recorded temperature {temperature}C at CCP {ccp_id}")

        # Create alert if out of limits
        if not within_limits:
            self._create_alert(venue_id, ccp_id, temperature, zone)

        return {
            "success": True,
            "id": reading.id,
            "ccp_id": ccp_id,
            "temperature": temperature,
            "within_limits": within_limits,
            "recorded_at": reading.recorded_at.isoformat()
        }

    def get_temperature_readings(self, venue_id: int, ccp_id: int = None,
                                  start: date = None, end: date = None) -> List[Dict[str, Any]]:
        """Get temperature readings."""
        from app.models.v6_features_models import TemperatureReading

        if not self.db:
            return []

        query = self.db.query(TemperatureReading).filter(
            TemperatureReading.venue_id == venue_id
        )

        if ccp_id:
            query = query.filter(TemperatureReading.ccp_id == ccp_id)
        if start:
            query = query.filter(func.date(TemperatureReading.recorded_at) >= start)
        if end:
            query = query.filter(func.date(TemperatureReading.recorded_at) <= end)

        readings = query.order_by(TemperatureReading.recorded_at.desc()).all()

        return [
            {
                "id": r.id,
                "ccp_id": r.ccp_id,
                "location": r.location,
                "zone": r.zone,
                "temperature": r.temperature,
                "recorded_by": r.recorded_by,
                "recorded_at": r.recorded_at.isoformat(),
                "within_limits": r.within_limits,
                "corrective_action": r.corrective_action
            }
            for r in readings
        ]

    def _create_alert(self, venue_id: int, ccp_id: int, temperature: float, zone: str):
        """Create HACCP temperature violation alert."""
        logger.warning(
            f"HACCP ALERT: Temperature violation at venue {venue_id}, "
            f"CCP {ccp_id}, Zone {zone}: {temperature}C"
        )

        # Store alert in database
        if self.db:
            try:
                from app.models import AuditLog

                audit_log = AuditLog(
                    venue_id=venue_id,
                    action="haccp_temperature_alert",
                    entity_type="temperature_reading",
                    new_values={
                        "ccp_id": ccp_id,
                        "temperature": temperature,
                        "zone": zone,
                        "alert_type": "violation"
                    },
                    notes=f"HACCP temperature violation: {temperature}C in {zone} at CCP {ccp_id}"
                )
                self.db.add(audit_log)
                self.db.commit()
            except Exception as e:
                logger.error(f"Failed to store HACCP alert: {e}")

    # ==================== FOOD BATCHES ====================

    def register_batch(self, venue_id: int, item_name: str, batch_number: str,
                       expiry_date: date, quantity: float, unit: str,
                       storage_location: str, **kwargs) -> Dict[str, Any]:
        """Register a food batch."""
        from app.models.v6_features_models import HACCPFoodBatch

        if not self.db:
            return {"success": False, "error": "No database session"}

        batch = HACCPFoodBatch(
            venue_id=venue_id,
            item_name=item_name,
            batch_number=batch_number,
            received_date=date.today(),
            expiry_date=expiry_date,
            quantity=quantity,
            unit=unit,
            storage_location=storage_location,
            supplier_id=kwargs.get('supplier_id'),
            allergens=kwargs.get('allergens', [])
        )

        self.db.add(batch)
        self.db.commit()
        self.db.refresh(batch)

        logger.info(f"Registered batch {batch.id}: {item_name}")

        return {
            "success": True,
            "id": batch.id,
            "item_name": batch.item_name,
            "batch_number": batch.batch_number,
            "expiry_date": batch.expiry_date.isoformat()
        }

    def get_batches(self, venue_id: int, status: str = None) -> List[Dict[str, Any]]:
        """Get food batches."""
        from app.models.v6_features_models import HACCPFoodBatch

        if not self.db:
            return []

        query = self.db.query(HACCPFoodBatch).filter(
            HACCPFoodBatch.venue_id == venue_id
        )

        if status:
            query = query.filter(HACCPFoodBatch.status == status)

        batches = query.order_by(HACCPFoodBatch.expiry_date.asc()).all()

        return [
            {
                "id": b.id,
                "item_name": b.item_name,
                "batch_number": b.batch_number,
                "received_date": b.received_date.isoformat(),
                "expiry_date": b.expiry_date.isoformat(),
                "quantity": b.quantity,
                "unit": b.unit,
                "storage_location": b.storage_location,
                "allergens": b.allergens,
                "status": b.status,
                "days_until_expiry": (b.expiry_date - date.today()).days
            }
            for b in batches
        ]

    def get_expiring_batches(self, venue_id: int, days: int = 3) -> List[Dict[str, Any]]:
        """Get batches expiring soon."""
        from app.models.v6_features_models import HACCPFoodBatch

        if not self.db:
            return []

        threshold = date.today() + timedelta(days=days)

        batches = self.db.query(HACCPFoodBatch).filter(
            HACCPFoodBatch.venue_id == venue_id,
            HACCPFoodBatch.status == "active",
            HACCPFoodBatch.expiry_date <= threshold
        ).order_by(HACCPFoodBatch.expiry_date.asc()).all()

        return [
            {
                "id": b.id,
                "item_name": b.item_name,
                "batch_number": b.batch_number,
                "expiry_date": b.expiry_date.isoformat(),
                "storage_location": b.storage_location,
                "days_until_expiry": (b.expiry_date - date.today()).days
            }
            for b in batches
        ]

    def update_batch_status(self, batch_id: int, status: str) -> Dict[str, Any]:
        """Update batch status."""
        from app.models.v6_features_models import HACCPFoodBatch

        if not self.db:
            return {"success": False, "error": "No database session"}

        batch = self.db.query(HACCPFoodBatch).filter(
            HACCPFoodBatch.id == batch_id
        ).first()

        if not batch:
            return {"success": False, "error": "Batch not found"}

        batch.status = status
        self.db.commit()

        return {"success": True, "batch_id": batch_id, "status": status}

    def check_allergen_conflict(self, venue_id: int,
                                 order_allergens: List[str]) -> List[Dict[str, Any]]:
        """Check for potential allergen cross-contamination."""
        from app.models.v6_features_models import HACCPFoodBatch

        if not self.db:
            return []

        batches = self.db.query(HACCPFoodBatch).filter(
            HACCPFoodBatch.venue_id == venue_id,
            HACCPFoodBatch.status == "active"
        ).all()

        conflicts = []
        for batch in batches:
            common = set(batch.allergens or []) & set(order_allergens)
            if common:
                conflicts.append({
                    "batch_id": batch.id,
                    "item": batch.item_name,
                    "allergens": list(common),
                    "location": batch.storage_location
                })

        return conflicts

    # ==================== SUPPLIER CERTIFICATIONS ====================

    def add_certification(self, venue_id: int, supplier_id: int, supplier_name: str,
                          certification_type: str, certificate_number: str,
                          issued_date: date, expiry_date: date,
                          document_url: str = None) -> Dict[str, Any]:
        """Add supplier certification."""
        from app.models.v6_features_models import HACCPSupplierCertification

        if not self.db:
            return {"success": False, "error": "No database session"}

        cert = HACCPSupplierCertification(
            venue_id=venue_id,
            supplier_id=supplier_id,
            supplier_name=supplier_name,
            certification_type=certification_type,
            certificate_number=certificate_number,
            issued_date=issued_date,
            expiry_date=expiry_date,
            document_url=document_url
        )

        self.db.add(cert)
        self.db.commit()
        self.db.refresh(cert)

        logger.info(f"Added certification {cert.id} for supplier {supplier_name}")

        return {
            "success": True,
            "id": cert.id,
            "supplier_name": supplier_name,
            "certification_type": certification_type,
            "expiry_date": expiry_date.isoformat()
        }

    def get_certifications(self, venue_id: int, supplier_id: int = None) -> List[Dict[str, Any]]:
        """Get supplier certifications."""
        from app.models.v6_features_models import HACCPSupplierCertification

        if not self.db:
            return []

        query = self.db.query(HACCPSupplierCertification).filter(
            HACCPSupplierCertification.venue_id == venue_id
        )

        if supplier_id:
            query = query.filter(HACCPSupplierCertification.supplier_id == supplier_id)

        certs = query.order_by(HACCPSupplierCertification.expiry_date.asc()).all()

        return [
            {
                "id": c.id,
                "supplier_id": c.supplier_id,
                "supplier_name": c.supplier_name,
                "certification_type": c.certification_type,
                "certificate_number": c.certificate_number,
                "issued_date": c.issued_date.isoformat(),
                "expiry_date": c.expiry_date.isoformat(),
                "document_url": c.document_url,
                "verified": c.verified,
                "days_until_expiry": (c.expiry_date - date.today()).days
            }
            for c in certs
        ]

    def get_expiring_certifications(self, venue_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get certifications expiring soon."""
        from app.models.v6_features_models import HACCPSupplierCertification

        if not self.db:
            return []

        threshold = date.today() + timedelta(days=days)

        certs = self.db.query(HACCPSupplierCertification).filter(
            HACCPSupplierCertification.venue_id == venue_id,
            HACCPSupplierCertification.expiry_date <= threshold
        ).order_by(HACCPSupplierCertification.expiry_date.asc()).all()

        return [
            {
                "id": c.id,
                "supplier_name": c.supplier_name,
                "certification_type": c.certification_type,
                "expiry_date": c.expiry_date.isoformat(),
                "days_until_expiry": (c.expiry_date - date.today()).days
            }
            for c in certs
        ]

    # ==================== INSPECTIONS ====================

    def create_checklist(self, venue_id: int, inspection_type: str,
                         inspector_name: str, items: List[Dict]) -> Dict[str, Any]:
        """Create an inspection checklist."""
        from app.models.v6_features_models import HACCPInspectionChecklist

        if not self.db:
            return {"success": False, "error": "No database session"}

        checklist = HACCPInspectionChecklist(
            venue_id=venue_id,
            inspection_type=inspection_type,
            inspection_date=date.today(),
            inspector_name=inspector_name,
            items=items
        )

        self.db.add(checklist)
        self.db.commit()
        self.db.refresh(checklist)

        logger.info(f"Created checklist {checklist.id} for {inspection_type}")

        return {
            "success": True,
            "id": checklist.id,
            "inspection_type": inspection_type,
            "inspection_date": checklist.inspection_date.isoformat(),
            "items_count": len(items)
        }

    def complete_checklist(self, checklist_id: int, results: List[Dict],
                            notes: str = None) -> Dict[str, Any]:
        """Complete an inspection checklist."""
        from app.models.v6_features_models import HACCPInspectionChecklist

        if not self.db:
            return {"success": False, "error": "No database session"}

        checklist = self.db.query(HACCPInspectionChecklist).filter(
            HACCPInspectionChecklist.id == checklist_id
        ).first()

        if not checklist:
            return {"success": False, "error": "Checklist not found"}

        checklist.items = results
        passed_items = sum(1 for r in results if r.get("passed", False))
        checklist.overall_score = (passed_items / len(results) * 100) if results else 100
        checklist.passed = checklist.overall_score >= 80
        checklist.notes = notes
        checklist.completed_at = datetime.utcnow()

        self.db.commit()

        logger.info(f"Completed checklist {checklist_id} with score {checklist.overall_score}")

        return {
            "success": True,
            "checklist_id": checklist_id,
            "overall_score": float(checklist.overall_score),
            "passed": checklist.passed
        }

    def get_checklists(self, venue_id: int, start: date = None,
                       end: date = None) -> List[Dict[str, Any]]:
        """Get inspection checklists."""
        from app.models.v6_features_models import HACCPInspectionChecklist

        if not self.db:
            return []

        query = self.db.query(HACCPInspectionChecklist).filter(
            HACCPInspectionChecklist.venue_id == venue_id
        )

        if start:
            query = query.filter(HACCPInspectionChecklist.inspection_date >= start)
        if end:
            query = query.filter(HACCPInspectionChecklist.inspection_date <= end)

        checklists = query.order_by(HACCPInspectionChecklist.inspection_date.desc()).all()

        return [
            {
                "id": c.id,
                "inspection_type": c.inspection_type,
                "inspection_date": c.inspection_date.isoformat(),
                "inspector_name": c.inspector_name,
                "overall_score": float(c.overall_score),
                "passed": c.passed,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None
            }
            for c in checklists
        ]

    # ==================== CORRECTIVE ACTIONS ====================

    def create_corrective_action(self, venue_id: int, incident_type: str,
                                  description: str, severity: str,
                                  immediate_action: str, responsible_person: str,
                                  ccp_id: int = None) -> Dict[str, Any]:
        """Create a corrective action."""
        from app.models.v6_features_models import HACCPCorrectiveAction

        if not self.db:
            return {"success": False, "error": "No database session"}

        if isinstance(severity, Severity):
            severity = severity.value

        action = HACCPCorrectiveAction(
            venue_id=venue_id,
            ccp_id=ccp_id,
            incident_type=incident_type,
            incident_date=datetime.utcnow(),
            description=description,
            severity=severity,
            immediate_action=immediate_action,
            responsible_person=responsible_person
        )

        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)

        logger.info(f"Created corrective action {action.id}: {incident_type}")

        return {
            "success": True,
            "id": action.id,
            "incident_type": incident_type,
            "severity": severity,
            "status": action.status
        }

    def complete_corrective_action(self, action_id: int, root_cause: str,
                                    preventive_measures: str,
                                    verified_by: str = None) -> Dict[str, Any]:
        """Complete a corrective action."""
        from app.models.v6_features_models import HACCPCorrectiveAction

        if not self.db:
            return {"success": False, "error": "No database session"}

        action = self.db.query(HACCPCorrectiveAction).filter(
            HACCPCorrectiveAction.id == action_id
        ).first()

        if not action:
            return {"success": False, "error": "Action not found"}

        action.root_cause = root_cause
        action.preventive_measures = preventive_measures
        action.status = "completed"
        action.completed_at = datetime.utcnow()
        action.verified_by = verified_by

        self.db.commit()

        logger.info(f"Completed corrective action {action_id}")

        return {
            "success": True,
            "action_id": action_id,
            "status": action.status,
            "completed_at": action.completed_at.isoformat()
        }

    def get_corrective_actions(self, venue_id: int, status: str = None,
                                start: date = None, end: date = None) -> List[Dict[str, Any]]:
        """Get corrective actions."""
        from app.models.v6_features_models import HACCPCorrectiveAction

        if not self.db:
            return []

        query = self.db.query(HACCPCorrectiveAction).filter(
            HACCPCorrectiveAction.venue_id == venue_id
        )

        if status:
            query = query.filter(HACCPCorrectiveAction.status == status)
        if start:
            query = query.filter(func.date(HACCPCorrectiveAction.incident_date) >= start)
        if end:
            query = query.filter(func.date(HACCPCorrectiveAction.incident_date) <= end)

        actions = query.order_by(HACCPCorrectiveAction.incident_date.desc()).all()

        return [
            {
                "id": a.id,
                "ccp_id": a.ccp_id,
                "incident_type": a.incident_type,
                "incident_date": a.incident_date.isoformat(),
                "description": a.description,
                "severity": a.severity,
                "immediate_action": a.immediate_action,
                "root_cause": a.root_cause,
                "preventive_measures": a.preventive_measures,
                "responsible_person": a.responsible_person,
                "status": a.status,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None
            }
            for a in actions
        ]

    def list_ccps(self, venue_id: int, status: str = None,
                  hazard_type: str = None, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all Critical Control Points with optional filtering."""
        from app.models.v6_features_models import CriticalControlPoint

        if not self.db:
            return []

        query = self.db.query(CriticalControlPoint).filter(
            CriticalControlPoint.venue_id == venue_id
        )

        if active_only:
            query = query.filter(CriticalControlPoint.active == True)

        if status:
            query = query.filter(CriticalControlPoint.status == status)

        if hazard_type:
            if isinstance(hazard_type, HazardType):
                hazard_type = hazard_type.value
            query = query.filter(CriticalControlPoint.hazard_type == hazard_type)

        ccps = query.order_by(
            CriticalControlPoint.status.desc(),  # Critical first
            CriticalControlPoint.location
        ).all()

        return [
            {
                "id": c.id,
                "venue_id": c.venue_id,
                "name": c.name,
                "location": c.location,
                "hazard_type": c.hazard_type,
                "critical_limit_min": c.critical_limit_min,
                "critical_limit_max": c.critical_limit_max,
                "target_value": c.target_value,
                "unit": c.unit,
                "monitoring_frequency_minutes": c.monitoring_frequency_minutes,
                "last_reading": c.last_reading,
                "last_reading_at": c.last_reading_at.isoformat() if c.last_reading_at else None,
                "status": c.status,
                "sensor_id": c.sensor_id,
                "auto_monitoring": c.auto_monitoring,
                "active": c.active,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat()
            }
            for c in ccps
        ]

    def get_overdue_readings(self, venue_id: int,
                             grace_period_minutes: int = 15) -> List[Dict[str, Any]]:
        """Get CCPs with overdue temperature readings based on monitoring frequency."""
        from app.models.v6_features_models import CriticalControlPoint

        if not self.db:
            return []

        # Get all active CCPs
        ccps = self.db.query(CriticalControlPoint).filter(
            CriticalControlPoint.venue_id == venue_id,
            CriticalControlPoint.active == True
        ).all()

        overdue_list = []
        now = datetime.utcnow()

        for ccp in ccps:
            # Skip auto-monitored CCPs
            if ccp.auto_monitoring:
                continue

            # Check if reading is overdue
            monitoring_interval = timedelta(minutes=ccp.monitoring_frequency_minutes)
            grace_interval = timedelta(minutes=grace_period_minutes)
            total_interval = monitoring_interval + grace_interval

            if ccp.last_reading_at:
                time_since_reading = now - ccp.last_reading_at
                is_overdue = time_since_reading > total_interval
            else:
                # Never had a reading - definitely overdue
                is_overdue = True
                time_since_reading = None

            if is_overdue:
                overdue_item = {
                    "ccp_id": ccp.id,
                    "name": ccp.name,
                    "location": ccp.location,
                    "hazard_type": ccp.hazard_type,
                    "status": ccp.status,
                    "monitoring_frequency_minutes": ccp.monitoring_frequency_minutes,
                    "last_reading": ccp.last_reading,
                    "last_reading_at": ccp.last_reading_at.isoformat() if ccp.last_reading_at else None,
                    "minutes_overdue": int(time_since_reading.total_seconds() / 60) - ccp.monitoring_frequency_minutes if time_since_reading else None,
                    "expected_by": (ccp.last_reading_at + monitoring_interval).isoformat() if ccp.last_reading_at else "immediately",
                    "severity": self._calculate_overdue_severity(time_since_reading, monitoring_interval) if time_since_reading else "critical"
                }
                overdue_list.append(overdue_item)

        # Sort by severity and minutes overdue
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        overdue_list.sort(key=lambda x: (
            severity_order.get(x["severity"], 4),
            -(x["minutes_overdue"] or 999999)
        ))

        return overdue_list

    def _calculate_overdue_severity(self, time_since_reading: timedelta,
                                     monitoring_interval: timedelta) -> str:
        """Calculate severity of overdue reading."""
        if not time_since_reading:
            return "critical"

        overdue_ratio = time_since_reading / monitoring_interval

        if overdue_ratio >= 3:
            return "critical"
        elif overdue_ratio >= 2:
            return "high"
        elif overdue_ratio >= 1.5:
            return "medium"
        else:
            return "low"

    def get_compliance_report(self, venue_id: int, start: date,
                              end: date, include_details: bool = False) -> Dict[str, Any]:
        """Generate comprehensive HACCP compliance report for a period."""
        from app.models.v6_features_models import (
            CriticalControlPoint, TemperatureReading, HACCPFoodBatch,
            HACCPSupplierCertification, HACCPInspectionChecklist,
            HACCPCorrectiveAction
        )

        if not self.db:
            return {"error": "No database session"}

        # Get all CCPs
        ccps = self.db.query(CriticalControlPoint).filter(
            CriticalControlPoint.venue_id == venue_id
        ).all()

        # Get temperature readings for the period
        readings = self.db.query(TemperatureReading).filter(
            TemperatureReading.venue_id == venue_id,
            func.date(TemperatureReading.recorded_at) >= start,
            func.date(TemperatureReading.recorded_at) <= end
        ).all()

        # Calculate compliance metrics
        total_readings = len(readings)
        compliant_readings = len([r for r in readings if r.within_limits])
        non_compliant_readings = total_readings - compliant_readings
        compliance_rate = (compliant_readings / total_readings * 100) if total_readings > 0 else 100

        # Readings by CCP
        readings_by_ccp = {}
        violations_by_ccp = {}
        for reading in readings:
            ccp_id = reading.ccp_id
            if ccp_id not in readings_by_ccp:
                readings_by_ccp[ccp_id] = 0
                violations_by_ccp[ccp_id] = 0
            readings_by_ccp[ccp_id] += 1
            if not reading.within_limits:
                violations_by_ccp[ccp_id] += 1

        # Get inspections
        inspections = self.db.query(HACCPInspectionChecklist).filter(
            HACCPInspectionChecklist.venue_id == venue_id,
            HACCPInspectionChecklist.inspection_date >= start,
            HACCPInspectionChecklist.inspection_date <= end
        ).all()

        completed_inspections = [i for i in inspections if i.completed_at]
        passed_inspections = [i for i in completed_inspections if i.passed]
        avg_inspection_score = (
            sum(float(i.overall_score) for i in completed_inspections) / len(completed_inspections)
            if completed_inspections else 0
        )

        # Get corrective actions
        actions = self.db.query(HACCPCorrectiveAction).filter(
            HACCPCorrectiveAction.venue_id == venue_id,
            func.date(HACCPCorrectiveAction.incident_date) >= start,
            func.date(HACCPCorrectiveAction.incident_date) <= end
        ).all()

        pending_actions = [a for a in actions if a.status == 'pending']
        completed_actions = [a for a in actions if a.status == 'completed']
        action_completion_rate = (
            len(completed_actions) / len(actions) * 100
            if actions else 100
        )

        # Get expiring items
        expiring_batches = self.db.query(HACCPFoodBatch).filter(
            HACCPFoodBatch.venue_id == venue_id,
            HACCPFoodBatch.status == "active",
            HACCPFoodBatch.expiry_date <= end,
            HACCPFoodBatch.expiry_date >= start
        ).count()

        expiring_certs = self.db.query(HACCPSupplierCertification).filter(
            HACCPSupplierCertification.venue_id == venue_id,
            HACCPSupplierCertification.expiry_date <= end,
            HACCPSupplierCertification.expiry_date >= start
        ).count()

        # Calculate overall compliance score
        # Weighted score: 40% temp compliance, 30% inspections, 20% corrective actions, 10% certifications
        temp_score = compliance_rate
        inspection_score = avg_inspection_score
        action_score = action_completion_rate
        cert_score = 100 if expiring_certs == 0 else max(0, 100 - (expiring_certs * 10))

        overall_score = (
            temp_score * 0.4 +
            inspection_score * 0.3 +
            action_score * 0.2 +
            cert_score * 0.1
        )

        # Determine compliance status
        if overall_score >= 95:
            compliance_status = "excellent"
        elif overall_score >= 85:
            compliance_status = "good"
        elif overall_score >= 75:
            compliance_status = "satisfactory"
        elif overall_score >= 60:
            compliance_status = "needs_improvement"
        else:
            compliance_status = "non_compliant"

        report = {
            "venue_id": venue_id,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "generated_at": datetime.utcnow().isoformat(),
            "overall_score": round(overall_score, 2),
            "compliance_status": compliance_status,
            "temperature_monitoring": {
                "total_readings": total_readings,
                "compliant_readings": compliant_readings,
                "non_compliant_readings": non_compliant_readings,
                "compliance_rate": round(compliance_rate, 2),
                "ccps_monitored": len(readings_by_ccp),
                "ccps_with_violations": len([v for v in violations_by_ccp.values() if v > 0])
            },
            "inspections": {
                "total": len(inspections),
                "completed": len(completed_inspections),
                "passed": len(passed_inspections),
                "failed": len(completed_inspections) - len(passed_inspections),
                "average_score": round(avg_inspection_score, 2)
            },
            "corrective_actions": {
                "total": len(actions),
                "pending": len(pending_actions),
                "completed": len(completed_actions),
                "completion_rate": round(action_completion_rate, 2),
                "by_severity": {
                    "critical": len([a for a in actions if a.severity == "critical"]),
                    "high": len([a for a in actions if a.severity == "high"]),
                    "medium": len([a for a in actions if a.severity == "medium"]),
                    "low": len([a for a in actions if a.severity == "low"])
                }
            },
            "food_safety": {
                "expiring_batches": expiring_batches,
                "expiring_certifications": expiring_certs
            },
            "critical_issues": self._identify_critical_issues(
                ccps, readings, violations_by_ccp, pending_actions
            ),
            "recommendations": self._generate_recommendations(
                compliance_rate, avg_inspection_score, action_completion_rate,
                expiring_certs, len(pending_actions)
            )
        }

        # Add detailed breakdowns if requested
        if include_details:
            report["details"] = {
                "ccp_performance": [
                    {
                        "ccp_id": ccp.id,
                        "name": ccp.name,
                        "location": ccp.location,
                        "total_readings": readings_by_ccp.get(ccp.id, 0),
                        "violations": violations_by_ccp.get(ccp.id, 0),
                        "compliance_rate": round(
                            ((readings_by_ccp.get(ccp.id, 0) - violations_by_ccp.get(ccp.id, 0)) /
                             readings_by_ccp.get(ccp.id, 1) * 100), 2
                        ) if readings_by_ccp.get(ccp.id, 0) > 0 else 100
                    }
                    for ccp in ccps
                ],
                "recent_violations": [
                    {
                        "ccp_id": r.ccp_id,
                        "location": r.location,
                        "temperature": r.temperature,
                        "recorded_at": r.recorded_at.isoformat(),
                        "recorded_by": r.recorded_by,
                        "corrective_action": r.corrective_action
                    }
                    for r in sorted(readings, key=lambda x: x.recorded_at, reverse=True)[:10]
                    if not r.within_limits
                ]
            }

        return report

    def _identify_critical_issues(self, ccps: List, readings: List,
                                   violations_by_ccp: Dict, pending_actions: List) -> List[Dict[str, Any]]:
        """Identify critical HACCP issues that need immediate attention."""
        issues = []

        # Check for CCPs with high violation rates
        for ccp in ccps:
            ccp_readings = sum(1 for r in readings if r.ccp_id == ccp.id)
            if ccp_readings > 0:
                violation_rate = (violations_by_ccp.get(ccp.id, 0) / ccp_readings) * 100
                if violation_rate > 20:  # More than 20% violations
                    issues.append({
                        "type": "high_violation_rate",
                        "severity": "critical" if violation_rate > 50 else "high",
                        "ccp_id": ccp.id,
                        "ccp_name": ccp.name,
                        "location": ccp.location,
                        "violation_rate": round(violation_rate, 2),
                        "message": f"CCP '{ccp.name}' at {ccp.location} has {violation_rate:.1f}% violation rate"
                    })

        # Check for pending critical corrective actions
        critical_pending = [a for a in pending_actions if a.severity in ['critical', 'high']]
        if critical_pending:
            issues.append({
                "type": "pending_critical_actions",
                "severity": "critical",
                "count": len(critical_pending),
                "message": f"{len(critical_pending)} critical/high severity corrective actions pending"
            })

        # Check for CCPs with no recent readings
        now = datetime.utcnow()
        for ccp in ccps:
            if ccp.active and not ccp.auto_monitoring:
                if not ccp.last_reading_at:
                    issues.append({
                        "type": "missing_readings",
                        "severity": "high",
                        "ccp_id": ccp.id,
                        "ccp_name": ccp.name,
                        "location": ccp.location,
                        "message": f"CCP '{ccp.name}' has never been monitored"
                    })
                else:
                    time_since = now - ccp.last_reading_at
                    expected_interval = timedelta(minutes=ccp.monitoring_frequency_minutes)
                    if time_since > expected_interval * 2:
                        issues.append({
                            "type": "overdue_reading",
                            "severity": "high",
                            "ccp_id": ccp.id,
                            "ccp_name": ccp.name,
                            "location": ccp.location,
                            "hours_overdue": round(time_since.total_seconds() / 3600, 1),
                            "message": f"CCP '{ccp.name}' reading is {round(time_since.total_seconds() / 3600, 1)} hours overdue"
                        })

        return issues

    def _generate_recommendations(self, compliance_rate: float, avg_inspection_score: float,
                                   action_completion_rate: float, expiring_certs: int,
                                   pending_actions_count: int) -> List[str]:
        """Generate recommendations based on compliance metrics."""
        recommendations = []

        if compliance_rate < 95:
            recommendations.append(
                "Improve temperature monitoring compliance. Consider implementing automated monitoring systems."
            )

        if compliance_rate < 85:
            recommendations.append(
                "CRITICAL: Temperature compliance is below acceptable standards. "
                "Review CCP procedures and staff training immediately."
            )

        if avg_inspection_score < 85:
            recommendations.append(
                "Inspection scores indicate areas for improvement. "
                "Review failed checklist items and implement corrective measures."
            )

        if action_completion_rate < 80:
            recommendations.append(
                "Corrective action completion rate is low. "
                "Prioritize pending actions and assign clear responsibilities."
            )

        if expiring_certs > 0:
            recommendations.append(
                f"Renew {expiring_certs} expiring supplier certifications to maintain compliance."
            )

        if pending_actions_count > 5:
            recommendations.append(
                "High number of pending corrective actions. "
                "Conduct review meeting to address backlog."
            )

        if not recommendations:
            recommendations.append(
                "Excellent HACCP compliance. Continue current monitoring and documentation practices."
            )

        return recommendations

    # ==================== REPORTS & DASHBOARD ====================

    def generate_haccp_report(self, venue_id: int, start: date, end: date) -> Dict[str, Any]:
        """Generate HACCP compliance report."""
        readings = self.get_temperature_readings(venue_id, start=start, end=end)
        out_of_limit = [r for r in readings if not r['within_limits']]

        checklists = self.get_checklists(venue_id, start=start, end=end)
        completed = [c for c in checklists if c['completed_at']]

        actions = self.get_corrective_actions(venue_id, start=start, end=end)

        return {
            "period": f"{start} to {end}",
            "temperature_readings": len(readings),
            "out_of_limit_readings": len(out_of_limit),
            "compliance_rate": ((len(readings) - len(out_of_limit)) / len(readings) * 100)
            if readings else 100,
            "inspections_completed": len(completed),
            "avg_inspection_score": sum(c['overall_score'] for c in checklists) / len(checklists)
            if checklists else 0,
            "corrective_actions": len(actions),
            "pending_actions": len([a for a in actions if a['status'] == 'pending']),
            "expiring_batches": len(self.get_expiring_batches(venue_id)),
            "expiring_certifications": len(self.get_expiring_certifications(venue_id))
        }

    def get_dashboard(self, venue_id: int) -> Dict[str, Any]:
        """Get HACCP dashboard data."""
        today = date.today()
        week_ago = today - timedelta(days=7)

        ccps = self.get_ccps(venue_id)
        critical_ccps = [c for c in ccps if c['status'] == 'critical']

        readings_today = self.get_temperature_readings(venue_id, start=today, end=today)
        out_of_limit_today = [r for r in readings_today if not r['within_limits']]

        pending_actions = self.get_corrective_actions(venue_id, status='pending')

        return {
            "date": today.isoformat(),
            "ccps_total": len(ccps),
            "ccps_critical": len(critical_ccps),
            "readings_today": len(readings_today),
            "out_of_limit_today": len(out_of_limit_today),
            "pending_actions": len(pending_actions),
            "expiring_batches_3_days": len(self.get_expiring_batches(venue_id, 3)),
            "expiring_certs_30_days": len(self.get_expiring_certifications(venue_id, 30)),
            "compliance_rate_week": self._calculate_weekly_compliance(venue_id, week_ago, today),
            "critical_ccps": critical_ccps[:5],  # Top 5 critical
            "recent_actions": pending_actions[:5]  # Top 5 pending actions
        }

    def _calculate_weekly_compliance(self, venue_id: int, start: date, end: date) -> float:
        """Calculate weekly temperature compliance rate."""
        readings = self.get_temperature_readings(venue_id, start=start, end=end)
        if not readings:
            return 100.0

        compliant = len([r for r in readings if r['within_limits']])
        return round(compliant / len(readings) * 100, 2)
