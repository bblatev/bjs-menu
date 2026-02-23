"""Tests for financial services: PLAnalysisService, CashFlowForecastService, accounting integration.

Tests get_profit_loss, get_balance_sheet, forecast_cash_flow with mock data.
Tests empty-state and null-safety.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


API = "/api/v1"


class TestPLAnalysisService:
    """Tests for P&L Analysis Service."""

    def test_pl_analysis_service_instantiation(self, db_session: Session):
        """Test that PLAnalysisService can be instantiated."""
        from app.services.pl_analysis_service import PLAnalysisService
        service = PLAnalysisService(db_session)
        assert service is not None

    def test_cost_data_defaults(self):
        """Test CostData with default values."""
        from app.services.pl_analysis_service import CostData
        cost = CostData()
        assert cost.food == 0
        assert cost.beverage == 0
        assert cost.labor == 0
        assert cost.operating == 0
        assert cost.total == 0

    def test_cost_data_with_values(self):
        """Test CostData total calculation."""
        from app.services.pl_analysis_service import CostData
        cost = CostData(food=1000, beverage=500, labor=2000, operating=300)
        assert cost.total == 3800
        assert cost.food == 1000
        assert cost.beverage == 500

    def test_labor_data_defaults(self):
        """Test LaborData with default values."""
        from app.services.pl_analysis_service import LaborData
        labor = LaborData()
        assert labor.total == 0
        assert labor.regular_hours == 0
        assert labor.overtime_hours == 0
        assert labor.staff_count == 0

    def test_labor_data_with_values(self):
        """Test LaborData with provided values."""
        from app.services.pl_analysis_service import LaborData
        labor = LaborData(total=5000, regular_hours=160, overtime_hours=10, staff_count=5)
        assert labor.total == 5000
        assert labor.regular_hours == 160
        assert labor.overtime_hours == 10
        assert labor.staff_count == 5

    def test_pl_analysis_result(self):
        """Test PLAnalysisResult container."""
        from app.services.pl_analysis_service import PLAnalysisResult
        result = PLAnalysisResult(
            metrics={"revenue": 10000, "costs": 7000, "profit": 3000},
            insights=["Revenue is up 10%"],
            opportunities=[],
            trend_data={"weekly": []}
        )
        assert result.metrics["revenue"] == 10000
        assert len(result.insights) == 1
        assert result.trend_data == {"weekly": []}

    def test_profit_loss_endpoint_empty_state(self, client: TestClient):
        """Test P&L endpoint returns valid response with empty database."""
        response = client.post(f"{API}/missing-features/financial/profit-loss")
        assert response.status_code != 500, f"P&L endpoint returned 500: {response.text}"

    def test_budget_variance_endpoint_empty_state(self, client: TestClient):
        """Test budget variance endpoint with empty database."""
        response = client.get(f"{API}/missing-features/financial/budget-variance")
        assert response.status_code != 500, f"Budget variance endpoint returned 500: {response.text}"

    def test_cash_flow_endpoint_empty_state(self, client: TestClient):
        """Test cash flow endpoint with empty database."""
        response = client.get(f"{API}/missing-features/financial/cash-flow")
        assert response.status_code != 500, f"Cash flow endpoint returned 500: {response.text}"


class TestCashFlowForecastService:
    """Tests for Cash Flow Forecast Service."""

    def test_forecast_cash_flow_default_days(self, db_session: Session):
        """Test cash flow forecast with default 30 days."""
        from app.services.cash_flow_forecast_service import CashFlowForecastService
        result = CashFlowForecastService.forecast_cash_flow(db_session, venue_id=1)
        assert result is not None
        assert "forecast_days" in result
        assert result["forecast_days"] == 30
        assert "projections" in result
        assert len(result["projections"]) == 30

    def test_forecast_cash_flow_custom_days(self, db_session: Session):
        """Test cash flow forecast with custom number of days."""
        from app.services.cash_flow_forecast_service import CashFlowForecastService
        result = CashFlowForecastService.forecast_cash_flow(db_session, venue_id=1, days_ahead=7)
        assert result["forecast_days"] == 7
        assert len(result["projections"]) == 7

    def test_forecast_has_required_fields(self, db_session: Session):
        """Test that forecast result contains all required fields."""
        from app.services.cash_flow_forecast_service import CashFlowForecastService
        result = CashFlowForecastService.forecast_cash_flow(db_session, venue_id=1, days_ahead=7)
        assert "starting_balance" in result
        assert "ending_balance" in result
        assert "total_projected_income" in result
        assert "total_projected_expenses" in result
        assert "net_cash_flow" in result
        assert "venue_id" in result
        assert result["venue_id"] == 1

    def test_forecast_projection_structure(self, db_session: Session):
        """Test individual projection entry structure."""
        from app.services.cash_flow_forecast_service import CashFlowForecastService
        result = CashFlowForecastService.forecast_cash_flow(db_session, venue_id=1, days_ahead=1)
        assert len(result["projections"]) == 1
        proj = result["projections"][0]
        assert "date" in proj
        assert "day" in proj
        assert "projected_income" in proj
        assert "projected_expenses" in proj
        assert "net" in proj
        assert "projected_balance" in proj

    def test_forecast_income_is_positive(self, db_session: Session):
        """Test that projected income is always positive."""
        from app.services.cash_flow_forecast_service import CashFlowForecastService
        result = CashFlowForecastService.forecast_cash_flow(db_session, venue_id=1, days_ahead=14)
        for proj in result["projections"]:
            assert proj["projected_income"] > 0, f"Income should be positive on {proj['date']}"

    def test_forecast_starting_balance(self, db_session: Session):
        """Test that starting balance is set correctly."""
        from app.services.cash_flow_forecast_service import CashFlowForecastService
        result = CashFlowForecastService.forecast_cash_flow(db_session, venue_id=1)
        assert result["starting_balance"] == 50000

    def test_forecast_net_equals_income_minus_expenses(self, db_session: Session):
        """Test that net cash flow equals total income minus total expenses."""
        from app.services.cash_flow_forecast_service import CashFlowForecastService
        result = CashFlowForecastService.forecast_cash_flow(db_session, venue_id=1, days_ahead=7)
        expected_net = result["total_projected_income"] - result["total_projected_expenses"]
        assert abs(result["net_cash_flow"] - expected_net) < 0.01


class TestAccountingIntegrationService:
    """Tests for Accounting Integration Service."""

    def test_service_instantiation(self, db_session: Session):
        """Test that AccountingIntegrationService can be instantiated."""
        from app.services.accounting_integration_service import AccountingIntegrationService
        service = AccountingIntegrationService(db_session)
        assert service is not None
        assert service._integrations == {}
        assert service._pending_transactions == []

    def test_platform_enum(self):
        """Test AccountingPlatform enum values."""
        from app.services.accounting_integration_service import AccountingPlatform
        assert AccountingPlatform.QUICKBOOKS == "quickbooks"
        assert AccountingPlatform.XERO == "xero"
        assert AccountingPlatform.SAGE == "sage"

    def test_transaction_type_enum(self):
        """Test TransactionType enum values."""
        from app.services.accounting_integration_service import TransactionType
        assert TransactionType.SALE == "sale"
        assert TransactionType.REFUND == "refund"
        assert TransactionType.EXPENSE == "expense"

    def test_sync_status_enum(self):
        """Test SyncStatus enum values."""
        from app.services.accounting_integration_service import SyncStatus
        assert SyncStatus.PENDING == "pending"
        assert SyncStatus.SYNCED == "synced"
        assert SyncStatus.FAILED == "failed"

    def test_v3_accounting_profit_loss_empty(self, client: TestClient):
        """Test v3 accounting profit-loss with empty data."""
        response = client.get(f"{API}/v3/accounting/reports/profit-loss")
        assert response.status_code != 500

    def test_v3_accounting_balance_sheet_empty(self, client: TestClient):
        """Test v3 accounting balance-sheet with empty data."""
        response = client.get(f"{API}/v3/accounting/reports/balance-sheet")
        assert response.status_code != 500

    def test_v3_accounting_cash_flow_empty(self, client: TestClient):
        """Test v3 accounting cash-flow with empty data."""
        response = client.get(f"{API}/v3/accounting/reports/cash-flow")
        assert response.status_code != 500

    def test_quickbooks_profit_loss_empty(self, client: TestClient):
        """Test QuickBooks profit-and-loss with no integration."""
        response = client.get(f"{API}/quickbooks/reports/profit-and-loss")
        assert response.status_code != 500

    def test_quickbooks_balance_sheet_empty(self, client: TestClient):
        """Test QuickBooks balance-sheet with no integration."""
        response = client.get(f"{API}/quickbooks/reports/balance-sheet")
        assert response.status_code != 500
