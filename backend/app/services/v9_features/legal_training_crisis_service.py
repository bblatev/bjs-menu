"""
Legal, Training & Crisis Management Service Stub
==================================================
Service stub for V9 features covering legal risk/incident management,
staff training and certification, and crisis mode management.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any


class LegalRiskService:
    """Service for legal risk and incident management.

    Note: Methods are called as class methods in the route files.
    """

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def create_incident_report(db, venue_id: int, reported_by: int, incident_type: str,
                               incident_date: datetime, location: str, description: str,
                               severity: str, persons_involved: list = None,
                               witnesses: list = None,
                               immediate_actions: str = None) -> dict:
        """Create an incident report."""
        return {
            "id": 1,
            "venue_id": venue_id,
            "incident_type": incident_type,
            "severity": severity,
            "status": "open",
            "reported_by": reported_by,
        }

    @staticmethod
    def add_evidence(db, report_id: int, evidence_type: str, file_path: str,
                     description: str, uploaded_by: int) -> dict:
        """Add evidence to an incident report."""
        return {
            "id": 1,
            "report_id": report_id,
            "evidence_type": evidence_type,
        }

    @staticmethod
    def update_incident_status(db, report_id: int, status: str,
                               updated_by: int, notes: str = None,
                               resolution: str = None) -> dict:
        """Update incident report status."""
        return {
            "report_id": report_id,
            "status": status,
        }

    @staticmethod
    def get_incident_reports(db, venue_id: int, status: str = None,
                             incident_type: str = None, start_date: date = None,
                             end_date: date = None) -> list:
        """Get incident reports with filters."""
        return []

    @staticmethod
    def link_insurance_claim(db, report_id: int, claim_number: str,
                             claim_details: dict = None) -> dict:
        """Link an insurance claim to an incident report."""
        return {
            "report_id": report_id,
            "claim_number": claim_number,
        }


class TrainingService:
    """Service for staff training and certification management.

    Note: Methods are called as class methods in the route files.
    """

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def create_training_module(db, venue_id: int, module_name: str, module_type: str,
                               description: str, content: dict, duration_minutes: int,
                               required_roles: list, passing_score: int = 80,
                               certification_valid_days: int = 365) -> dict:
        """Create a training module."""
        return {
            "id": 1,
            "venue_id": venue_id,
            "module_name": module_name,
            "module_type": module_type,
            "duration_minutes": duration_minutes,
            "passing_score": passing_score,
        }

    @staticmethod
    def get_training_modules(db, venue_id: int, module_type: str = None,
                             role: str = None) -> list:
        """Get training modules with filters."""
        return []

    @staticmethod
    def start_training(db, staff_id: int, module_id: int) -> dict:
        """Start a training session for a staff member."""
        return {
            "id": 1,
            "staff_id": staff_id,
            "module_id": module_id,
            "status": "in_progress",
        }

    @staticmethod
    def complete_training(db, record_id: int, score: int) -> dict:
        """Complete a training session with score."""
        return {
            "record_id": record_id,
            "score": score,
            "passed": score >= 80,
            "status": "completed",
        }

    @staticmethod
    def get_staff_training_status(db, staff_id: int, venue_id: int) -> dict:
        """Get training status for a staff member."""
        return {
            "staff_id": staff_id,
            "completed_modules": 0,
            "pending_modules": 0,
            "certifications": [],
        }

    @staticmethod
    def get_expiring_certifications(db, venue_id: int, days_ahead: int = 30) -> list:
        """Get certifications expiring soon."""
        return []


class CrisisManagementService:
    """Service for crisis mode management.

    Note: Methods are called as class methods in the route files.
    """

    def __init__(self, db=None):
        self.db = db

    @staticmethod
    def create_crisis_mode(db, venue_id: int, mode_name: str, mode_type: str,
                           description: str, simplified_menu_ids: list,
                           margin_protection_percentage: Decimal,
                           operational_changes: dict,
                           auto_activation_conditions: dict = None) -> dict:
        """Create a crisis mode configuration."""
        return {
            "id": 1,
            "venue_id": venue_id,
            "mode_name": mode_name,
            "mode_type": mode_type,
            "is_active": False,
        }

    @staticmethod
    def activate_crisis_mode(db, crisis_mode_id: int, activated_by: int,
                             reason: str) -> dict:
        """Activate a crisis mode."""
        return {
            "crisis_mode_id": crisis_mode_id,
            "activated_by": activated_by,
            "is_active": True,
        }

    @staticmethod
    def deactivate_crisis_mode(db, venue_id: int, deactivated_by: int,
                               reason: str) -> dict:
        """Deactivate the current crisis mode."""
        return {
            "venue_id": venue_id,
            "deactivated_by": deactivated_by,
            "is_active": False,
        }

    @staticmethod
    def get_active_crisis_mode(db, venue_id: int) -> Optional[dict]:
        """Get the currently active crisis mode."""
        return None

    @staticmethod
    def get_crisis_modes(db, venue_id: int) -> list:
        """Get all crisis mode configurations."""
        return []

    @staticmethod
    def check_auto_activation(db, venue_id: int, current_conditions: dict) -> Optional[dict]:
        """Check if any crisis mode should be auto-activated."""
        return None
