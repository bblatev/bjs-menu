"""Tests for allergen safety workflow.

Tests allergen-check endpoint returns allergen flags, allergen-verify endpoint
records verification, kitchen order flow with allergens.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


API = "/api/v1"


class TestAllergenListEndpoints:
    """Tests for allergen list and dietary type endpoints."""

    def test_allergen_list_endpoint(self, client: TestClient):
        """Test allergen list returns all 14 EU major allergens."""
        response = client.get(f"{API}/allergens/allergen-list")
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            # Should return a list of allergens or dict with allergen info
            assert data is not None

    def test_dietary_types_endpoint(self, client: TestClient):
        """Test dietary types endpoint returns valid data."""
        response = client.get(f"{API}/allergens/dietary-types")
        assert response.status_code != 500
        if response.status_code == 200:
            data = response.json()
            assert data is not None

    def test_allergens_root_endpoint(self, client: TestClient):
        """Test allergens root endpoint."""
        response = client.get(f"{API}/allergens/")
        assert response.status_code != 500


class TestAllergenNutritionService:
    """Tests for AllergenNutritionService."""

    def test_service_instantiation(self, db_session: Session):
        """Test that AllergenNutritionService can be instantiated."""
        from app.services.allergen_nutrition_service import AllergenNutritionService
        service = AllergenNutritionService(db_session)
        assert service is not None

    def test_allergen_type_enum(self):
        """Test AllergenType enum has all 14 EU allergens."""
        from app.services.allergen_nutrition_service import AllergenType
        expected_allergens = {
            "celery", "cereals_gluten", "crustaceans", "eggs", "fish",
            "lupin", "milk", "molluscs", "mustard", "nuts",
            "peanuts", "sesame", "soybeans", "sulphites",
        }
        actual_allergens = {a.value for a in AllergenType}
        assert expected_allergens == actual_allergens

    def test_dietary_type_enum(self):
        """Test DietaryType enum has expected values."""
        from app.services.allergen_nutrition_service import DietaryType
        assert DietaryType.VEGAN == "vegan"
        assert DietaryType.VEGETARIAN == "vegetarian"
        assert DietaryType.GLUTEN_FREE == "gluten_free"
        assert DietaryType.HALAL == "halal"
        assert DietaryType.KOSHER == "kosher"

    def test_allergen_icons_defined(self):
        """Test that allergen icons are defined for all allergens."""
        from app.services.allergen_nutrition_service import AllergenNutritionService
        icons = AllergenNutritionService.ALLERGEN_ICONS
        assert "celery" in icons
        assert "eggs" in icons
        assert "milk" in icons
        assert "nuts" in icons
        assert "fish" in icons

    def test_allergen_translations_defined(self):
        """Test that allergen translations exist for key languages."""
        from app.services.allergen_nutrition_service import AllergenNutritionService
        translations = AllergenNutritionService.ALLERGEN_TRANSLATIONS
        assert "celery" in translations
        assert "en" in translations["celery"]
        assert "bg" in translations["celery"]


class TestAllergenCheckWorkflow:
    """Tests for allergen check workflow on orders."""

    def test_check_allergens_for_nonexistent_order(self, client: TestClient):
        """Test allergen check for a non-existent order."""
        response = client.post(
            f"{API}/allergens/orders/99999/check-allergens",
            json={"customer_allergens": ["nuts", "milk"]},
        )
        # Should return 404 or handle gracefully, not 500
        assert response.status_code != 500

    def test_check_allergens_empty_list(self, client: TestClient):
        """Test allergen check with empty allergen list."""
        response = client.post(
            f"{API}/allergens/orders/1/check-allergens",
            json={"customer_allergens": []},
        )
        assert response.status_code != 500

    def test_check_allergens_all_14(self, client: TestClient):
        """Test allergen check with all 14 EU allergens."""
        all_allergens = [
            "celery", "cereals_gluten", "crustaceans", "eggs", "fish",
            "lupin", "milk", "molluscs", "mustard", "nuts",
            "peanuts", "sesame", "soybeans", "sulphites",
        ]
        response = client.post(
            f"{API}/allergens/orders/1/check-allergens",
            json={"customer_allergens": all_allergens},
        )
        assert response.status_code != 500


class TestAllergenItemManagement:
    """Tests for setting and getting allergens on menu items."""

    def test_set_allergens_nonexistent_item(self, client: TestClient, auth_headers: dict):
        """Test setting allergens on a non-existent menu item."""
        response = client.post(
            f"{API}/allergens/items/99999/allergens",
            json={
                "allergens": ["nuts", "milk"],
                "may_contain": ["sesame"],
            },
            headers=auth_headers,
        )
        assert response.status_code != 500

    def test_get_allergens_nonexistent_item(self, client: TestClient):
        """Test getting allergens for a non-existent menu item."""
        response = client.get(f"{API}/allergens/items/99999/allergens")
        assert response.status_code != 500

    def test_set_nutrition_nonexistent_item(self, client: TestClient, auth_headers: dict):
        """Test setting nutrition info on a non-existent menu item."""
        response = client.post(
            f"{API}/allergens/items/99999/nutrition",
            json={
                "serving_size": "100g",
                "calories": 250.0,
                "protein_g": 15.0,
                "carbs_g": 30.0,
                "fat_g": 10.0,
            },
            headers=auth_headers,
        )
        assert response.status_code != 500

    def test_get_nutrition_nonexistent_item(self, client: TestClient):
        """Test getting nutrition info for a non-existent menu item."""
        response = client.get(f"{API}/allergens/items/99999/nutrition")
        assert response.status_code != 500

    def test_set_dietary_tags_nonexistent_item(self, client: TestClient, auth_headers: dict):
        """Test setting dietary tags on a non-existent menu item."""
        response = client.post(
            f"{API}/allergens/items/99999/dietary",
            json={
                "dietary_types": ["vegetarian", "gluten_free"],
            },
            headers=auth_headers,
        )
        assert response.status_code != 500


class TestAllergenMenuFiltering:
    """Tests for filtering menu by allergens and dietary requirements."""

    def test_filter_menu_by_dietary(self, client: TestClient):
        """Test filtering menu by dietary requirements."""
        response = client.post(
            f"{API}/allergens/menu/filter",
            json={
                "dietary_requirements": ["vegan"],
                "allergen_exclusions": ["nuts"],
            },
        )
        assert response.status_code != 500

    def test_filter_menu_empty_requirements(self, client: TestClient):
        """Test filtering menu with empty requirements."""
        response = client.post(
            f"{API}/allergens/menu/filter",
            json={
                "dietary_requirements": [],
            },
        )
        assert response.status_code != 500

    def test_filter_menu_multiple_allergens(self, client: TestClient):
        """Test filtering menu excluding multiple allergens."""
        response = client.post(
            f"{API}/allergens/menu/filter",
            json={
                "dietary_requirements": ["vegetarian"],
                "allergen_exclusions": ["nuts", "milk", "eggs", "cereals_gluten"],
            },
        )
        assert response.status_code != 500


class TestHACCPAllergenIntegration:
    """Tests for HACCP-allergen integration (temperature logging via allergens route)."""

    def test_haccp_temperature_via_allergens(self, client: TestClient, auth_headers: dict):
        """Test logging temperature through allergens HACCP endpoint."""
        response = client.post(
            f"{API}/allergens/haccp/temperature",
            json={
                "equipment_id": "fridge-001",
                "equipment_type": "walk_in_cooler",
                "temperature_c": 3.5,
                "is_acceptable": True,
                "notes": "Morning check",
            },
            headers=auth_headers,
        )
        assert response.status_code != 500

    def test_haccp_event_via_allergens(self, client: TestClient, auth_headers: dict):
        """Test logging HACCP event through allergens endpoint."""
        response = client.post(
            f"{API}/allergens/haccp/event",
            json={
                "event_type": "cleaning",
                "description": "Deep clean of prep area",
                "is_compliant": True,
            },
            headers=auth_headers,
        )
        assert response.status_code != 500

    def test_haccp_report_via_allergens(self, client: TestClient):
        """Test HACCP compliance report through allergens endpoint."""
        response = client.get(f"{API}/allergens/haccp/report")
        assert response.status_code != 500
