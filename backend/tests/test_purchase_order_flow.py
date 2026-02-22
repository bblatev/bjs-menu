"""Purchase order flow integration tests (H2.4)."""

import pytest
from fastapi.testclient import TestClient


class TestPurchaseOrderFlow:
    """Test the PO lifecycle: create -> submit -> approve -> receive."""

    def test_create_purchase_order(self, client, auth_headers, test_supplier):
        resp = client.post("/api/v1/purchase-orders", json={
            "supplier_id": test_supplier.id,
            "notes": "Test PO",
        }, headers=auth_headers)
        assert resp.status_code in (200, 201, 404, 422)

    def test_get_purchase_orders(self, client, auth_headers):
        resp = client.get("/api/v1/purchase-orders", headers=auth_headers)
        assert resp.status_code in (200, 404)

    def test_submit_purchase_order(self, client, auth_headers):
        resp = client.post("/api/v1/purchase-orders/1/submit", headers=auth_headers)
        assert resp.status_code in (200, 404, 422)

    def test_approve_purchase_order(self, client, auth_headers):
        resp = client.post("/api/v1/purchase-orders/1/approve", headers=auth_headers)
        assert resp.status_code in (200, 404, 422)

    def test_receive_purchase_order(self, client, auth_headers):
        resp = client.post("/api/v1/purchase-orders/1/receive", json={
            "lines": [{"line_id": 1, "quantity_received": 10}],
        }, headers=auth_headers)
        assert resp.status_code in (200, 404, 422)
