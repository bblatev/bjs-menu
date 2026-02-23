"""Tests for delivery aggregator service.

Tests get_all_integrations with empty state, test unified_orders endpoint,
test platform badge mapping.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


API = "/api/v1"


class TestDeliveryAggregatorService:
    """Tests for DeliveryAggregatorService."""

    def test_service_instantiation(self, db_session: Session):
        """Test that DeliveryAggregatorService can be instantiated."""
        from app.services.delivery_aggregator_service import DeliveryAggregatorService
        service = DeliveryAggregatorService(db_session)
        assert service is not None

    def test_get_all_integrations_empty(self, db_session: Session):
        """Test get_all_integrations returns empty list with no integrations."""
        from app.services.delivery_service import DeliveryAggregatorService
        service = DeliveryAggregatorService(db_session)
        integrations = service.get_all_integrations()
        assert isinstance(integrations, list)
        assert len(integrations) == 0

    def test_platform_enum_values(self):
        """Test DeliveryPlatform enum has expected values."""
        from app.services.delivery_aggregator_service import DeliveryPlatform
        assert DeliveryPlatform.GLOVO == "glovo"
        assert DeliveryPlatform.UBER_EATS == "uber_eats"
        assert DeliveryPlatform.WOLT == "wolt"
        assert DeliveryPlatform.BOLT_FOOD == "bolt_food"
        assert DeliveryPlatform.FOODPANDA == "foodpanda"
        assert DeliveryPlatform.TAKEAWAY == "takeaway"
        assert DeliveryPlatform.OWN_FLEET == "own_fleet"

    def test_order_status_enum(self):
        """Test AggregatorOrderStatus enum values."""
        from app.services.delivery_aggregator_service import AggregatorOrderStatus
        assert AggregatorOrderStatus.PENDING == "pending"
        assert AggregatorOrderStatus.ACCEPTED == "accepted"
        assert AggregatorOrderStatus.PREPARING == "preparing"
        assert AggregatorOrderStatus.DELIVERED == "delivered"
        assert AggregatorOrderStatus.CANCELLED == "cancelled"

    def test_driver_status_enum(self):
        """Test DriverStatus enum values."""
        from app.services.delivery_aggregator_service import DriverStatus
        assert DriverStatus.OFFLINE == "offline"
        assert DriverStatus.AVAILABLE == "available"
        assert DriverStatus.DELIVERING == "delivering"

    def test_platform_endpoints_configured(self):
        """Test that platform endpoints are configured for all platforms."""
        from app.services.delivery_aggregator_service import DeliveryAggregatorService, DeliveryPlatform
        endpoints = DeliveryAggregatorService.PLATFORM_ENDPOINTS
        assert DeliveryPlatform.GLOVO in endpoints
        assert DeliveryPlatform.UBER_EATS in endpoints
        assert DeliveryPlatform.WOLT in endpoints
        for platform, config in endpoints.items():
            assert "base_url" in config
            assert "orders" in config


class TestDeliveryRoutes:
    """Tests for delivery API routes."""

    def test_delivery_root_returns_status(self, client: TestClient, auth_headers: dict):
        """Test delivery root endpoint returns status overview."""
        response = client.get(f"{API}/delivery/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "total_integrations" in data
        assert "active_integrations" in data
        assert "platforms" in data
        assert isinstance(data["platforms"], list)

    def test_delivery_root_inactive_with_no_integrations(self, client: TestClient, auth_headers: dict):
        """Test delivery root shows inactive when no integrations configured."""
        response = client.get(f"{API}/delivery/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"
        assert data["total_integrations"] == 0
        assert data["active_integrations"] == 0

    def test_delivery_integrations_list_empty(self, client: TestClient, auth_headers: dict):
        """Test listing integrations returns empty list when none configured."""
        response = client.get(f"{API}/delivery/integrations/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_delivery_orders_list_empty(self, client: TestClient, auth_headers: dict):
        """Test listing orders returns empty list when none exist."""
        response = client.get(f"{API}/delivery/orders/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_unified_orders_endpoint(self, client: TestClient, auth_headers: dict):
        """Test unified orders endpoint returns valid response."""
        response = client.get(f"{API}/delivery/unified-orders", headers=auth_headers)
        assert response.status_code != 500
        # Should return a list or similar structure
        data = response.json()
        assert data is not None

    def test_platform_badge_mapping(self):
        """Test platform badge mapping: each platform has a known string identifier."""
        from app.services.delivery_aggregator_service import DeliveryPlatform
        platform_badges = {
            DeliveryPlatform.GLOVO: "glovo",
            DeliveryPlatform.UBER_EATS: "uber_eats",
            DeliveryPlatform.WOLT: "wolt",
            DeliveryPlatform.BOLT_FOOD: "bolt_food",
            DeliveryPlatform.FOODPANDA: "foodpanda",
            DeliveryPlatform.TAKEAWAY: "takeaway",
        }
        for platform, badge in platform_badges.items():
            assert platform.value == badge

    def test_delivery_profitability_endpoint(self, client: TestClient):
        """Test delivery profitability endpoint."""
        response = client.get(f"{API}/delivery/profitability")
        assert response.status_code != 500

    def test_delivery_virtual_brands_endpoint(self, client: TestClient):
        """Test virtual brands listing endpoint."""
        response = client.get(f"{API}/delivery/virtual-brands")
        assert response.status_code != 500

    def test_delivery_dynamic_radius_endpoint(self, client: TestClient):
        """Test dynamic delivery radius endpoint."""
        response = client.get(f"{API}/delivery/dynamic-radius")
        assert response.status_code != 500

    def test_delivery_availability_endpoint(self, client: TestClient):
        """Test item availability listing endpoint."""
        response = client.get(f"{API}/delivery/availability/")
        assert response.status_code != 500
