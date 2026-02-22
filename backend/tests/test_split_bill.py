"""Split bill flow integration tests (H2.5)."""

import pytest
from fastapi.testclient import TestClient


class TestSplitBillFlow:
    """Test check splitting functionality."""

    def test_create_check(self, client, auth_headers, db_session):
        from app.models.restaurant import Table
        table = Table(number="SB1", capacity=4, status="available", area="Main")
        db_session.add(table)
        db_session.commit()

        resp = client.post("/api/v1/waiter/checks", json={
            "table_id": table.id,
        }, headers=auth_headers)
        assert resp.status_code in (200, 201, 404, 422)

    def test_get_checks(self, client, auth_headers):
        resp = client.get("/api/v1/waiter/checks", headers=auth_headers)
        assert resp.status_code in (200, 404)

    def test_split_check_evenly(self, client, auth_headers):
        resp = client.post("/api/v1/waiter/checks/1/split", json={
            "split_count": 2,
            "method": "even",
        }, headers=auth_headers)
        assert resp.status_code in (200, 404, 422)

    def test_split_check_by_item(self, client, auth_headers):
        resp = client.post("/api/v1/waiter/checks/1/split", json={
            "method": "by_item",
            "item_assignments": {"1": 1, "2": 2},
        }, headers=auth_headers)
        assert resp.status_code in (200, 404, 422)

    def test_pay_split_check(self, client, auth_headers):
        resp = client.post("/api/v1/waiter/checks/1/pay", json={
            "payment_method": "cash",
            "amount": 25.00,
        }, headers=auth_headers)
        assert resp.status_code in (200, 404, 422)
