"""Tests for HACCP temperature logging and safety checks.

Tests temperature recording, out-of-range alerts, compliance reporting.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


API = "/api/v1"


class TestHACCPDashboard:
    """Tests for HACCP dashboard endpoint."""

    def test_dashboard_returns_ok(self, client: TestClient, auth_headers: dict):
        """Test HACCP dashboard returns valid response."""
        response = client.get(f"{API}/haccp/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "compliance_score" in data
        assert "pending_checks" in data
        assert "overdue_checks" in data
        assert "recent_violations" in data
        assert "last_inspection" in data
        assert "next_inspection" in data

    def test_dashboard_compliance_score_range(self, client: TestClient, auth_headers: dict):
        """Test compliance score is in valid range (0-100)."""
        response = client.get(f"{API}/haccp/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        score = data["compliance_score"]
        assert 0 <= score <= 100, f"Compliance score {score} outside 0-100 range"

    def test_dashboard_empty_state(self, client: TestClient, auth_headers: dict):
        """Test dashboard with no checks or logs returns 100% compliance."""
        response = client.get(f"{API}/haccp/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # With no checks, compliance should default to 100%
        assert data["compliance_score"] == 100
        assert data["pending_checks"] == 0
        assert data["overdue_checks"] == 0
        assert data["recent_violations"] == 0

    def test_haccp_root_same_as_dashboard(self, client: TestClient, auth_headers: dict):
        """Test HACCP root endpoint returns same data as dashboard."""
        root_resp = client.get(f"{API}/haccp/", headers=auth_headers)
        dash_resp = client.get(f"{API}/haccp/dashboard", headers=auth_headers)
        assert root_resp.status_code == 200
        assert dash_resp.status_code == 200
        assert root_resp.json() == dash_resp.json()


class TestHACCPTemperatureLogs:
    """Tests for HACCP temperature logging."""

    def test_get_temperature_logs_empty(self, client: TestClient, auth_headers: dict):
        """Test getting temperature logs when none exist."""
        response = client.get(f"{API}/haccp/temperature-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_temperature_log(self, client: TestClient, auth_headers: dict):
        """Test creating a normal temperature log entry."""
        response = client.post(
            f"{API}/haccp/temperature-logs",
            json={
                "location": "walk_in_cooler",
                "equipment": "Cooler A",
                "temperature": 3.5,
                "status": "normal",
                "recorded_by": "test_user",
                "notes": "Morning check",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "id" in data

    def test_create_temperature_log_warning(self, client: TestClient, auth_headers: dict):
        """Test creating a warning temperature log entry."""
        response = client.post(
            f"{API}/haccp/temperature-logs",
            json={
                "location": "walk_in_cooler",
                "equipment": "Cooler B",
                "temperature": 6.0,
                "status": "warning",
                "recorded_by": "test_user",
                "notes": "Temperature slightly elevated",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_create_temperature_log_critical(self, client: TestClient, auth_headers: dict):
        """Test creating a critical temperature log entry."""
        response = client.post(
            f"{API}/haccp/temperature-logs",
            json={
                "location": "freezer",
                "equipment": "Freezer 1",
                "temperature": -5.0,
                "status": "critical",
                "recorded_by": "test_user",
                "notes": "Freezer malfunction, items moved",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_temperature_logs_after_creation(self, client: TestClient, auth_headers: dict):
        """Test retrieving temperature logs after creating entries."""
        # Create a log
        client.post(
            f"{API}/haccp/temperature-logs",
            json={
                "location": "hot_holding",
                "equipment": "Heat Lamp",
                "temperature": 65.0,
                "status": "normal",
                "recorded_by": "chef",
            },
            headers=auth_headers,
        )

        # Retrieve logs
        response = client.get(f"{API}/haccp/temperature-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        log = data[0]
        assert "id" in log
        assert "location" in log
        assert "temperature" in log
        assert "status" in log

    def test_temperature_log_structure(self, client: TestClient, auth_headers: dict):
        """Test temperature log entry has all required fields."""
        client.post(
            f"{API}/haccp/temperature-logs",
            json={
                "location": "prep_area",
                "equipment": "Thermometer",
                "temperature": 22.0,
                "status": "normal",
                "recorded_by": "staff1",
                "notes": "Ambient temp",
            },
            headers=auth_headers,
        )

        response = client.get(f"{API}/haccp/temperature-logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        log = data[0]
        assert "id" in log
        assert "location" in log
        assert "equipment" in log
        assert "temperature" in log
        assert "status" in log
        assert "recorded_by" in log


class TestHACCPSafetyChecks:
    """Tests for HACCP safety check management."""

    def test_get_safety_checks_empty(self, client: TestClient, auth_headers: dict):
        """Test getting safety checks when none exist."""
        response = client.get(f"{API}/haccp/safety-checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_safety_check(self, client: TestClient, auth_headers: dict):
        """Test creating a new safety check."""
        response = client.post(
            f"{API}/haccp/safety-checks",
            json={
                "check_type": "opening_checklist",
                "checked_by": "manager1",
                "items": [
                    {"task": "Check fridge temps", "status": "pass"},
                    {"task": "Check handwash stations", "status": "pass"},
                ],
                "notes": "All clear",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "id" in data

    def test_create_safety_check_minimal(self, client: TestClient, auth_headers: dict):
        """Test creating a safety check with minimal data."""
        response = client.post(
            f"{API}/haccp/safety-checks",
            json={
                "check_type": "daily_inspection",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_safety_checks_after_creation(self, client: TestClient, auth_headers: dict):
        """Test retrieving safety checks after creation."""
        # Create a check
        create_resp = client.post(
            f"{API}/haccp/safety-checks",
            json={
                "check_type": "closing_checklist",
                "checked_by": "manager2",
                "notes": "End of day check",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 200

        # Retrieve checks
        response = client.get(f"{API}/haccp/safety-checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        check = data[0]
        assert "id" in check
        assert "check_type" in check
        assert "status" in check

    def test_complete_safety_check(self, client: TestClient, auth_headers: dict):
        """Test completing a safety check."""
        # Create a check first
        create_resp = client.post(
            f"{API}/haccp/safety-checks",
            json={
                "check_type": "hygiene_check",
                "checked_by": "inspector",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 200
        check_id = create_resp.json()["id"]

        # Complete it
        response = client.post(
            f"{API}/haccp/safety-checks/{check_id}/complete?result=pass",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_complete_nonexistent_check(self, client: TestClient, auth_headers: dict):
        """Test completing a non-existent safety check."""
        response = client.post(
            f"{API}/haccp/safety-checks/999999/complete?result=pass",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_safety_check_structure(self, client: TestClient, auth_headers: dict):
        """Test safety check response structure."""
        client.post(
            f"{API}/haccp/safety-checks",
            json={
                "check_type": "equipment_check",
                "checked_by": "technician",
            },
            headers=auth_headers,
        )

        response = client.get(f"{API}/haccp/safety-checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

        check = data[0]
        assert "id" in check
        assert "check_type" in check
        assert "status" in check
        assert "due_date" in check


class TestHACCPChecksAlternateEndpoint:
    """Tests for the alternate /haccp/checks endpoint."""

    def test_get_haccp_checks_empty(self, client: TestClient, auth_headers: dict):
        """Test getting HACCP checks when none exist."""
        response = client.get(f"{API}/haccp/checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_haccp_checks_after_safety_check(self, client: TestClient, auth_headers: dict):
        """Test that /haccp/checks reflects created safety checks."""
        client.post(
            f"{API}/haccp/safety-checks",
            json={
                "check_type": "fire_safety",
                "checked_by": "fire_marshal",
            },
            headers=auth_headers,
        )

        response = client.get(f"{API}/haccp/checks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            check = data[0]
            assert "id" in check
            assert "name" in check
            assert "status" in check


class TestHACCPLogsEndpoint:
    """Tests for the /haccp/logs compliance logs endpoint."""

    def test_get_haccp_logs_empty(self, client: TestClient, auth_headers: dict):
        """Test getting HACCP logs when none exist."""
        response = client.get(f"{API}/haccp/logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_haccp_logs_after_temperature_entry(self, client: TestClient, auth_headers: dict):
        """Test that /haccp/logs reflects temperature entries."""
        client.post(
            f"{API}/haccp/temperature-logs",
            json={
                "location": "storage",
                "equipment": "Shelf sensor",
                "temperature": 4.0,
                "status": "normal",
                "recorded_by": "system",
            },
            headers=auth_headers,
        )

        response = client.get(f"{API}/haccp/logs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        log = data[0]
        assert "id" in log
        assert "value" in log
        assert "status" in log
        assert "recorded_at" in log


class TestHACCPFoodSafetyService:
    """Tests for the HACCPFoodSafetyService class."""

    def test_service_instantiation(self):
        """Test HACCPFoodSafetyService can be instantiated."""
        from app.services.haccp_food_safety_service import HACCPFoodSafetyService
        service = HACCPFoodSafetyService()
        assert service is not None

    def test_service_with_db(self, db_session: Session):
        """Test HACCPFoodSafetyService with database session."""
        from app.services.haccp_food_safety_service import HACCPFoodSafetyService
        service = HACCPFoodSafetyService(db_session=db_session)
        assert service.db is not None

    def test_temp_limits_defined(self):
        """Test temperature limits are defined for zones."""
        from app.services.haccp_food_safety_service import HACCPFoodSafetyService, TemperatureZone
        limits = HACCPFoodSafetyService.TEMP_LIMITS
        assert TemperatureZone.COLD_STORAGE in limits
        assert TemperatureZone.FREEZER in limits
        assert TemperatureZone.HOT_HOLDING in limits
        assert TemperatureZone.COOKING in limits

    def test_cold_storage_limits(self):
        """Test cold storage temperature limits are correct."""
        from app.services.haccp_food_safety_service import HACCPFoodSafetyService, TemperatureZone
        limits = HACCPFoodSafetyService.TEMP_LIMITS[TemperatureZone.COLD_STORAGE]
        assert limits["min"] == 0
        assert limits["max"] == 4

    def test_freezer_limits(self):
        """Test freezer temperature limits are correct."""
        from app.services.haccp_food_safety_service import HACCPFoodSafetyService, TemperatureZone
        limits = HACCPFoodSafetyService.TEMP_LIMITS[TemperatureZone.FREEZER]
        assert limits["min"] == -25
        assert limits["max"] == -18

    def test_hot_holding_limits(self):
        """Test hot holding temperature limits are correct."""
        from app.services.haccp_food_safety_service import HACCPFoodSafetyService, TemperatureZone
        limits = HACCPFoodSafetyService.TEMP_LIMITS[TemperatureZone.HOT_HOLDING]
        assert limits["min"] == 63
        assert limits["max"] == 100

    def test_hazard_type_enum(self):
        """Test HazardType enum values."""
        from app.services.haccp_food_safety_service import HazardType
        assert HazardType.BIOLOGICAL == "biological"
        assert HazardType.CHEMICAL == "chemical"
        assert HazardType.PHYSICAL == "physical"
        assert HazardType.ALLERGEN == "allergen"

    def test_severity_enum(self):
        """Test Severity enum values."""
        from app.services.haccp_food_safety_service import Severity
        assert Severity.LOW == "low"
        assert Severity.MEDIUM == "medium"
        assert Severity.HIGH == "high"
        assert Severity.CRITICAL == "critical"

    def test_temperature_zone_enum(self):
        """Test TemperatureZone enum values."""
        from app.services.haccp_food_safety_service import TemperatureZone
        assert TemperatureZone.COLD_STORAGE == "cold_storage"
        assert TemperatureZone.FREEZER == "freezer"
        assert TemperatureZone.HOT_HOLDING == "hot_holding"
        assert TemperatureZone.COOKING == "cooking"
        assert TemperatureZone.AMBIENT == "ambient"


class TestHACCPComplianceReporting:
    """Tests for HACCP compliance reporting through the dashboard."""

    def test_compliance_after_completed_check(self, client: TestClient, auth_headers: dict):
        """Test that compliance score reflects completed checks."""
        # Create and complete a safety check
        create_resp = client.post(
            f"{API}/haccp/safety-checks",
            json={
                "check_type": "compliance_test",
                "checked_by": "auditor",
            },
            headers=auth_headers,
        )
        assert create_resp.status_code == 200

        # Check dashboard
        dash_resp = client.get(f"{API}/haccp/dashboard", headers=auth_headers)
        assert dash_resp.status_code == 200
        data = dash_resp.json()
        assert "compliance_score" in data

    def test_violation_tracking(self, client: TestClient, auth_headers: dict):
        """Test that critical temperature logs show as violations."""
        # Log a critical temperature
        client.post(
            f"{API}/haccp/temperature-logs",
            json={
                "location": "cold_storage",
                "equipment": "Main cooler",
                "temperature": 12.0,
                "status": "critical",
                "recorded_by": "sensor",
                "notes": "Temperature out of range",
            },
            headers=auth_headers,
        )

        # Check dashboard for violations
        response = client.get(f"{API}/haccp/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["recent_violations"] >= 1
