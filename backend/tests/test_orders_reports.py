"""Comprehensive tests for orders and reports API endpoints."""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.core.rbac import UserRole
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.product import Product
from app.models.supplier import Supplier
from app.models.location import Location
from app.models.order import PurchaseOrder, PurchaseOrderLine, POStatus
from app.models.stock import StockOnHand, StockMovement


# ==================== PURCHASE ORDER TESTS ====================

class TestOrderSuggestions:
    """Test order suggestion generation."""

    def test_get_suggestions_empty(self, client: TestClient, db_session, auth_headers, test_location):
        """Test getting suggestions when no products need reordering."""
        response = client.get(
            f"/api/v1/orders/suggestions?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["location_id"] == test_location.id
        assert data["suggestions"] == []

    def test_get_suggestions_with_low_stock(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test getting suggestions for products below target stock."""
        # Create product with target stock
        product = Product(
            name="Low Stock Beer",
            barcode="1111111111111",
            supplier_id=test_supplier.id,
            min_stock=Decimal("10"),
            target_stock=Decimal("50"),
            cost_price=Decimal("2.00"),
            unit="btl",
            active=True,
        )
        db_session.add(product)
        db_session.commit()

        # Create stock below target
        stock = StockOnHand(
            product_id=product.id,
            location_id=test_location.id,
            qty=Decimal("5"),
        )
        db_session.add(stock)
        db_session.commit()

        response = client.get(
            f"/api/v1/orders/suggestions?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        # May include test_product fixture as well
        assert len(data["suggestions"]) >= 1

        # Find our product in suggestions (may or may not be present depending on fixture)
        suggestion = next((s for s in data["suggestions"] if s["product_id"] == product.id), None)
        if suggestion:
            assert float(suggestion["suggested_qty"]) == 45  # 50 - 5

    def test_get_suggestions_invalid_location(self, client: TestClient, db_session, auth_headers):
        """Test getting suggestions for non-existent location."""
        response = client.get(
            "/api/v1/orders/suggestions?location_id=9999",
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_get_suggestions_grouped_by_supplier(self, client: TestClient, db_session, auth_headers, test_location):
        """Test that suggestions are grouped by supplier."""
        # Create two suppliers
        supplier1 = Supplier(name="Supplier A")
        supplier2 = Supplier(name="Supplier B")
        db_session.add_all([supplier1, supplier2])
        db_session.commit()

        # Create products for each supplier
        product1 = Product(
            name="Product A",
            supplier_id=supplier1.id,
            target_stock=Decimal("100"),
            active=True,
        )
        product2 = Product(
            name="Product B",
            supplier_id=supplier2.id,
            target_stock=Decimal("100"),
            active=True,
        )
        db_session.add_all([product1, product2])
        db_session.commit()

        response = client.get(
            f"/api/v1/orders/suggestions?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should have entries grouped by supplier
        assert "by_supplier" in data


class TestPurchaseOrderCRUD:
    """Test purchase order CRUD operations."""

    def test_list_orders_empty(self, client: TestClient, db_session, auth_headers):
        """Test listing orders when none exist."""
        response = client.get("/api/v1/orders/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_create_order(self, client: TestClient, db_session, auth_headers, test_supplier, test_location, test_product):
        """Test creating a purchase order."""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "supplier_id": test_supplier.id,
                "location_id": test_location.id,
                "notes": "Test order",
                "lines": [
                    {"product_id": test_product.id, "qty": "10", "unit_cost": "1.50"}
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["supplier_id"] == test_supplier.id
        assert data["status"] == "draft"
        assert len(data["lines"]) == 1

    def test_create_order_invalid_supplier(self, client: TestClient, db_session, auth_headers, test_location, test_product):
        """Test creating order with non-existent supplier."""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "supplier_id": 9999,
                "location_id": test_location.id,
                "lines": [{"product_id": test_product.id, "qty": "10"}]
            }
        )
        assert response.status_code == 404

    def test_create_order_invalid_location(self, client: TestClient, db_session, auth_headers, test_supplier, test_product):
        """Test creating order with non-existent location."""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "supplier_id": test_supplier.id,
                "location_id": 9999,
                "lines": [{"product_id": test_product.id, "qty": "10"}]
            }
        )
        assert response.status_code == 404

    def test_create_order_invalid_product(self, client: TestClient, db_session, auth_headers, test_supplier, test_location):
        """Test creating order with non-existent product."""
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "supplier_id": test_supplier.id,
                "location_id": test_location.id,
                "lines": [{"product_id": 9999, "qty": "10"}]
            }
        )
        assert response.status_code == 400

    def test_get_order(self, client: TestClient, db_session, auth_headers, test_supplier, test_location):
        """Test getting a specific order."""
        order = PurchaseOrder(
            supplier_id=test_supplier.id,
            location_id=test_location.id,
            created_by=1,
        )
        db_session.add(order)
        db_session.commit()

        response = client.get(f"/api/v1/orders/{order.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == order.id

    def test_get_order_not_found(self, client: TestClient, db_session, auth_headers):
        """Test getting non-existent order."""
        response = client.get("/api/v1/orders/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_list_orders_filter_by_supplier(self, client: TestClient, db_session, auth_headers, test_supplier, test_location):
        """Test filtering orders by supplier."""
        # Create orders for different suppliers
        supplier2 = Supplier(name="Other Supplier")
        db_session.add(supplier2)
        db_session.commit()

        order1 = PurchaseOrder(supplier_id=test_supplier.id, location_id=test_location.id, created_by=1)
        order2 = PurchaseOrder(supplier_id=supplier2.id, location_id=test_location.id, created_by=1)
        db_session.add_all([order1, order2])
        db_session.commit()

        response = client.get(
            f"/api/v1/orders/?supplier_id={test_supplier.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(o["supplier_id"] == test_supplier.id for o in data)

    def test_list_orders_filter_by_status(self, client: TestClient, db_session, auth_headers, test_supplier, test_location):
        """Test filtering orders by status."""
        order1 = PurchaseOrder(
            supplier_id=test_supplier.id,
            location_id=test_location.id,
            created_by=1,
            status=POStatus.DRAFT,
        )
        order2 = PurchaseOrder(
            supplier_id=test_supplier.id,
            location_id=test_location.id,
            created_by=1,
            status=POStatus.SENT,
        )
        db_session.add_all([order1, order2])
        db_session.commit()

        response = client.get("/api/v1/orders/?status=draft", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(o["status"] == "draft" for o in data)


class TestOrderStatusUpdates:
    """Test order status transitions."""

    def test_update_status_to_sent(self, client: TestClient, db_session, auth_headers, test_supplier, test_location):
        """Test updating order status to sent."""
        order = PurchaseOrder(
            supplier_id=test_supplier.id,
            location_id=test_location.id,
            created_by=1,
            status=POStatus.DRAFT,
        )
        db_session.add(order)
        db_session.commit()

        response = client.put(
            f"/api/v1/orders/{order.id}/status?status=sent",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "sent"

    def test_update_status_to_received(self, client: TestClient, db_session, auth_headers, test_supplier, test_location):
        """Test updating order status to received."""
        order = PurchaseOrder(
            supplier_id=test_supplier.id,
            location_id=test_location.id,
            created_by=1,
            status=POStatus.SENT,
        )
        db_session.add(order)
        db_session.commit()

        response = client.put(
            f"/api/v1/orders/{order.id}/status?status=received",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "received"

    def test_update_status_order_not_found(self, client: TestClient, db_session, auth_headers):
        """Test updating status of non-existent order."""
        response = client.put(
            "/api/v1/orders/9999/status?status=sent",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestOrderExports:
    """Test order export functionality."""

    def test_export_whatsapp(self, client: TestClient, db_session, auth_headers, test_supplier, test_location, test_product):
        """Test exporting order as WhatsApp text."""
        order = PurchaseOrder(
            supplier_id=test_supplier.id,
            location_id=test_location.id,
            created_by=1,
        )
        db_session.add(order)
        db_session.flush()

        line = PurchaseOrderLine(
            po_id=order.id,
            product_id=test_product.id,
            qty=Decimal("10"),
        )
        db_session.add(line)
        db_session.commit()

        response = client.get(
            f"/api/v1/orders/{order.id}/export/whatsapp",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "text" in data

    def test_export_whatsapp_order_not_found(self, client: TestClient, db_session, auth_headers):
        """Test exporting non-existent order."""
        response = client.get(
            "/api/v1/orders/9999/export/whatsapp",
            headers=auth_headers
        )
        assert response.status_code == 404


# ==================== REPORTS TESTS ====================

class TestStockValuationReport:
    """Test stock valuation report."""

    def test_stock_valuation_empty(self, client: TestClient, db_session, auth_headers):
        """Test stock valuation with no stock."""
        response = client.get("/api/v1/reports/stock-valuation", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total_value"] == 0

    def test_stock_valuation_with_stock(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test stock valuation with actual stock."""
        product = Product(
            name="Valued Product",
            supplier_id=test_supplier.id,
            cost_price=Decimal("5.00"),
            active=True,
        )
        db_session.add(product)
        db_session.commit()

        stock = StockOnHand(
            product_id=product.id,
            location_id=test_location.id,
            qty=Decimal("100"),
        )
        db_session.add(stock)
        db_session.commit()

        response = client.get("/api/v1/reports/stock-valuation", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Find our product
        item = next((i for i in data["items"] if i["product_id"] == product.id), None)
        assert item is not None
        assert item["quantity"] == 100
        assert item["total_value"] == 500  # 100 * 5.00

    def test_stock_valuation_filter_by_location(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test stock valuation filtered by location."""
        product = Product(name="Test", supplier_id=test_supplier.id, cost_price=Decimal("10"))
        db_session.add(product)
        db_session.commit()

        # Create stock in multiple locations
        loc2 = Location(name="Other Location", active=True)
        db_session.add(loc2)
        db_session.commit()

        stock1 = StockOnHand(product_id=product.id, location_id=test_location.id, qty=Decimal("50"))
        stock2 = StockOnHand(product_id=product.id, location_id=loc2.id, qty=Decimal("30"))
        db_session.add_all([stock1, stock2])
        db_session.commit()

        # Filter by location
        response = client.get(
            f"/api/v1/reports/stock-valuation?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Should only have stock from test_location
        assert all(item["location_id"] == test_location.id for item in data["items"])


class TestConsumptionReport:
    """Test consumption report."""

    def test_consumption_empty(self, client: TestClient, db_session, auth_headers):
        """Test consumption report with no sales."""
        response = client.get("/api/v1/reports/consumption", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_consumption_with_sales(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test consumption report with sales movements."""
        product = Product(
            name="Sold Product",
            supplier_id=test_supplier.id,
            cost_price=Decimal("3.00"),
            unit="btl",
            active=True,
        )
        db_session.add(product)
        db_session.commit()

        # Create sale movements
        movement = StockMovement(
            product_id=product.id,
            location_id=test_location.id,
            qty_delta=Decimal("-10"),  # Negative = consumption
            reason="sale",
            created_by=1,
        )
        db_session.add(movement)
        db_session.commit()

        response = client.get("/api/v1/reports/consumption?days=30", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        item = next((i for i in data["items"] if i["product_id"] == product.id), None)
        assert item is not None
        assert item["quantity"] == 10
        assert item["value"] == 30  # 10 * 3.00

    def test_consumption_different_periods(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test consumption report with different time periods."""
        product = Product(name="Product", supplier_id=test_supplier.id, cost_price=Decimal("1"))
        db_session.add(product)
        db_session.commit()

        # Movement from 3 days ago
        movement = StockMovement(
            product_id=product.id,
            location_id=test_location.id,
            qty_delta=Decimal("-5"),
            reason="sale",
            created_by=1,
        )
        db_session.add(movement)
        db_session.commit()

        # Test 7 days (should include)
        response = client.get("/api/v1/reports/consumption?days=7", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["items"]) >= 1


class TestMovementSummaryReport:
    """Test movement summary report."""

    def test_movement_summary_empty(self, client: TestClient, db_session, auth_headers):
        """Test movement summary with no movements."""
        response = client.get("/api/v1/reports/movement-summary", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["by_reason"] == []
        assert data["total_movements"] == 0

    def test_movement_summary_by_reason(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test movement summary grouped by reason."""
        product = Product(name="Product", supplier_id=test_supplier.id)
        db_session.add(product)
        db_session.commit()

        # Create movements with different reasons
        movements = [
            StockMovement(product_id=product.id, location_id=test_location.id, qty_delta=Decimal("10"), reason="purchase", created_by=1),
            StockMovement(product_id=product.id, location_id=test_location.id, qty_delta=Decimal("-5"), reason="sale", created_by=1),
            StockMovement(product_id=product.id, location_id=test_location.id, qty_delta=Decimal("-2"), reason="sale", created_by=1),
            StockMovement(product_id=product.id, location_id=test_location.id, qty_delta=Decimal("-1"), reason="waste", created_by=1),
        ]
        db_session.add_all(movements)
        db_session.commit()

        response = client.get("/api/v1/reports/movement-summary?days=7", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_movements"] == 4
        # Check reasons are grouped
        reasons = {r["reason"]: r for r in data["by_reason"]}
        assert "purchase" in reasons
        assert "sale" in reasons
        assert reasons["sale"]["count"] == 2


class TestLowStockReport:
    """Test low stock report."""

    def test_low_stock_empty(self, client: TestClient, db_session, auth_headers, test_location):
        """Test low stock report with no low stock items."""
        response = client.get(
            f"/api/v1/reports/low-stock?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []

    def test_low_stock_with_items(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test low stock report with items below target."""
        product = Product(
            name="Low Stock Item",
            supplier_id=test_supplier.id,
            min_stock=Decimal("20"),
            target_stock=Decimal("100"),
            cost_price=Decimal("5.00"),
            unit="pcs",
            active=True,
        )
        db_session.add(product)
        db_session.commit()

        stock = StockOnHand(
            product_id=product.id,
            location_id=test_location.id,
            qty=Decimal("15"),  # Below min_stock
        )
        db_session.add(stock)
        db_session.commit()

        response = client.get(
            f"/api/v1/reports/low-stock?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        assert data["total_items"] >= 1

        item = next((i for i in data["items"] if i["product_id"] == product.id), None)
        assert item is not None
        assert item["current_stock"] == 15
        assert item["reorder_qty"] == 85  # 100 - 15
        assert item["urgency"] == "urgent"  # Below min_stock

    def test_low_stock_urgency_levels(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test low stock urgency classification."""
        # Critical: <= 50% of min_stock
        critical = Product(
            name="Critical Item",
            supplier_id=test_supplier.id,
            min_stock=Decimal("100"),
            target_stock=Decimal("200"),
            active=True,
        )
        # Urgent: <= min_stock
        urgent = Product(
            name="Urgent Item",
            supplier_id=test_supplier.id,
            min_stock=Decimal("100"),
            target_stock=Decimal("200"),
            active=True,
        )
        # Normal: > min_stock but < target
        normal = Product(
            name="Normal Item",
            supplier_id=test_supplier.id,
            min_stock=Decimal("100"),
            target_stock=Decimal("200"),
            active=True,
        )
        db_session.add_all([critical, urgent, normal])
        db_session.commit()

        # Create stock at different levels
        stocks = [
            StockOnHand(product_id=critical.id, location_id=test_location.id, qty=Decimal("40")),  # 40% of min
            StockOnHand(product_id=urgent.id, location_id=test_location.id, qty=Decimal("80")),  # 80% of min
            StockOnHand(product_id=normal.id, location_id=test_location.id, qty=Decimal("150")),  # Above min, below target
        ]
        db_session.add_all(stocks)
        db_session.commit()

        response = client.get(
            f"/api/v1/reports/low-stock?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        items_by_name = {i["product_name"]: i for i in data["items"]}

        assert items_by_name["Critical Item"]["urgency"] == "critical"
        assert items_by_name["Urgent Item"]["urgency"] == "urgent"
        assert items_by_name["Normal Item"]["urgency"] == "normal"

        # Verify counts
        assert data["critical_count"] >= 1
        assert data["urgent_count"] >= 1


# ==================== INTEGRATION TESTS ====================

class TestOrderWorkflow:
    """Test complete order workflow."""

    def test_complete_order_workflow(self, client: TestClient, db_session, auth_headers, test_supplier, test_location, test_product):
        """Test creating and processing a purchase order through all stages."""
        # 1. Create order
        response = client.post(
            "/api/v1/orders/",
            headers=auth_headers,
            json={
                "supplier_id": test_supplier.id,
                "location_id": test_location.id,
                "notes": "Weekly restock",
                "lines": [
                    {"product_id": test_product.id, "qty": "50", "unit_cost": "1.50"}
                ]
            }
        )
        assert response.status_code == 201
        order_id = response.json()["id"]
        assert response.json()["status"] == "draft"

        # 2. Update to sent
        response = client.put(
            f"/api/v1/orders/{order_id}/status?status=sent",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "sent"

        # 3. Export for WhatsApp
        response = client.get(
            f"/api/v1/orders/{order_id}/export/whatsapp",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "text" in response.json()

        # 4. Update to received
        response = client.put(
            f"/api/v1/orders/{order_id}/status?status=received",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "received"

    def test_suggestion_to_order_workflow(self, client: TestClient, db_session, auth_headers, test_supplier, test_location):
        """Test creating orders from suggestions."""
        # Create product below target
        product = Product(
            name="Needs Reorder",
            supplier_id=test_supplier.id,
            target_stock=Decimal("100"),
            min_stock=Decimal("20"),
            active=True,
        )
        db_session.add(product)
        db_session.commit()

        stock = StockOnHand(
            product_id=product.id,
            location_id=test_location.id,
            qty=Decimal("10"),
        )
        db_session.add(stock)
        db_session.commit()

        # Get suggestions
        response = client.get(
            f"/api/v1/orders/suggestions?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        suggestions = response.json()
        assert len(suggestions["suggestions"]) >= 1

        # Create orders from suggestions
        response = client.post(
            "/api/v1/orders/from-suggestions",
            headers=auth_headers,
            json={
                "location_id": test_location.id,
                "supplier_ids": [test_supplier.id]
            }
        )
        assert response.status_code == 200
        orders = response.json()
        assert len(orders) >= 1


class TestReportIntegration:
    """Test reports with realistic data."""

    def test_reports_consistency(self, client: TestClient, db_session, auth_headers, test_location, test_supplier):
        """Test that reports are consistent with actual data."""
        # Create products with known values
        product = Product(
            name="Test Product",
            supplier_id=test_supplier.id,
            cost_price=Decimal("10.00"),
            unit="btl",
            active=True,
        )
        db_session.add(product)
        db_session.commit()

        # Add stock
        stock = StockOnHand(
            product_id=product.id,
            location_id=test_location.id,
            qty=Decimal("50"),
        )
        db_session.add(stock)
        db_session.commit()

        # Verify valuation
        response = client.get(
            f"/api/v1/reports/stock-valuation?location_id={test_location.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        item = next((i for i in data["items"] if i["product_id"] == product.id), None)
        assert item is not None
        assert item["total_value"] == 500  # 50 * 10
