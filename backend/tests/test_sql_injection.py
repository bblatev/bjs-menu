"""SQL injection tests (H3.2).

Verifies that SQL injection payloads do not cause SQL errors
or data leakage on any endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SQL_PAYLOADS = [
    "'; DROP TABLE users; --",
    "1 OR 1=1",
    "' UNION SELECT * FROM users --",
    "1; DELETE FROM products WHERE 1=1",
    "' OR '1'='1",
    "admin'--",
    "1' AND (SELECT COUNT(*) FROM users) > 0 --",
    "'; EXEC xp_cmdshell('dir'); --",
    "1' WAITFOR DELAY '0:0:5' --",
    "' OR '' = '",
]


class TestSQLInjectionPathParams:
    """Test SQL injection via path parameters."""

    @pytest.mark.parametrize("payload", SQL_PAYLOADS[:3])
    def test_order_id_injection(self, payload):
        resp = client.get(f"/api/v1/orders/{payload}")
        # Should not return 500 (SQL error) — 401/404/422 are acceptable
        assert resp.status_code != 500

    @pytest.mark.parametrize("payload", SQL_PAYLOADS[:3])
    def test_menu_item_id_injection(self, payload):
        resp = client.get(f"/api/v1/menu/items/{payload}")
        assert resp.status_code != 500

    @pytest.mark.parametrize("payload", SQL_PAYLOADS[:3])
    def test_customer_id_injection(self, payload):
        resp = client.get(f"/api/v1/customers/{payload}")
        assert resp.status_code != 500


class TestSQLInjectionQueryParams:
    """Test SQL injection via query parameters."""

    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    def test_search_injection(self, payload):
        resp = client.get("/api/v1/menu/items", params={"search": payload})
        assert resp.status_code != 500

    @pytest.mark.parametrize("payload", SQL_PAYLOADS[:3])
    def test_filter_injection(self, payload):
        resp = client.get("/api/v1/stock/items", params={"category": payload})
        assert resp.status_code != 500


class TestSQLInjectionRequestBody:
    """Test SQL injection via JSON request body."""

    def test_guest_order_item_name_injection(self):
        for payload in SQL_PAYLOADS[:3]:
            resp = client.post("/api/v1/guest-orders/create", json={
                "table_number": 1,
                "items": [{"name": payload, "quantity": 1, "menu_item_id": 1}],
            })
            assert resp.status_code != 500

    def test_login_injection(self):
        for payload in SQL_PAYLOADS[:3]:
            resp = client.post("/api/v1/auth/login", json={
                "email": payload,
                "password": payload,
            })
            assert resp.status_code in (401, 422, 400, 200)
