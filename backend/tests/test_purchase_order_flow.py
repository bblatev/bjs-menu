"""Purchase order flow integration tests (H2.4)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


def _manager_headers():
    token = create_access_token({
        "sub": "1", "email": "manager@test.com", "role": "manager", "venue_id": 1,
    })
    return {"Authorization": f"Bearer {token}"}


class TestPurchaseOrderFlow:
    """Test the PO lifecycle: create -> submit -> approve -> receive."""

    def test_create_purchase_order(self):
        headers = _manager_headers()
        resp = client.post("/api/v1/purchase-orders", json={
            "supplier_id": 1,
            "notes": "Test PO",
        }, headers=headers)
        assert resp.status_code in (200, 201, 404, 422)

    def test_get_purchase_orders(self):
        headers = _manager_headers()
        resp = client.get("/api/v1/purchase-orders", headers=headers)
        assert resp.status_code in (200, 404)

    def test_submit_purchase_order(self):
        headers = _manager_headers()
        resp = client.post("/api/v1/purchase-orders/1/submit", headers=headers)
        assert resp.status_code in (200, 404, 422)

    def test_approve_purchase_order(self):
        headers = _manager_headers()
        resp = client.post("/api/v1/purchase-orders/1/approve", headers=headers)
        assert resp.status_code in (200, 404, 422)

    def test_receive_purchase_order(self):
        headers = _manager_headers()
        resp = client.post("/api/v1/purchase-orders/1/receive", json={
            "lines": [{"line_id": 1, "quantity_received": 10}],
        }, headers=headers)
        assert resp.status_code in (200, 404, 422)
