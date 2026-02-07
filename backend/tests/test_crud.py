"""Integration tests for CRUD endpoint cycles (H2.1)."""

import pytest
from decimal import Decimal

from app.core.rbac import UserRole
from app.core.security import create_access_token, get_password_hash
from app.models.user import User


# ============== Supplier CRUD ==============

class TestSupplierCRUD:
    """Full create-read-update-delete cycle for suppliers."""

    def test_create_supplier(self, client, auth_headers):
        res = client.post("/api/v1/suppliers/", json={
            "name": "New Supplier",
            "contact_phone": "555-0001",
            "contact_email": "new@supplier.com",
        }, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "New Supplier"
        assert data["id"] > 0

    def test_list_suppliers(self, client, test_supplier):
        res = client.get("/api/v1/suppliers/")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        names = [s["name"] for s in data]
        assert "Test Supplier" in names

    def test_get_supplier(self, client, auth_headers, test_supplier):
        res = client.get(f"/api/v1/suppliers/{test_supplier.id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Test Supplier"

    def test_get_nonexistent_supplier_404(self, client, auth_headers):
        res = client.get("/api/v1/suppliers/99999", headers=auth_headers)
        assert res.status_code == 404

    def test_update_supplier(self, client, auth_headers, test_supplier):
        res = client.put(f"/api/v1/suppliers/{test_supplier.id}", json={
            "name": "Updated Supplier",
            "notes": "Updated notes",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Updated Supplier"

    def test_full_crud_cycle(self, client, auth_headers):
        # Create
        res = client.post("/api/v1/suppliers/", json={
            "name": "Cycle Supplier",
            "contact_email": "cycle@test.com",
        }, headers=auth_headers)
        assert res.status_code == 201
        supplier_id = res.json()["id"]

        # Read
        res = client.get(f"/api/v1/suppliers/{supplier_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Cycle Supplier"

        # Update
        res = client.put(f"/api/v1/suppliers/{supplier_id}", json={
            "name": "Cycle Supplier Updated",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Cycle Supplier Updated"

        # Verify update persisted
        res = client.get(f"/api/v1/suppliers/{supplier_id}", headers=auth_headers)
        assert res.json()["name"] == "Cycle Supplier Updated"


# ============== Product CRUD ==============

class TestProductCRUD:
    """Full CRUD cycle for products."""

    def test_create_product(self, client, auth_headers, test_supplier):
        res = client.post("/api/v1/products/", json={
            "name": "New Product",
            "barcode": "9999999999999",
            "supplier_id": test_supplier.id,
            "cost_price": "2.50",
        }, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "New Product"
        assert data["barcode"] == "9999999999999"

    def test_duplicate_barcode_rejected(self, client, auth_headers, test_product):
        res = client.post("/api/v1/products/", json={
            "name": "Duplicate",
            "barcode": test_product.barcode,
        }, headers=auth_headers)
        assert res.status_code == 400

    def test_list_products(self, client, auth_headers, test_product):
        res = client.get("/api/v1/products/", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1

    def test_get_product_by_id(self, client, auth_headers, test_product):
        res = client.get(f"/api/v1/products/{test_product.id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Test Beer"

    def test_get_product_by_barcode(self, client, auth_headers, test_product):
        res = client.get(
            f"/api/v1/products/by-barcode/{test_product.barcode}",
            headers=auth_headers,
        )
        assert res.status_code == 200
        assert res.json()["id"] == test_product.id

    def test_update_product(self, client, auth_headers, test_product):
        res = client.put(f"/api/v1/products/{test_product.id}", json={
            "name": "Updated Beer",
            "cost_price": "2.00",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Updated Beer"

    def test_search_products(self, client, auth_headers, test_product):
        res = client.get("/api/v1/products/?search=Beer", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["total"] >= 1


# ============== Customer CRUD (all mutating requests require auth) ==============

class TestCustomerCRUD:
    """Full CRUD cycle for customers."""

    def test_create_customer(self, client, auth_headers):
        res = client.post("/api/v1/customers/", json={
            "name": "Jane Doe",
            "phone": "555-1111",
            "email": "jane@test.com",
        }, headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Jane Doe"
        assert data["id"] > 0

    def test_duplicate_phone_rejected(self, client, auth_headers):
        client.post("/api/v1/customers/", json={
            "name": "First", "phone": "555-DUP",
        }, headers=auth_headers)
        res = client.post("/api/v1/customers/", json={
            "name": "Second", "phone": "555-DUP",
        }, headers=auth_headers)
        assert res.status_code == 400

    def test_list_customers(self, client, auth_headers):
        client.post("/api/v1/customers/", json={
            "name": "List Test", "phone": "555-LIST",
        }, headers=auth_headers)
        res = client.get("/api/v1/customers/")
        assert res.status_code == 200
        data = res.json()
        assert data["total"] >= 1

    def test_get_customer(self, client, auth_headers):
        create_res = client.post("/api/v1/customers/", json={
            "name": "Get Test", "phone": "555-GET",
        }, headers=auth_headers)
        cust_id = create_res.json()["id"]

        res = client.get(f"/api/v1/customers/{cust_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "Get Test"

    def test_update_customer(self, client, auth_headers):
        create_res = client.post("/api/v1/customers/", json={
            "name": "Original", "phone": "555-UPD",
        }, headers=auth_headers)
        cust_id = create_res.json()["id"]

        res = client.put(f"/api/v1/customers/{cust_id}", json={
            "name": "Updated",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"

    def test_delete_customer(self, client, auth_headers):
        create_res = client.post("/api/v1/customers/", json={
            "name": "Delete Me", "phone": "555-DEL",
        }, headers=auth_headers)
        cust_id = create_res.json()["id"]

        res = client.delete(f"/api/v1/customers/{cust_id}", headers=auth_headers)
        assert res.status_code == 200

        # Verify deleted
        res = client.get(f"/api/v1/customers/{cust_id}")
        assert res.status_code == 404

    def test_search_customers(self, client, auth_headers):
        client.post("/api/v1/customers/", json={
            "name": "Searchable Person", "phone": "555-SRCH",
        }, headers=auth_headers)
        res = client.get("/api/v1/customers/?search=Searchable")
        assert res.status_code == 200
        assert res.json()["total"] >= 1


# ============== Recipe CRUD ==============

class TestRecipeCRUD:
    """Full CRUD cycle for recipes (BOM)."""

    def test_create_recipe(self, client, auth_headers, test_product):
        res = client.post("/api/v1/recipes/", json={
            "name": "Test Cocktail",
            "pos_item_name": "Cocktail",
            "lines": [{
                "product_id": test_product.id,
                "qty": "0.5",
                "unit": "L",
            }],
        }, headers=auth_headers)
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Test Cocktail"
        assert len(data["lines"]) == 1

    def test_list_recipes(self, client, auth_headers, test_product):
        # Create one first
        client.post("/api/v1/recipes/", json={
            "name": "List Recipe",
            "lines": [{"product_id": test_product.id, "qty": "1", "unit": "pcs"}],
        }, headers=auth_headers)

        res = client.get("/api/v1/recipes/")
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_get_recipe(self, client, auth_headers, test_product):
        create_res = client.post("/api/v1/recipes/", json={
            "name": "Get Recipe",
            "lines": [{"product_id": test_product.id, "qty": "2", "unit": "pcs"}],
        }, headers=auth_headers)
        recipe_id = create_res.json()["id"]

        res = client.get(f"/api/v1/recipes/{recipe_id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Get Recipe"

    def test_update_recipe(self, client, auth_headers, test_product):
        create_res = client.post("/api/v1/recipes/", json={
            "name": "Old Name",
            "lines": [{"product_id": test_product.id, "qty": "1", "unit": "pcs"}],
        }, headers=auth_headers)
        recipe_id = create_res.json()["id"]

        res = client.put(f"/api/v1/recipes/{recipe_id}", json={
            "name": "New Name",
        }, headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "New Name"

    def test_delete_recipe(self, client, auth_headers, test_product):
        create_res = client.post("/api/v1/recipes/", json={
            "name": "Delete Me",
            "lines": [{"product_id": test_product.id, "qty": "1", "unit": "pcs"}],
        }, headers=auth_headers)
        recipe_id = create_res.json()["id"]

        res = client.delete(f"/api/v1/recipes/{recipe_id}", headers=auth_headers)
        assert res.status_code == 204

        # Verify deleted
        res = client.get(f"/api/v1/recipes/{recipe_id}", headers=auth_headers)
        assert res.status_code == 404

    def test_recipe_with_invalid_product_400(self, client, auth_headers):
        res = client.post("/api/v1/recipes/", json={
            "name": "Bad Recipe",
            "lines": [{"product_id": 99999, "qty": "1", "unit": "pcs"}],
        }, headers=auth_headers)
        assert res.status_code == 400


# ============== Location CRUD ==============

class TestLocationCRUD:
    def test_list_locations(self, client, auth_headers, test_location):
        res = client.get("/api/v1/locations/", headers=auth_headers)
        assert res.status_code == 200

    def test_get_location(self, client, auth_headers, test_location):
        res = client.get(f"/api/v1/locations/{test_location.id}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["name"] == "Main Bar"
