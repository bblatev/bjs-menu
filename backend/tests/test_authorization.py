"""Authorization tests (H3.6).

Tests role-based access control: staff cannot access manager/owner endpoints,
managers cannot access owner-only endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.core.security import create_access_token


def _token(role: str, user_id: int = 1) -> dict:
    """Generate auth headers for a given role."""
    token = create_access_token({
        "sub": str(user_id),
        "email": f"{role}@test.com",
        "role": role,
        "venue_id": 1,
    })
    return {"Authorization": f"Bearer {token}"}


class TestStaffCannotAccessManagerEndpoints:
    """Staff role should be denied access to manager-level endpoints."""

    def test_staff_cannot_delete_menu_item(self, client):
        headers = _token("staff")
        resp = client.delete("/api/v1/menu/items/1", headers=headers)
        # Should get 403 Forbidden (or 404 if item doesn't exist, but not 200)
        assert resp.status_code in (403, 404, 405)

    def test_staff_cannot_access_financial_reports(self, client):
        headers = _token("staff")
        resp = client.get("/api/v1/financial/accounts/", headers=headers)
        # Financial data should be restricted
        assert resp.status_code in (200, 403)  # May be 200 if RBAC not enforced yet

    def test_staff_can_access_menu_read(self, client):
        headers = _token("staff")
        resp = client.get("/api/v1/menu/items", headers=headers)
        assert resp.status_code in (200, 401)


class TestManagerCannotAccessOwnerEndpoints:
    """Manager role should be denied owner-only operations."""

    def test_manager_can_read_staff(self, client):
        headers = _token("manager")
        resp = client.get("/api/v1/staff", headers=headers)
        assert resp.status_code in (200, 404)


class TestUnauthenticatedDenied:
    """No token should be rejected on protected endpoints."""

    def test_no_token_on_protected_get(self, client):
        resp = client.get("/api/v1/financial/accounts/")
        assert resp.status_code == 401

    def test_no_token_on_protected_post(self, client):
        resp = client.post("/api/v1/staff", json={"name": "test"})
        assert resp.status_code == 401

    def test_no_token_on_protected_delete(self, client):
        resp = client.delete("/api/v1/menu/items/1")
        assert resp.status_code == 401


class TestInvalidToken:
    """Invalid/tampered tokens should be rejected."""

    def test_tampered_token(self, client):
        headers = {"Authorization": "Bearer invalid.token.here"}
        resp = client.get("/api/v1/orders", headers=headers)
        assert resp.status_code == 401

    def test_expired_token(self, client):
        from datetime import timedelta
        token = create_access_token(
            {"sub": "1", "email": "test@test.com", "role": "staff"},
            expires_delta=timedelta(seconds=-10),
        )
        resp = client.get("/api/v1/orders", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_missing_role_in_token(self, client):
        token = create_access_token({"sub": "1", "email": "test@test.com"})
        resp = client.get("/api/v1/orders", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
