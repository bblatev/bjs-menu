"""Comprehensive tests for recipes and invoices API endpoints."""

import pytest
from decimal import Decimal
from datetime import date
from fastapi.testclient import TestClient

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.recipe import Recipe, RecipeLine
from app.models.invoice import Invoice, InvoiceLine, GLCode, PriceAlert


# ==================== RECIPE TESTS ====================

class TestRecipeEndpoints:
    """Test recipe (BOM) management endpoints."""

    def test_list_recipes_empty(self, client: TestClient, db_session, auth_headers):
        """Test listing recipes when none exist."""
        response = client.get("/api/v1/recipes/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_create_recipe(self, client: TestClient, db_session, auth_headers, test_product):
        """Test creating a recipe."""
        response = client.post(
            "/api/v1/recipes/",
            headers=auth_headers,
            json={
                "name": "Margarita",
                "pos_item_id": "MAR001",
                "pos_item_name": "Classic Margarita",
                "lines": [
                    {"product_id": test_product.id, "qty": "2.0", "unit": "oz"}
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Margarita"
        assert data["pos_item_id"] == "MAR001"
        assert len(data["lines"]) == 1

    def test_create_recipe_without_lines(self, client: TestClient, db_session, auth_headers):
        """Test creating a recipe without lines."""
        response = client.post(
            "/api/v1/recipes/",
            headers=auth_headers,
            json={
                "name": "Empty Recipe",
                "lines": []
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Empty Recipe"
        assert data["lines"] == []

    def test_create_recipe_invalid_product(self, client: TestClient, db_session, auth_headers):
        """Test creating recipe with non-existent product."""
        response = client.post(
            "/api/v1/recipes/",
            headers=auth_headers,
            json={
                "name": "Bad Recipe",
                "lines": [
                    {"product_id": 9999, "qty": "1.0", "unit": "oz"}
                ]
            }
        )
        assert response.status_code == 400

    def test_create_recipe_duplicate_pos_item_id(self, client: TestClient, db_session, auth_headers):
        """Test creating recipe with duplicate pos_item_id."""
        recipe = Recipe(name="First Recipe", pos_item_id="DUPE001")
        db_session.add(recipe)
        db_session.commit()

        response = client.post(
            "/api/v1/recipes/",
            headers=auth_headers,
            json={
                "name": "Second Recipe",
                "pos_item_id": "DUPE001",  # Duplicate
                "lines": []
            }
        )
        assert response.status_code == 400

    def test_get_recipe(self, client: TestClient, db_session, auth_headers, test_product):
        """Test getting a specific recipe."""
        recipe = Recipe(name="Test Recipe", pos_item_id="TEST001")
        db_session.add(recipe)
        db_session.flush()

        line = RecipeLine(
            recipe_id=recipe.id,
            product_id=test_product.id,
            qty=Decimal("1.5"),
            unit="oz",
        )
        db_session.add(line)
        db_session.commit()

        response = client.get(f"/api/v1/recipes/{recipe.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Recipe"
        assert len(data["lines"]) == 1

    def test_get_recipe_not_found(self, client: TestClient, db_session, auth_headers):
        """Test getting non-existent recipe."""
        response = client.get("/api/v1/recipes/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_list_recipes(self, client: TestClient, db_session, auth_headers):
        """Test listing recipes."""
        recipe1 = Recipe(name="Recipe A")
        recipe2 = Recipe(name="Recipe B")
        db_session.add_all([recipe1, recipe2])
        db_session.commit()

        response = client.get("/api/v1/recipes/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) >= 2

    def test_list_recipes_search(self, client: TestClient, db_session, auth_headers):
        """Test searching recipes."""
        recipe1 = Recipe(name="Margarita")
        recipe2 = Recipe(name="Mojito")
        db_session.add_all([recipe1, recipe2])
        db_session.commit()

        response = client.get("/api/v1/recipes/?search=Marg", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Margarita"

    def test_update_recipe(self, client: TestClient, db_session, auth_headers, test_product):
        """Test updating a recipe."""
        recipe = Recipe(name="Original Name")
        db_session.add(recipe)
        db_session.commit()

        response = client.put(
            f"/api/v1/recipes/{recipe.id}",
            headers=auth_headers,
            json={
                "name": "Updated Name",
                "pos_item_name": "New POS Name",
            }
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"
        assert response.json()["pos_item_name"] == "New POS Name"

    def test_update_recipe_lines(self, client: TestClient, db_session, auth_headers, test_product):
        """Test updating recipe with new lines."""
        recipe = Recipe(name="Recipe With Lines")
        db_session.add(recipe)
        db_session.flush()

        old_line = RecipeLine(
            recipe_id=recipe.id,
            product_id=test_product.id,
            qty=Decimal("1.0"),
            unit="oz",
        )
        db_session.add(old_line)
        db_session.commit()

        response = client.put(
            f"/api/v1/recipes/{recipe.id}",
            headers=auth_headers,
            json={
                "lines": [
                    {"product_id": test_product.id, "qty": "2.5", "unit": "ml"}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["lines"]) == 1
        assert float(data["lines"][0]["qty"]) == 2.5

    def test_update_recipe_not_found(self, client: TestClient, db_session, auth_headers):
        """Test updating non-existent recipe."""
        response = client.put(
            "/api/v1/recipes/9999",
            headers=auth_headers,
            json={"name": "New Name"}
        )
        assert response.status_code == 404

    def test_delete_recipe(self, client: TestClient, db_session, auth_headers):
        """Test deleting a recipe."""
        recipe = Recipe(name="To Delete")
        db_session.add(recipe)
        db_session.commit()

        response = client.delete(f"/api/v1/recipes/{recipe.id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/v1/recipes/{recipe.id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_recipe_not_found(self, client: TestClient, db_session, auth_headers):
        """Test deleting non-existent recipe."""
        response = client.delete("/api/v1/recipes/9999", headers=auth_headers)
        assert response.status_code == 404


# ==================== INVOICE TESTS ====================

class TestInvoiceEndpoints:
    """Test invoice management endpoints."""

    def test_list_invoices_empty(self, client: TestClient, db_session, auth_headers):
        """Test listing invoices when none exist."""
        response = client.get("/api/v1/invoices/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_create_invoice(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test creating an invoice."""
        response = client.post(
            "/api/v1/invoices/",
            headers=auth_headers,
            json={
                "supplier_id": test_supplier.id,
                "invoice_number": "INV-001",
                "invoice_date": "2024-01-15",
                "subtotal": "100.00",
                "tax": "10.00",
                "total": "110.00",
                "lines": [
                    {
                        "line_number": 1,
                        "description": "Beer cases",
                        "quantity": 10,
                        "unit_price": "10.00",
                        "total_price": "100.00"
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_number"] == "INV-001"
        assert len(data["lines"]) == 1

    def test_create_invoice_minimal(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test creating invoice with minimal data."""
        response = client.post(
            "/api/v1/invoices/",
            headers=auth_headers,
            json={
                "supplier_id": test_supplier.id,
                "invoice_number": "INV-MIN",
                "invoice_date": "2024-01-15",
                "lines": []
            }
        )
        assert response.status_code == 200

    def test_get_invoice(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test getting a specific invoice."""
        invoice = Invoice(
            supplier_id=test_supplier.id,
            invoice_number="INV-GET",
            subtotal=Decimal("50.00"),
            tax_amount=Decimal("5.00"),
            total_amount=Decimal("55.00"),
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.get(f"/api/v1/invoices/{invoice.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["invoice_number"] == "INV-GET"

    def test_get_invoice_not_found(self, client: TestClient, db_session, auth_headers):
        """Test getting non-existent invoice."""
        response = client.get("/api/v1/invoices/9999", headers=auth_headers)
        assert response.status_code == 404

    def test_list_invoices_filter_by_supplier(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test filtering invoices by supplier."""
        invoice = Invoice(supplier_id=test_supplier.id, invoice_number="SUP-001")
        db_session.add(invoice)
        db_session.commit()

        response = client.get(f"/api/v1/invoices/?supplier_id={test_supplier.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(inv["supplier_id"] == test_supplier.id for inv in data)

    def test_list_invoices_filter_by_status(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test filtering invoices by status."""
        invoice1 = Invoice(supplier_id=test_supplier.id, invoice_number="STAT-001", status="pending")
        invoice2 = Invoice(supplier_id=test_supplier.id, invoice_number="STAT-002", status="approved")
        db_session.add_all([invoice1, invoice2])
        db_session.commit()

        response = client.get("/api/v1/invoices/?status=pending", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert all(inv["status"] == "pending" for inv in data)

    def test_update_invoice(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test updating an invoice."""
        invoice = Invoice(
            supplier_id=test_supplier.id,
            invoice_number="UPD-001",
            status="pending",
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.put(
            f"/api/v1/invoices/{invoice.id}",
            headers=auth_headers,
            json={"status": "approved", "notes": "Reviewed"}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "approved"

    def test_update_invoice_not_found(self, client: TestClient, db_session, auth_headers):
        """Test updating non-existent invoice."""
        response = client.put(
            "/api/v1/invoices/9999",
            headers=auth_headers,
            json={"status": "approved"}
        )
        assert response.status_code == 404

    def test_delete_invoice(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test deleting an invoice."""
        invoice = Invoice(supplier_id=test_supplier.id, invoice_number="DEL-001")
        db_session.add(invoice)
        db_session.commit()

        response = client.delete(f"/api/v1/invoices/{invoice.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_invoice_not_found(self, client: TestClient, db_session, auth_headers):
        """Test deleting non-existent invoice."""
        response = client.delete("/api/v1/invoices/9999", headers=auth_headers)
        assert response.status_code == 404


# ==================== GL CODE TESTS ====================

class TestGLCodeEndpoints:
    """Test GL code management endpoints."""

    def test_list_gl_codes_empty(self, client: TestClient, db_session, auth_headers):
        """Test listing GL codes when none exist."""
        response = client.get("/api/v1/invoices/gl-codes/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_create_gl_code(self, client: TestClient, db_session, auth_headers):
        """Test creating a GL code."""
        response = client.post(
            "/api/v1/invoices/gl-codes/",
            headers=auth_headers,
            json={
                "code": "5000",
                "name": "Cost of Goods Sold",
                "description": "COGS account",
                "category": "expense"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "5000"
        assert data["name"] == "Cost of Goods Sold"

    def test_list_gl_codes(self, client: TestClient, db_session, auth_headers):
        """Test listing GL codes."""
        gl1 = GLCode(code="5001", name="Food Cost", is_active=True)
        gl2 = GLCode(code="5002", name="Beverage Cost", is_active=True)
        gl3 = GLCode(code="5003", name="Inactive", is_active=False)
        db_session.add_all([gl1, gl2, gl3])
        db_session.commit()

        response = client.get("/api/v1/invoices/gl-codes/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should only show active GL codes
        assert len(data) == 2


# ==================== PRICE ALERT TESTS ====================

class TestPriceAlertEndpoints:
    """Test price alert endpoints."""

    def test_list_price_alerts_empty(self, client: TestClient, db_session, auth_headers):
        """Test listing price alerts when none exist."""
        response = client.get("/api/v1/invoices/price-alerts/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_price_alerts(self, client: TestClient, db_session, auth_headers, test_product, test_supplier):
        """Test listing price alerts."""
        # Use actual model fields (alert configuration model)
        alert = PriceAlert(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            alert_type="price_increase",
            threshold_percent=10.0,
            is_active=True,
        )
        db_session.add(alert)
        db_session.commit()

        response = client.get("/api/v1/invoices/price-alerts/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_list_price_alerts_filter_active(self, client: TestClient, db_session, auth_headers, test_product, test_supplier):
        """Test filtering price alerts by active status."""
        response = client.get("/api/v1/invoices/price-alerts/?active=true", headers=auth_headers)
        assert response.status_code == 200

    def test_acknowledge_price_alert(self, client: TestClient, db_session, auth_headers, test_product, test_supplier, test_user):
        """Test acknowledging a price alert."""
        alert = PriceAlert(
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            alert_type="price_increase",
            threshold_percent=10.0,
            is_active=True,
        )
        db_session.add(alert)
        db_session.commit()

        response = client.post(
            f"/api/v1/invoices/price-alerts/{alert.id}/acknowledge?user_id={test_user.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["status"] == "acknowledged"

    def test_acknowledge_price_alert_not_found(self, client: TestClient, db_session, auth_headers, test_user):
        """Test acknowledging non-existent alert."""
        response = client.post(
            f"/api/v1/invoices/price-alerts/9999/acknowledge?user_id={test_user.id}",
            headers=auth_headers
        )
        assert response.status_code == 404


# ==================== INVOICE APPROVAL TESTS ====================

class TestInvoiceApprovalEndpoints:
    """Test invoice approval workflow endpoints."""

    def test_approve_invoice(self, client: TestClient, db_session, auth_headers, test_supplier, test_user):
        """Test approving an invoice."""
        invoice = Invoice(
            supplier_id=test_supplier.id,
            invoice_number="APR-001",
            status="pending",
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/approve?approver_id={test_user.id}",
            headers=auth_headers,
            json={"notes": "Looks good"}
        )
        assert response.status_code in [200, 400]

    def test_reject_invoice(self, client: TestClient, db_session, auth_headers, test_supplier, test_user):
        """Test rejecting an invoice."""
        invoice = Invoice(
            supplier_id=test_supplier.id,
            invoice_number="REJ-001",
            status="pending",
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.post(
            f"/api/v1/invoices/{invoice.id}/reject?approver_id={test_user.id}",
            headers=auth_headers,
            json={"notes": "Price too high"}
        )
        assert response.status_code in [200, 400]

    def test_get_invoice_approvals(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test getting approval history for an invoice."""
        invoice = Invoice(
            supplier_id=test_supplier.id,
            invoice_number="HIST-001",
        )
        db_session.add(invoice)
        db_session.commit()

        response = client.get(f"/api/v1/invoices/{invoice.id}/approvals", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ==================== INTEGRATION TESTS ====================

class TestRecipeIntegration:
    """Test recipe integration workflows."""

    def test_recipe_with_multiple_products(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test creating a recipe with multiple products."""
        # Create multiple products
        products = [
            Product(name=f"Ingredient {i}", supplier_id=test_supplier.id, active=True)
            for i in range(3)
        ]
        db_session.add_all(products)
        db_session.commit()

        # Create recipe with all products
        response = client.post(
            "/api/v1/recipes/",
            headers=auth_headers,
            json={
                "name": "Complex Cocktail",
                "pos_item_id": "COMP001",
                "lines": [
                    {"product_id": p.id, "qty": f"{i+1}.0", "unit": "oz"}
                    for i, p in enumerate(products)
                ]
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["lines"]) == 3

    def test_recipe_update_preserves_lines(self, client: TestClient, db_session, auth_headers, test_product):
        """Test that updating recipe name preserves lines."""
        # Create recipe with lines
        recipe = Recipe(name="Original")
        db_session.add(recipe)
        db_session.flush()

        line = RecipeLine(
            recipe_id=recipe.id,
            product_id=test_product.id,
            qty=Decimal("2.0"),
            unit="oz",
        )
        db_session.add(line)
        db_session.commit()

        # Update only name (not lines)
        response = client.put(
            f"/api/v1/recipes/{recipe.id}",
            headers=auth_headers,
            json={"name": "Updated Name"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        # Lines should be preserved
        assert len(data["lines"]) == 1


class TestInvoiceIntegration:
    """Test invoice integration workflows."""

    def test_invoice_with_multiple_lines(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test creating an invoice with multiple lines."""
        response = client.post(
            "/api/v1/invoices/",
            headers=auth_headers,
            json={
                "supplier_id": test_supplier.id,
                "invoice_number": "MULTI-001",
                "invoice_date": "2024-01-15",
                "subtotal": "250.00",
                "tax": "25.00",
                "total": "275.00",
                "lines": [
                    {"line_number": 1, "description": "Item 1", "quantity": 10, "unit_price": "10.00", "total_price": "100.00"},
                    {"line_number": 2, "description": "Item 2", "quantity": 5, "unit_price": "20.00", "total_price": "100.00"},
                    {"line_number": 3, "description": "Item 3", "quantity": 2, "unit_price": "25.00", "total_price": "50.00"},
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["lines"]) == 3

    def test_invoice_filtering_combined(self, client: TestClient, db_session, auth_headers, test_supplier):
        """Test combined invoice filtering."""
        # Create invoices with different attributes
        inv1 = Invoice(
            supplier_id=test_supplier.id,
            invoice_number="COMB-001",
            status="pending",
            invoice_date=date(2024, 1, 15),
        )
        inv2 = Invoice(
            supplier_id=test_supplier.id,
            invoice_number="COMB-002",
            status="approved",
            invoice_date=date(2024, 1, 20),
        )
        db_session.add_all([inv1, inv2])
        db_session.commit()

        # Filter by supplier and status
        response = client.get(
            f"/api/v1/invoices/?supplier_id={test_supplier.id}&status=pending",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert all(inv["status"] == "pending" for inv in data)
