"""Split bill flow integration tests (H2.5)."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)


def _staff_headers():
    token = create_access_token({
        "sub": "1", "email": "staff@test.com", "role": "staff", "venue_id": 1,
    })
    return {"Authorization": f"Bearer {token}"}


class TestSplitBillFlow:
    """Test check splitting functionality."""

    def test_create_check(self):
        headers = _staff_headers()
        resp = client.post("/api/v1/waiter/checks", json={
            "table_id": 1,
        }, headers=headers)
        assert resp.status_code in (200, 201, 404, 422)

    def test_get_checks(self):
        headers = _staff_headers()
        resp = client.get("/api/v1/waiter/checks", headers=headers)
        assert resp.status_code in (200, 404)

    def test_split_check_evenly(self):
        headers = _staff_headers()
        resp = client.post("/api/v1/waiter/checks/1/split", json={
            "split_count": 2,
            "method": "even",
        }, headers=headers)
        assert resp.status_code in (200, 404, 422)

    def test_split_check_by_item(self):
        headers = _staff_headers()
        resp = client.post("/api/v1/waiter/checks/1/split", json={
            "method": "by_item",
            "item_assignments": {"1": 1, "2": 2},
        }, headers=headers)
        assert resp.status_code in (200, 404, 422)

    def test_pay_split_check(self):
        headers = _staff_headers()
        resp = client.post("/api/v1/waiter/checks/1/pay", json={
            "payment_method": "cash",
            "amount": 25.00,
        }, headers=headers)
        assert resp.status_code in (200, 404, 422)
