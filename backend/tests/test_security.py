"""Security tests: validators, sanitization, auth enforcement, rate limiting."""

import pytest
from decimal import Decimal

from app.core.sanitize import sanitize_text
from app.models.validators import non_negative, positive, percentage, rating_score


# ============== Sanitization Tests ==============

class TestSanitizeText:
    """Test XSS sanitization utility."""

    def test_script_tag(self):
        result = sanitize_text("<script>alert(1)</script>")
        assert "<script>" not in result
        assert "alert(1)" in result

    def test_img_onerror(self):
        result = sanitize_text('<img src=x onerror=alert(1)>')
        assert "onerror" not in result or "&lt;" in result

    def test_normal_text_preserved(self):
        result = sanitize_text("Normal text here")
        assert result == "Normal text here"

    def test_unicode_preserved(self):
        result = sanitize_text("Без лук, моля")
        assert result == "Без лук, моля"

    def test_none_returns_none(self):
        assert sanitize_text(None) is None

    def test_empty_string(self):
        assert sanitize_text("") == ""

    def test_ampersand_escaped(self):
        result = sanitize_text("Fish & Chips")
        assert "&amp;" in result

    def test_quotes_escaped(self):
        result = sanitize_text('He said "hello"')
        assert "&quot;" in result


# ============== Validator Tests ==============

class TestNonNegative:
    def test_zero_allowed(self):
        assert non_negative("qty", Decimal("0")) == Decimal("0")

    def test_positive_allowed(self):
        assert non_negative("qty", Decimal("10.5")) == Decimal("10.5")

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="cannot be negative"):
            non_negative("qty", Decimal("-1"))

    def test_none_allowed(self):
        assert non_negative("qty", None) is None


class TestPositive:
    def test_positive_allowed(self):
        assert positive("price", Decimal("5.00")) == Decimal("5.00")

    def test_zero_rejected(self):
        with pytest.raises(ValueError, match="must be positive"):
            positive("price", Decimal("0"))

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="must be positive"):
            positive("price", Decimal("-1"))


class TestPercentage:
    def test_valid_percentage(self):
        assert percentage("pct", 50) == 50

    def test_zero_allowed(self):
        assert percentage("pct", 0) == 0

    def test_hundred_allowed(self):
        assert percentage("pct", 100) == 100

    def test_over_hundred_rejected(self):
        with pytest.raises(ValueError, match="between 0 and 100"):
            percentage("pct", 101)

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="between 0 and 100"):
            percentage("pct", -1)


class TestRatingScore:
    def test_valid_rating(self):
        assert rating_score("rating", 4.5) == 4.5

    def test_zero_allowed(self):
        assert rating_score("rating", 0) == 0

    def test_five_allowed(self):
        assert rating_score("rating", 5) == 5

    def test_over_five_rejected(self):
        with pytest.raises(ValueError, match="between 0 and 5"):
            rating_score("rating", 5.1)


# ============== Auth Enforcement Tests ==============

class TestAuthEnforcement:
    """Test that auth middleware blocks unauthenticated requests."""

    def test_health_no_auth_required(self, client):
        res = client.get("/health")
        assert res.status_code == 200

    def test_public_paths_accessible(self, client):
        """Public paths should not require auth."""
        public_paths = ["/health", "/health/ready"]
        for path in public_paths:
            res = client.get(path)
            assert res.status_code in (200, 307), f"{path} returned {res.status_code}"

    def test_api_post_requires_auth(self, client):
        """POST endpoints should require auth."""
        res = client.post(
            "/api/v1/products/",
            json={"name": "test", "barcode": "123"},
        )
        assert res.status_code == 401

    def test_api_delete_requires_auth(self, client):
        """DELETE endpoints should require auth."""
        res = client.delete("/api/v1/products/1")
        assert res.status_code == 401

    def test_api_with_auth_passes(self, client, auth_headers):
        """Authenticated requests should pass the auth middleware."""
        res = client.get("/api/v1/products/", headers=auth_headers)
        # Should get 200 (or possibly 404/500), but NOT 401
        assert res.status_code != 401


# ============== CSP Header Tests ==============

class TestSecurityHeaders:
    def test_csp_header_present(self, client):
        res = client.get("/health")
        assert "content-security-policy" in res.headers

    def test_x_frame_options(self, client):
        res = client.get("/health")
        assert res.headers.get("x-frame-options") == "DENY"

    def test_x_content_type_options(self, client):
        res = client.get("/health")
        assert res.headers.get("x-content-type-options") == "nosniff"

    def test_referrer_policy(self, client):
        res = client.get("/health")
        assert "strict-origin" in res.headers.get("referrer-policy", "")
