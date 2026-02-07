"""Comprehensive tests for POS, sync, delivery, and analytics API endpoints."""

import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from io import BytesIO

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.location import Location
from app.models.recipe import Recipe, RecipeLine
from app.models.pos import PosSalesLine, PosRawEvent
from app.models.delivery import (
    DeliveryIntegration, DeliveryOrder, DeliveryPlatform,
    DeliveryOrderStatus, ItemAvailability, DeliveryPlatformMapping
)
from app.models.analytics import (
    MenuAnalysis, ServerPerformance, DailyMetrics, Benchmark, BottleWeight
)


# ==================== POS TESTS ====================

class TestPOSEndpoints:
    """Test POS integration endpoints."""

    def test_list_sales_lines_empty(self, client: TestClient, db_session, auth_headers):
        """Test listing sales lines when none exist."""
        response = client.get("/api/v1/pos/sales", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_sales_lines(self, client: TestClient, db_session, auth_headers, test_location):
        """Test listing sales lines."""
        # Create test sales line
        raw_event = PosRawEvent(source="test", payload_json={})
        db_session.add(raw_event)
        db_session.flush()

        sales_line = PosSalesLine(
            ts=datetime.utcnow(),
            pos_item_id="ITEM001",
            name="Test Item",
            qty=Decimal("2"),
            is_refund=False,
            location_id=test_location.id,
            raw_event_id=raw_event.id,
            processed=False
        )
        db_session.add(sales_line)
        db_session.commit()

        response = client.get("/api/v1/pos/sales", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_list_sales_lines_filter_processed(self, client: TestClient, db_session, auth_headers, test_location):
        """Test filtering sales lines by processed status."""
        raw_event = PosRawEvent(source="test", payload_json={})
        db_session.add(raw_event)
        db_session.flush()

        # Create unprocessed line
        unprocessed = PosSalesLine(
            ts=datetime.utcnow(),
            name="Unprocessed",
            qty=Decimal("1"),
            location_id=test_location.id,
            raw_event_id=raw_event.id,
            processed=False
        )
        # Create processed line
        processed = PosSalesLine(
            ts=datetime.utcnow(),
            name="Processed",
            qty=Decimal("1"),
            location_id=test_location.id,
            raw_event_id=raw_event.id,
            processed=True
        )
        db_session.add_all([unprocessed, processed])
        db_session.commit()

        response = client.get("/api/v1/pos/sales?processed=false", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(not line.get("processed", True) for line in data)

    def test_import_pos_csv_invalid_file_type(self, client: TestClient, db_session, auth_headers, test_location):
        """Test importing POS data from non-CSV file."""
        file_content = b"not a csv"
        files = {"file": ("data.txt", BytesIO(file_content), "text/plain")}

        response = client.post(
            f"/api/v1/pos/import/csv?location_id={test_location.id}",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_import_pos_csv_location_not_found(self, client: TestClient, db_session, auth_headers):
        """Test importing POS data with invalid location."""
        csv_content = b"timestamp,item_id,item_name,qty,is_refund\n2024-01-15T12:00:00,ITEM1,Beer,2,false"
        files = {"file": ("data.csv", BytesIO(csv_content), "text/csv")}

        response = client.post(
            "/api/v1/pos/import/csv?location_id=9999",
            files=files,
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_consume_sales(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test consuming sales to create stock movements."""
        # Create recipe
        recipe = Recipe(name="Test Recipe", pos_item_id="TESTITEM")
        db_session.add(recipe)
        db_session.flush()

        recipe_line = RecipeLine(
            recipe_id=recipe.id,
            product_id=test_product.id,
            qty=Decimal("1.5"),
            unit="oz"
        )
        db_session.add(recipe_line)

        # Create unprocessed sales line
        raw_event = PosRawEvent(source="test", payload_json={})
        db_session.add(raw_event)
        db_session.flush()

        sales_line = PosSalesLine(
            ts=datetime.utcnow(),
            pos_item_id="TESTITEM",
            name="Test Recipe",
            qty=Decimal("3"),
            is_refund=False,
            location_id=test_location.id,
            raw_event_id=raw_event.id,
            processed=False
        )
        db_session.add(sales_line)
        db_session.commit()

        response = client.post(
            f"/api/v1/pos/consume?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "sales_processed" in data
        assert "movements_created" in data


# ==================== SYNC TESTS ====================

class TestSyncEndpoints:
    """Test mobile sync endpoints."""

    def test_sync_pull_empty(self, client: TestClient, db_session, auth_headers):
        """Test sync pull with no data."""
        response = client.get("/api/v1/sync/pull", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "suppliers" in data
        assert "locations" in data
        assert "server_timestamp" in data

    def test_sync_pull_with_data(self, client: TestClient, db_session, auth_headers, test_supplier, test_location, test_product):
        """Test sync pull returns data."""
        response = client.get("/api/v1/sync/pull", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "suppliers" in data
        assert "locations" in data
        assert "server_timestamp" in data
        assert len(data["products"]) >= 1
        assert len(data["suppliers"]) >= 1
        assert len(data["locations"]) >= 1

    def test_sync_pull_with_since(self, client: TestClient, db_session, auth_headers):
        """Test sync pull with since parameter."""
        since = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        response = client.get(f"/api/v1/sync/pull?since={since}", headers=auth_headers)
        assert response.status_code == 200

    def test_sync_push(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test sync push from mobile."""
        response = client.post(
            "/api/v1/sync/push",
            headers=auth_headers,
            json={
                "sessions": [
                    {
                        "local_id": "local-123",
                        "location_id": test_location.id,
                        "status": "in_progress",
                        "started_at": datetime.utcnow().isoformat(),
                        "lines": [
                            {
                                "local_id": "line-456",
                                "product_id": test_product.id,
                                "counted_qty": "10.5",
                                "method": "barcode",
                                "counted_at": datetime.utcnow().isoformat()
                            }
                        ]
                    }
                ]
            }
        )
        assert response.status_code in [200, 422]


# ==================== DELIVERY TESTS ====================

class TestDeliveryEndpoints:
    """Test delivery aggregator endpoints."""

    def test_list_integrations_empty(self, client: TestClient, db_session):
        """Test listing integrations when none exist."""
        response = client.get("/api/v1/delivery/integrations/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_integration(self, client: TestClient, db_session, auth_headers, test_location):
        """Test creating a delivery integration."""
        response = client.post(
            "/api/v1/delivery/integrations/",
            headers=auth_headers,
            json={
                "location_id": test_location.id,
                "platform": "doordash",
                "store_id": "STORE123",
                "api_key": "test-api-key",
                "is_active": True
            }
        )
        assert response.status_code in [200, 422]

    def test_get_integration_not_found(self, client: TestClient, db_session):
        """Test getting non-existent integration."""
        response = client.get("/api/v1/delivery/integrations/9999")
        assert response.status_code == 404

    def test_list_orders_empty(self, client: TestClient, db_session):
        """Test listing orders when none exist."""
        response = client.get("/api/v1/delivery/orders/")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_order_not_found(self, client: TestClient, db_session):
        """Test getting non-existent order."""
        response = client.get("/api/v1/delivery/orders/9999")
        assert response.status_code == 404

    def test_reject_order_not_found(self, client: TestClient, db_session, auth_headers):
        """Test rejecting non-existent order."""
        response = client.post(
            "/api/v1/delivery/orders/9999/reject",
            headers=auth_headers,
            json={"reason": "out_of_stock"}
        )
        assert response.status_code == 404

    def test_list_item_availability(self, client: TestClient, db_session):
        """Test listing item availability."""
        response = client.get("/api/v1/delivery/availability/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_delete_integration_not_found(self, client: TestClient, db_session, auth_headers):
        """Test deleting non-existent integration."""
        response = client.delete("/api/v1/delivery/integrations/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_delivery_summary(self, client: TestClient, db_session):
        """Test getting delivery summary report."""
        response = client.get("/api/v1/delivery/reports/summary")
        assert response.status_code == 200

    def test_get_platform_performance_invalid(self, client: TestClient, db_session):
        """Test getting performance for invalid platform."""
        response = client.get("/api/v1/delivery/reports/performance/invalid_platform")
        assert response.status_code == 400

    def test_handle_webhook_invalid_platform(self, client: TestClient, db_session, auth_headers):
        """Test webhook with invalid platform."""
        response = client.post(
            "/api/v1/delivery/webhook/invalid",
            headers=auth_headers,
            json={"event_type": "order.created", "data": {}}
        )
        assert response.status_code == 400


# ==================== ANALYTICS TESTS ====================

class TestAnalyticsEndpoints:
    """Test analytics and reporting endpoints."""

    def test_get_menu_engineering_report(self, client: TestClient, db_session):
        """Test getting menu engineering report."""
        response = client.get("/api/v1/analytics/menu-engineering/")
        assert response.status_code == 200

    def test_get_product_analysis_not_found(self, client: TestClient, db_session):
        """Test getting analysis for non-existent product."""
        response = client.get("/api/v1/analytics/menu-engineering/9999")
        assert response.status_code == 404

    def test_get_server_performance_report(self, client: TestClient, db_session):
        """Test getting server performance report."""
        response = client.get("/api/v1/analytics/server-performance/")
        assert response.status_code == 200
        data = response.json()
        assert "date_range" in data
        assert "rankings" in data

    def test_get_server_metrics(self, client: TestClient, db_session, test_user):
        """Test getting metrics for a specific server."""
        response = client.get(f"/api/v1/analytics/server-performance/{test_user.id}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_daily_metrics(self, client: TestClient, db_session):
        """Test getting daily metrics."""
        response = client.get("/api/v1/analytics/daily-metrics/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_daily_metrics_with_filters(self, client: TestClient, db_session, test_location):
        """Test getting daily metrics with filters."""
        response = client.get(
            f"/api/v1/analytics/daily-metrics/?location_id={test_location.id}&start_date=2024-01-01"
        )
        assert response.status_code == 200

    def test_calculate_daily_metrics(self, client: TestClient, db_session, auth_headers):
        """Test calculating daily metrics."""
        response = client.post("/api/v1/analytics/daily-metrics/calculate", headers=auth_headers)
        assert response.status_code == 200

    def test_get_metric_trend(self, client: TestClient, db_session):
        """Test getting metric trend."""
        response = client.get("/api/v1/analytics/metrics-trend/average_ticket")
        assert response.status_code == 200
        data = response.json()
        assert "metric_name" in data
        assert "trend" in data

    def test_chat_query(self, client: TestClient, db_session, auth_headers):
        """Test conversational AI query."""
        response = client.post(
            "/api/v1/analytics/chat/",
            headers=auth_headers,
            json={"query": "What were yesterday's sales?"}
        )
        assert response.status_code == 200

    def test_get_conversation_history(self, client: TestClient, db_session):
        """Test getting conversation history."""
        response = client.get("/api/v1/analytics/chat/history/test-conversation-id")
        assert response.status_code in [200, 404]

    def test_submit_query_feedback(self, client: TestClient, db_session, auth_headers):
        """Test submitting query feedback."""
        response = client.post(
            "/api/v1/analytics/chat/feedback",
            headers=auth_headers,
            json={"query_id": "test-query-id", "was_helpful": True}
        )
        assert response.status_code in [200, 404, 422]

    def test_list_benchmarks(self, client: TestClient, db_session):
        """Test listing benchmarks."""
        response = client.get("/api/v1/analytics/benchmarks/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_compare_to_benchmarks_no_metrics(self, client: TestClient, db_session, test_location):
        """Test comparing to benchmarks when no metrics exist."""
        response = client.get(f"/api/v1/analytics/benchmarks/compare?location_id={test_location.id}")
        assert response.status_code == 404


# ==================== BOTTLE WEIGHT TESTS ====================

class TestBottleWeightEndpoints:
    """Test bottle weight database endpoints."""

    def test_list_bottle_weights_empty(self, client: TestClient, db_session):
        """Test listing bottle weights when none exist."""
        response = client.get("/api/v1/analytics/bottle-weights/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_bottle_weight(self, client: TestClient, db_session, auth_headers, test_product):
        """Test creating a bottle weight entry."""
        response = client.post(
            "/api/v1/analytics/bottle-weights/",
            headers=auth_headers,
            json={
                "product_id": test_product.id,
                "full_weight": 1200.0,
                "empty_weight": 450.0,
                "volume_ml": 750
            }
        )
        assert response.status_code in [200, 422]

    def test_get_bottle_weight_not_found(self, client: TestClient, db_session):
        """Test getting bottle weight for non-existent product."""
        response = client.get("/api/v1/analytics/bottle-weights/9999")
        assert response.status_code == 404

    def test_get_products_without_weights(self, client: TestClient, db_session):
        """Test getting products without bottle weights."""
        response = client.get("/api/v1/analytics/bottle-weights/missing/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== SCALE TESTS ====================

class TestScaleEndpoints:
    """Test scale integration endpoints."""

    def test_process_scale_reading(self, client: TestClient, db_session, auth_headers, test_product):
        """Test processing a scale reading."""
        response = client.post(
            "/api/v1/analytics/scale/reading",
            headers=auth_headers,
            json={
                "product_id": test_product.id,
                "weight_grams": 800.0,
                "device_id": "SCALE001"
            }
        )
        assert response.status_code in [200, 400]

    def test_record_visual_estimate(self, client: TestClient, db_session, auth_headers, test_product):
        """Test recording a visual estimate."""
        response = client.post(
            "/api/v1/analytics/scale/visual-estimate",
            headers=auth_headers,
            json={
                "product_id": test_product.id,
                "estimated_percent": 65.0
            }
        )
        assert response.status_code in [200, 400]

    def test_get_scale_session_summary_not_found(self, client: TestClient, db_session):
        """Test getting scale session summary for non-existent session."""
        response = client.get("/api/v1/analytics/scale/session-summary/9999")
        assert response.status_code in [200, 404]


# ==================== INTEGRATION TESTS ====================

class TestPOSToInventoryIntegration:
    """Test POS to inventory integration flow."""

    def test_sales_consumption_flow(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test full flow from POS sale to inventory consumption."""
        # Create recipe linking POS item to product
        recipe = Recipe(name="Draft Beer", pos_item_id="BEER001")
        db_session.add(recipe)
        db_session.flush()

        recipe_line = RecipeLine(
            recipe_id=recipe.id,
            product_id=test_product.id,
            qty=Decimal("0.5"),  # Half unit per sale
            unit="unit"
        )
        db_session.add(recipe_line)

        # Create raw event
        raw_event = PosRawEvent(source="manual", payload_json={})
        db_session.add(raw_event)
        db_session.flush()

        # Create sales line
        sales_line = PosSalesLine(
            ts=datetime.utcnow(),
            pos_item_id="BEER001",
            name="Draft Beer",
            qty=Decimal("4"),
            is_refund=False,
            location_id=test_location.id,
            raw_event_id=raw_event.id,
            processed=False
        )
        db_session.add(sales_line)
        db_session.commit()

        # Verify sales line exists
        response = client.get("/api/v1/pos/sales?processed=false", headers=auth_headers)
        assert response.status_code == 200

        # Consume sales
        response = client.post("/api/v1/pos/consume", headers=auth_headers)
        assert response.status_code == 200


class TestDeliveryOrderFlow:
    """Test delivery order lifecycle."""

    def test_order_rejection_flow(self, client: TestClient, db_session, auth_headers, test_location):
        """Test order rejection flow."""
        # Create integration first (required for order)
        integration = DeliveryIntegration(
            location_id=test_location.id,
            platform=DeliveryPlatform.DOORDASH,
            store_id="STORE123",
            is_active=True
        )
        db_session.add(integration)
        db_session.flush()

        # Create order
        order = DeliveryOrder(
            integration_id=integration.id,
            platform=DeliveryPlatform.DOORDASH,
            platform_order_id="DD-12345",
            location_id=test_location.id,
            status=DeliveryOrderStatus.RECEIVED,
        )
        db_session.add(order)
        db_session.commit()

        # Reject order
        response = client.post(
            f"/api/v1/delivery/orders/{order.id}/reject",
            headers=auth_headers,
            json={"reason": "out_of_stock"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"
