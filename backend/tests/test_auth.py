"""Tests for authentication: login, token, PIN, RBAC (H1.1, H1.6)."""

import pytest
from datetime import timedelta

from app.core.rbac import UserRole
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    get_pin_hash,
    verify_password,
    verify_pin,
)
from app.models.user import User


# ============== Password hashing ==============

class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = get_password_hash("secret123")
        assert verify_password("secret123", h)

    def test_wrong_password_rejected(self):
        h = get_password_hash("secret123")
        assert not verify_password("wrong", h)

    def test_hash_is_unique(self):
        h1 = get_password_hash("same")
        h2 = get_password_hash("same")
        assert h1 != h2  # different salts

    def test_empty_password(self):
        h = get_password_hash("")
        assert verify_password("", h)

    def test_invalid_hash_returns_false(self):
        assert not verify_password("test", "not-a-hash")


# ============== PIN hashing ==============

class TestPinHashing:
    def test_hash_and_verify(self):
        h = get_pin_hash("1234")
        assert verify_pin("1234", h)

    def test_wrong_pin_rejected(self):
        h = get_pin_hash("1234")
        assert not verify_pin("5678", h)

    def test_invalid_hash_returns_false(self):
        assert not verify_pin("1234", "bad-hash")


# ============== JWT tokens ==============

class TestJWTTokens:
    def test_create_and_decode(self):
        token = create_access_token(data={"sub": "42", "email": "a@b.com", "role": "owner"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["email"] == "a@b.com"
        assert payload["role"] == "owner"

    def test_token_has_expiry(self):
        token = create_access_token(data={"sub": "1"})
        payload = decode_access_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_custom_expiry(self):
        token = create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(hours=1),
        )
        payload = decode_access_token(token)
        assert payload is not None

    def test_expired_token_rejected(self):
        token = create_access_token(
            data={"sub": "1"},
            expires_delta=timedelta(seconds=-10),
        )
        assert decode_access_token(token) is None

    def test_invalid_token_rejected(self):
        assert decode_access_token("not.a.token") is None

    def test_tampered_token_rejected(self):
        token = create_access_token(data={"sub": "1"})
        tampered = token[:-5] + "XXXXX"
        assert decode_access_token(tampered) is None


# ============== Login endpoint ==============

class TestLoginEndpoint:
    def test_successful_login(self, client, db_session):
        user = User(
            email="login@test.com",
            password_hash=get_password_hash("pass123"),
            role=UserRole.MANAGER,
            name="Login User",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        res = client.post("/api/v1/auth/login", json={
            "email": "login@test.com",
            "password": "pass123",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_wrong_password_401(self, client, db_session):
        user = User(
            email="wrong@test.com",
            password_hash=get_password_hash("correct"),
            role=UserRole.STAFF,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        res = client.post("/api/v1/auth/login", json={
            "email": "wrong@test.com",
            "password": "incorrect",
        })
        assert res.status_code == 401

    def test_nonexistent_user_401(self, client):
        res = client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "anything",
        })
        assert res.status_code == 401

    def test_inactive_user_401(self, client, db_session):
        user = User(
            email="inactive@test.com",
            password_hash=get_password_hash("pass"),
            role=UserRole.STAFF,
            is_active=False,
        )
        db_session.add(user)
        db_session.commit()

        res = client.post("/api/v1/auth/login", json={
            "email": "inactive@test.com",
            "password": "pass",
        })
        assert res.status_code == 401


# ============== PIN login endpoint ==============

class TestPinLogin:
    def test_successful_pin_login(self, client, db_session):
        user = User(
            email="pin@test.com",
            password_hash=get_password_hash("x"),
            pin_hash=get_pin_hash("9876"),
            role=UserRole.STAFF,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        res = client.post("/api/v1/auth/login/pin", json={"pin": "9876"})
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_wrong_pin_401(self, client, db_session):
        user = User(
            email="pin2@test.com",
            password_hash=get_password_hash("x"),
            pin_hash=get_pin_hash("1111"),
            role=UserRole.STAFF,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        res = client.post("/api/v1/auth/login/pin", json={"pin": "9999"})
        assert res.status_code == 401

    def test_invalid_pin_format_422(self, client):
        # PIN must be 4-8 characters; "ab" is too short → Pydantic returns 422
        res = client.post("/api/v1/auth/login/pin", json={"pin": "ab"})
        assert res.status_code == 422


# ============== Register endpoint ==============

class TestRegister:
    def test_first_user_registration(self, client):
        res = client.post("/api/v1/auth/register", json={
            "email": "first@test.com",
            "password": "strongpass",
            "name": "First Admin",
            "role": "owner",
        })
        assert res.status_code == 201
        assert res.json()["email"] == "first@test.com"

    def test_second_registration_blocked(self, client, test_user):
        res = client.post("/api/v1/auth/register", json={
            "email": "second@test.com",
            "password": "pass",
            "name": "Second",
            "role": "manager",
        })
        assert res.status_code == 403


# ============== /me endpoint ==============

class TestMeEndpoint:
    def test_get_current_user(self, client, auth_headers, test_user):
        res = client.get("/api/v1/auth/me", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == test_user.email

    def test_unauthenticated_rejected(self, client):
        res = client.get("/api/v1/auth/me")
        assert res.status_code in (401, 403)


# ============== PIN management ==============

class TestPinManagement:
    def test_set_pin(self, client, auth_headers):
        res = client.post(
            "/api/v1/auth/me/pin",
            json={"pin_code": "4567"},
            headers=auth_headers,
        )
        assert res.status_code == 200

    def test_clear_pin(self, client, auth_headers):
        res = client.delete("/api/v1/auth/me/pin", headers=auth_headers)
        assert res.status_code == 200

    def test_invalid_pin_rejected(self, client, auth_headers):
        res = client.post(
            "/api/v1/auth/me/pin",
            json={"pin_code": "ab"},
            headers=auth_headers,
        )
        assert res.status_code == 422  # Pydantic validation


# ============== RBAC ==============

class TestRBAC:
    def _make_token(self, user_id, email, role):
        return create_access_token(data={"sub": str(user_id), "email": email, "role": role})

    def test_staff_cannot_create_product(self, client, db_session):
        user = User(
            email="staff@test.com",
            password_hash=get_password_hash("x"),
            role=UserRole.STAFF,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        token = self._make_token(user.id, user.email, "staff")
        res = client.post(
            "/api/v1/products/",
            json={"name": "Test", "barcode": "111"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403

    def test_manager_can_create_product(self, client, db_session):
        user = User(
            email="mgr@test.com",
            password_hash=get_password_hash("x"),
            role=UserRole.MANAGER,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        token = self._make_token(user.id, user.email, "manager")
        res = client.post(
            "/api/v1/products/",
            json={"name": "Beer", "barcode": "222", "cost_price": "1.50"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201

    def test_owner_can_create_product(self, client, db_session):
        user = User(
            email="owner@test.com",
            password_hash=get_password_hash("x"),
            role=UserRole.OWNER,
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()

        token = self._make_token(user.id, user.email, "owner")
        res = client.post(
            "/api/v1/products/",
            json={"name": "Wine", "barcode": "333", "cost_price": "5.00"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 201
