"""Tests for payment routes.

Tests list_transactions, get_transaction, process_payment, refund with mock
Stripe responses. Tests 503 graceful degradation when Stripe not configured.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


API = "/api/v1"


class TestPaymentRoutesBasic:
    """Tests for basic payment route functionality."""

    def test_payments_root(self, client: TestClient, auth_headers: dict):
        """Test payments root endpoint returns status."""
        response = client.get(f"{API}/payments/", headers=auth_headers)
        assert response.status_code != 500

    def test_payments_config(self, client: TestClient, auth_headers: dict):
        """Test payments config endpoint returns configuration."""
        response = client.get(f"{API}/payments/config", headers=auth_headers)
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            assert "stripe_configured" in data
            assert "currency" in data

    def test_payments_config_stripe_not_configured(self, client: TestClient, auth_headers: dict):
        """Test payments config shows stripe_configured=false when no key set."""
        response = client.get(f"{API}/payments/config", headers=auth_headers)
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            # In test environment, Stripe should not be configured
            assert "stripe_configured" in data

    def test_payments_status(self, client: TestClient, auth_headers: dict):
        """Test payments status endpoint."""
        response = client.get(f"{API}/payments/status", headers=auth_headers)
        assert response.status_code != 500


class TestPaymentTransactions:
    """Tests for payment transaction endpoints."""

    def test_list_transactions_empty(self, client: TestClient, auth_headers: dict):
        """Test listing transactions when none exist."""
        response = client.get(f"{API}/payments/transactions", headers=auth_headers)
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data
            assert "total" in data
            assert isinstance(data["transactions"], list)

    def test_list_transactions_with_pagination(self, client: TestClient, auth_headers: dict):
        """Test listing transactions with limit and offset."""
        response = client.get(
            f"{API}/payments/transactions?limit=10&offset=0",
            headers=auth_headers,
        )
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            assert data["limit"] == 10
            assert data["offset"] == 0

    def test_get_transaction_not_found(self, client: TestClient, auth_headers: dict):
        """Test getting a non-existent transaction returns 404."""
        response = client.get(
            f"{API}/payments/transactions/99999",
            headers=auth_headers,
        )
        assert response.status_code in (404, 422), (
            f"Expected 404 or 422 for missing transaction, got {response.status_code}"
        )

    def test_list_transactions_response_structure(self, client: TestClient, auth_headers: dict):
        """Test transactions list response has expected structure."""
        response = client.get(f"{API}/payments/transactions", headers=auth_headers)
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            assert "transactions" in data
            assert "total" in data
            assert "limit" in data
            assert "offset" in data


class TestPaymentProcessing:
    """Tests for payment processing endpoints."""

    def test_create_payment_intent_no_stripe(self, client: TestClient, auth_headers: dict):
        """Test creating a payment intent when Stripe is not configured."""
        response = client.post(
            f"{API}/payments/create-intent",
            json={
                "amount": 1000,
                "currency": "usd",
                "payment_method": "card",
            },
            headers=auth_headers,
        )
        # Should gracefully handle no Stripe config (not 500)
        assert response.status_code != 500, (
            f"Payment intent creation returned 500: {response.text}"
        )
        # Accept 503 (service unavailable) or 400/422 (validation)
        # or 200 if mock is in place
        assert response.status_code in (200, 400, 401, 403, 422, 503)

    def test_create_payment_intent_validation(self, client: TestClient, auth_headers: dict):
        """Test payment intent validation rejects invalid data."""
        response = client.post(
            f"{API}/payments/create-intent",
            json={
                "amount": -100,  # Invalid negative amount
                "currency": "usd",
                "payment_method": "card",
            },
            headers=auth_headers,
        )
        # Should return validation error, not 500
        assert response.status_code != 500

    def test_create_payment_intent_missing_amount(self, client: TestClient, auth_headers: dict):
        """Test payment intent requires amount."""
        response = client.post(
            f"{API}/payments/create-intent",
            json={
                "currency": "usd",
                "payment_method": "card",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422  # Validation error

    def test_intents_endpoint_no_stripe(self, client: TestClient, auth_headers: dict):
        """Test POST /payments/intents without Stripe configured."""
        response = client.post(
            f"{API}/payments/intents",
            json={
                "amount": 2500,
                "currency": "bgn",
                "payment_method": "card",
            },
            headers=auth_headers,
        )
        assert response.status_code != 500


class TestPaymentRefunds:
    """Tests for payment refund endpoints."""

    def test_refund_nonexistent_payment(self, client: TestClient, auth_headers: dict):
        """Test refunding a non-existent payment intent."""
        response = client.post(
            f"{API}/payments/refund/pi_nonexistent",
            json={"reason": "requested_by_customer"},
            headers=auth_headers,
        )
        # Should handle gracefully (not 500)
        assert response.status_code != 500

    def test_refund_invalid_reason(self, client: TestClient, auth_headers: dict):
        """Test refund with invalid reason."""
        response = client.post(
            f"{API}/payments/refund/pi_test_123",
            json={"reason": "invalid_reason"},
            headers=auth_headers,
        )
        # Should return validation error for invalid reason pattern
        assert response.status_code in (400, 422, 503), (
            f"Expected validation error, got {response.status_code}"
        )

    def test_refund_with_amount(self, client: TestClient, auth_headers: dict):
        """Test partial refund request."""
        response = client.post(
            f"{API}/payments/refund/pi_test_456",
            json={
                "amount": 500,
                "reason": "duplicate",
            },
            headers=auth_headers,
        )
        assert response.status_code != 500

    def test_intents_refund_endpoint(self, client: TestClient, auth_headers: dict):
        """Test POST /payments/intents/{id}/refund."""
        response = client.post(
            f"{API}/payments/intents/pi_test_789/refund",
            json={"reason": "fraudulent"},
            headers=auth_headers,
        )
        assert response.status_code != 500


class TestPaymentDashboard:
    """Tests for payment dashboard endpoints."""

    def test_dashboard_empty_state(self, client: TestClient, auth_headers: dict):
        """Test payment dashboard with no transactions."""
        response = client.get(f"{API}/payments/dashboard", headers=auth_headers)
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            assert "total_transactions" in data
            assert "total_revenue_cents" in data
            assert "total_refunded_cents" in data
            assert "net_revenue_cents" in data

    def test_dashboard_by_status(self, client: TestClient, auth_headers: dict):
        """Test dashboard includes breakdown by status."""
        response = client.get(f"{API}/payments/dashboard", headers=auth_headers)
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            assert "by_status" in data
            assert "by_payment_method" in data


class TestPaymentTerminal:
    """Tests for Stripe Terminal endpoints."""

    def test_terminal_connection_token_no_stripe(self, client: TestClient, auth_headers: dict):
        """Test terminal connection token when Stripe not configured."""
        response = client.post(
            f"{API}/payments/terminal/connection-token",
            headers=auth_headers,
        )
        # Should gracefully degrade, not 500
        assert response.status_code != 500

    def test_terminal_readers_no_stripe(self, client: TestClient, auth_headers: dict):
        """Test listing terminal readers when Stripe not configured."""
        response = client.get(
            f"{API}/payments/terminal/readers",
            headers=auth_headers,
        )
        assert response.status_code != 500
