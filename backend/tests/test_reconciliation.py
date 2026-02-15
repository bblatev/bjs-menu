"""Tests for reconciliation, reorder, and export services."""

from decimal import Decimal
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.inventory import InventorySession, InventoryLine, SessionStatus, CountMethod
from app.models.stock import StockOnHand
from app.models.reconciliation import (
    ReconciliationResult,
    ReorderProposal,
    SupplierOrderDraft,
    DeltaSeverity,
    OrderDraftStatus,
)
from app.services.reconciliation_service import ReconciliationService, ReconciliationConfig
from app.services.reorder_service import ReorderService, ReorderConfig
from app.services.export_service import ExportService
from app.services.sku_mapping_service import SKUMappingService, MatchMethod


class TestReconciliationService:
    """Test reconciliation service."""

    @pytest.fixture
    def inventory_session(self, db_session, test_location, test_user):
        """Create a committed inventory session."""
        session = InventorySession(
            location_id=test_location.id,
            status=SessionStatus.COMMITTED,
            created_by=test_user.id,
            committed_at=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    @pytest.fixture
    def inventory_line(self, db_session, inventory_session, test_product):
        """Create an inventory line with counted qty."""
        line = InventoryLine(
            session_id=inventory_session.id,
            product_id=test_product.id,
            counted_qty=Decimal("45"),
            method=CountMethod.MANUAL,
        )
        db_session.add(line)
        db_session.commit()
        db_session.refresh(line)
        return line

    @pytest.fixture
    def stock_on_hand(self, db_session, test_location, test_product):
        """Create stock on hand record."""
        stock = StockOnHand(
            location_id=test_location.id,
            product_id=test_product.id,
            qty=Decimal("50"),
        )
        db_session.add(stock)
        db_session.commit()
        db_session.refresh(stock)
        return stock

    def test_reconcile_session_ok(
        self, db_session, inventory_session, inventory_line, stock_on_hand
    ):
        """Test reconciliation with small delta (OK severity)."""
        # Update line to have small delta
        inventory_line.counted_qty = Decimal("49")  # Expected is 50, delta is 1
        db_session.commit()

        config = ReconciliationConfig(
            critical_threshold_qty=Decimal("5"),
            warning_threshold_qty=Decimal("2"),
        )
        service = ReconciliationService(db_session, config)
        results = service.reconcile_session(inventory_session.id)

        assert len(results) == 1
        result = results[0]
        assert result.severity == DeltaSeverity.OK
        assert result.delta_qty == Decimal("1")  # 50 - 49

    def test_reconcile_session_warning(
        self, db_session, inventory_session, inventory_line, stock_on_hand
    ):
        """Test reconciliation with medium delta (WARNING severity)."""
        # Update line to have medium delta
        inventory_line.counted_qty = Decimal("47")  # Delta of 3
        db_session.commit()

        config = ReconciliationConfig(
            critical_threshold_qty=Decimal("5"),
            warning_threshold_qty=Decimal("2"),
        )
        service = ReconciliationService(db_session, config)
        results = service.reconcile_session(inventory_session.id)

        assert len(results) == 1
        result = results[0]
        assert result.severity == DeltaSeverity.WARNING

    def test_reconcile_session_critical(
        self, db_session, inventory_session, inventory_line, stock_on_hand
    ):
        """Test reconciliation with large delta (CRITICAL severity)."""
        # Update line to have large delta
        inventory_line.counted_qty = Decimal("40")  # Delta of 10
        db_session.commit()

        config = ReconciliationConfig(
            critical_threshold_qty=Decimal("5"),
        )
        service = ReconciliationService(db_session, config)
        results = service.reconcile_session(inventory_session.id)

        assert len(results) == 1
        result = results[0]
        assert result.severity == DeltaSeverity.CRITICAL

    def test_reconcile_calculates_delta_value(
        self, db_session, inventory_session, inventory_line, stock_on_hand, test_product
    ):
        """Test that delta value is calculated from cost price."""
        inventory_line.counted_qty = Decimal("40")  # Delta of 10
        db_session.commit()

        service = ReconciliationService(db_session)
        results = service.reconcile_session(inventory_session.id)

        result = results[0]
        # Delta value = 10 units * $1.50 cost = $15.00
        assert result.delta_value == Decimal("15.00")

    def test_get_reconciliation_summary(
        self, db_session, inventory_session, inventory_line, stock_on_hand
    ):
        """Test getting reconciliation summary."""
        service = ReconciliationService(db_session)
        service.reconcile_session(inventory_session.id)

        summary = service.get_reconciliation_summary(inventory_session.id)

        assert summary["session_id"] == inventory_session.id
        assert summary["total_products"] == 1
        assert "results" in summary


class TestReorderService:
    """Test reorder service."""

    @pytest.fixture
    def inventory_session(self, db_session, test_location, test_user):
        """Create an inventory session."""
        session = InventorySession(
            location_id=test_location.id,
            status=SessionStatus.COMMITTED,
            created_by=test_user.id,
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        return session

    @pytest.fixture
    def low_stock_line(self, db_session, inventory_session, test_product):
        """Create an inventory line with low stock."""
        line = InventoryLine(
            session_id=inventory_session.id,
            product_id=test_product.id,
            counted_qty=Decimal("5"),  # Low stock
            method=CountMethod.MANUAL,
        )
        db_session.add(line)
        db_session.commit()
        return line

    def test_generate_proposals(
        self, db_session, inventory_session, low_stock_line, test_product
    ):
        """Test generating reorder proposals."""
        # Set target stock
        test_product.target_stock = Decimal("50")
        test_product.par_level = Decimal("50")
        db_session.commit()

        config = ReorderConfig(
            use_par_level=True,
            round_to_case=False,
        )
        service = ReorderService(db_session, config)
        proposals = service.generate_proposals(inventory_session.id)

        assert len(proposals) == 1
        proposal = proposals[0]
        assert proposal.product_id == test_product.id
        assert proposal.current_stock == Decimal("5")
        assert proposal.target_stock == Decimal("50")
        assert proposal.recommended_qty == Decimal("45")  # 50 - 5

    def test_round_to_case(
        self, db_session, inventory_session, low_stock_line, test_product
    ):
        """Test that quantities are rounded to case pack."""
        test_product.target_stock = Decimal("50")
        test_product.par_level = Decimal("50")
        test_product.pack_size = 24  # Case of 24
        db_session.commit()

        config = ReorderConfig(
            use_par_level=True,
            round_to_case=True,
        )
        service = ReorderService(db_session, config)
        proposals = service.generate_proposals(inventory_session.id)

        proposal = proposals[0]
        # Need 45, round up to nearest 24 = 48
        assert proposal.rounded_qty == Decimal("48")

    def test_get_proposals_by_supplier(
        self, db_session, inventory_session, low_stock_line, test_product, test_supplier
    ):
        """Test grouping proposals by supplier."""
        test_product.target_stock = Decimal("50")
        test_product.par_level = Decimal("50")
        db_session.commit()

        service = ReorderService(db_session)
        service.generate_proposals(inventory_session.id)

        by_supplier = service.get_proposals_by_supplier(inventory_session.id)

        assert test_supplier.id in by_supplier
        assert by_supplier[test_supplier.id]["supplier_name"] == test_supplier.name
        assert len(by_supplier[test_supplier.id]["proposals"]) == 1

    def test_update_proposal(
        self, db_session, inventory_session, low_stock_line, test_product
    ):
        """Test updating a proposal with user override."""
        test_product.target_stock = Decimal("50")
        test_product.par_level = Decimal("50")
        db_session.commit()

        service = ReorderService(db_session)
        proposals = service.generate_proposals(inventory_session.id)
        proposal = proposals[0]

        # User overrides quantity
        updated = service.update_proposal(
            proposal_id=proposal.id,
            user_qty=Decimal("60"),
        )

        assert updated.user_qty == Decimal("60")


class TestExportService:
    """Test export service."""

    @pytest.fixture
    def session_with_proposals(
        self, db_session, test_location, test_user, test_product, test_supplier
    ):
        """Create session with reorder proposals."""
        # Create session
        session = InventorySession(
            location_id=test_location.id,
            status=SessionStatus.COMMITTED,
            created_by=test_user.id,
        )
        db_session.add(session)
        db_session.flush()

        # Create inventory line
        line = InventoryLine(
            session_id=session.id,
            product_id=test_product.id,
            counted_qty=Decimal("5"),
            method=CountMethod.MANUAL,
        )
        db_session.add(line)

        # Create proposal
        proposal = ReorderProposal(
            session_id=session.id,
            product_id=test_product.id,
            supplier_id=test_supplier.id,
            current_stock=Decimal("5"),
            target_stock=Decimal("50"),
            in_transit=Decimal("0"),
            recommended_qty=Decimal("45"),
            rounded_qty=Decimal("48"),
            pack_size=24,
            unit_cost=test_product.cost_price,
            included=True,
        )
        db_session.add(proposal)
        db_session.commit()
        db_session.refresh(session)

        return session

    def test_create_order_drafts(
        self, db_session, session_with_proposals, test_supplier
    ):
        """Test creating order drafts from proposals."""
        service = ExportService(db_session)
        drafts = service.create_order_drafts(session_with_proposals.id)

        assert len(drafts) == 1
        draft = drafts[0]
        assert draft.supplier_id == test_supplier.id
        assert draft.status == OrderDraftStatus.DRAFT
        assert draft.line_count == 1

    def test_export_to_csv(
        self, db_session, session_with_proposals
    ):
        """Test exporting draft to CSV."""
        service = ExportService(db_session)
        drafts = service.create_order_drafts(session_with_proposals.id)
        draft = drafts[0]

        csv_path = service.export_to_csv(draft.id)

        assert csv_path.endswith(".csv")
        assert draft.exported_csv_path == csv_path
        assert draft.status == OrderDraftStatus.EXPORTED

    def test_generate_email_template(
        self, db_session, session_with_proposals, test_supplier
    ):
        """Test generating email template."""
        service = ExportService(db_session)
        drafts = service.create_order_drafts(session_with_proposals.id)
        draft = drafts[0]

        template = service.generate_email_template(draft.id, "Test Bar")

        assert template["supplier_name"] == test_supplier.name
        assert "Purchase Order" in template["subject"]
        assert "Test Bar" in template["body"]

    def test_generate_whatsapp_text(
        self, db_session, session_with_proposals
    ):
        """Test generating WhatsApp text."""
        service = ExportService(db_session)
        drafts = service.create_order_drafts(session_with_proposals.id)
        draft = drafts[0]

        text = service.generate_whatsapp_text(draft.id)

        assert "PURCHASE ORDER" in text
        assert "Items:" in text


class TestSKUMappingService:
    """Test SKU mapping service."""

    def test_match_by_barcode(self, db_session, test_product):
        """Test matching by exact barcode."""
        service = SKUMappingService(db_session)
        result = service.match_by_barcode(test_product.barcode)

        assert result is not None
        assert result.product_id == test_product.id
        assert result.method == MatchMethod.BARCODE
        assert result.confidence == 1.0

    def test_match_by_barcode_not_found(self, db_session):
        """Test barcode match returns None when not found."""
        service = SKUMappingService(db_session)
        result = service.match_by_barcode("0000000000000")

        assert result is None

    def test_match_by_fuzzy_name(self, db_session, test_product):
        """Test fuzzy name matching."""
        service = SKUMappingService(db_session)
        # Search with partial name
        result = service.match_by_fuzzy_name("Test")

        assert result is not None
        assert result.product_id == test_product.id
        assert result.method == MatchMethod.FUZZY_NAME
        # Partial matches have lower confidence (0.4-0.5 for single word matches)
        assert result.confidence > 0.4

    def test_match_product_priority(self, db_session, test_product):
        """Test that barcode takes priority over fuzzy match."""
        service = SKUMappingService(db_session)

        # Both barcode and name provided
        result = service.match_product(
            barcode=test_product.barcode,
            name="Something Different",
        )

        # Should match by barcode with 100% confidence
        assert result.method == MatchMethod.BARCODE
        assert result.confidence == 1.0

    def test_search_products(self, db_session, test_product):
        """Test product search returns sorted results."""
        service = SKUMappingService(db_session)
        results = service.search_products("Test", limit=10)

        assert len(results) >= 1
        assert results[0]["product_id"] == test_product.id
        assert "confidence" in results[0]

    def test_match_product_not_found(self, db_session):
        """Test match_product returns NOT_FOUND when nothing matches."""
        service = SKUMappingService(db_session)
        result = service.match_product(
            barcode="0000000000000",
            name="xyznonexistent123",
        )

        assert result.method == MatchMethod.NOT_FOUND
        assert result.product_id is None


class TestReconciliationAPI:
    """Test reconciliation API endpoints."""

    @pytest.fixture
    def committed_session(self, db_session, test_location, test_user, test_product):
        """Create a committed session with lines and stock."""
        # Create session
        session = InventorySession(
            location_id=test_location.id,
            status=SessionStatus.COMMITTED,
            created_by=test_user.id,
            committed_at=datetime.now(timezone.utc),
        )
        db_session.add(session)
        db_session.flush()

        # Add line
        line = InventoryLine(
            session_id=session.id,
            product_id=test_product.id,
            counted_qty=Decimal("40"),
            method=CountMethod.MANUAL,
        )
        db_session.add(line)

        # Add expected stock
        stock = StockOnHand(
            location_id=test_location.id,
            product_id=test_product.id,
            qty=Decimal("50"),
        )
        db_session.add(stock)

        db_session.commit()
        db_session.refresh(session)
        return session

    def test_run_reconciliation_endpoint(
        self, client, auth_headers, committed_session
    ):
        """Test POST /reconciliation/reconcile endpoint."""
        response = client.post(
            "/api/v1/reconciliation/reconcile",
            json={
                "session_id": committed_session.id,
                "expected_source": "pos_stock",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == committed_session.id
        assert data["total_products"] == 1
        assert len(data["results"]) == 1

    def test_get_reconciliation_results_endpoint(
        self, client, auth_headers, committed_session, db_session
    ):
        """Test GET /reconciliation/sessions/{id}/reconciliation endpoint."""
        # First run reconciliation
        service = ReconciliationService(db_session)
        service.reconcile_session(committed_session.id)
        db_session.commit()

        response = client.get(
            f"/api/v1/reconciliation/sessions/{committed_session.id}/reconciliation",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_products"] == 1

    def test_smart_search_endpoint(
        self, client, auth_headers, test_product
    ):
        """Test GET /products/search/smart endpoint."""
        response = client.get(
            "/api/v1/products/search/smart",
            params={"q": "Test"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        assert any(r["product_id"] == test_product.id for r in data["results"])

    def test_match_product_endpoint(
        self, client, auth_headers, test_product
    ):
        """Test POST /products/match endpoint."""
        response = client.post(
            "/api/v1/products/match",
            params={"barcode": test_product.barcode},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == test_product.id
        assert data["match_method"] == "barcode"
        assert data["confidence"] == 1.0
