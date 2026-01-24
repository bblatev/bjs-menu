"""POS Adapter - Clean interface for fetching data from POS systems.

This adapter provides a unified interface for:
- Products/SKUs with supplier info
- Current stock by location
- Sales data by date range
- In-transit/pending orders

The adapter can be configured to work with different POS databases
via environment variables and a mapping configuration file.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
import os
import json
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


# ============== Data Transfer Objects ==============

@dataclass
class POSProduct:
    """Product/SKU from POS system."""
    id: int
    barcode: Optional[str]
    name: str
    brand: Optional[str] = None
    category: Optional[str] = None
    bottle_size_ml: Optional[int] = None
    case_pack: int = 1
    supplier_id: Optional[int] = None
    supplier_name: Optional[str] = None
    cost_price: Optional[Decimal] = None
    sell_price: Optional[Decimal] = None
    sku: Optional[str] = None
    ai_label: Optional[str] = None
    active: bool = True
    par_level: Optional[Decimal] = None
    min_stock: Optional[Decimal] = None
    lead_time_days: int = 1
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class POSSupplier:
    """Supplier from POS system."""
    id: int
    name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    min_order_value: Optional[Decimal] = None
    min_order_qty: Optional[int] = None
    delivery_days: Optional[List[str]] = None  # e.g., ["Mon", "Wed", "Fri"]
    lead_time_days: int = 1
    notes: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class POSStockLevel:
    """Current stock level for a product at a location."""
    product_id: int
    location_id: int
    location_name: str
    qty_on_hand: Decimal
    qty_reserved: Decimal = Decimal("0")
    qty_available: Decimal = Decimal("0")  # on_hand - reserved
    last_count_date: Optional[datetime] = None
    last_movement_date: Optional[datetime] = None


@dataclass
class POSSalesAggregate:
    """Aggregated sales data for a product over a period."""
    product_id: int
    product_name: str
    location_id: Optional[int]
    period_start: date
    period_end: date
    total_qty_sold: Decimal
    total_revenue: Optional[Decimal] = None
    num_transactions: int = 0
    avg_daily_qty: Optional[Decimal] = None


@dataclass
class POSInTransitOrder:
    """Pending/in-transit order from supplier."""
    order_id: int
    supplier_id: int
    supplier_name: str
    product_id: int
    product_name: str
    qty_ordered: Decimal
    order_date: datetime
    qty_received: Decimal = Decimal("0")
    qty_pending: Decimal = Decimal("0")  # ordered - received
    expected_delivery: Optional[datetime] = None
    status: str = "pending"  # pending, partial, received, cancelled


# ============== Abstract Adapter Interface ==============

class POSAdapterBase(ABC):
    """Abstract base class for POS adapters."""

    @abstractmethod
    def get_products(
        self,
        active_only: bool = True,
        supplier_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[POSProduct]:
        """Fetch products from POS."""
        pass

    @abstractmethod
    def get_product_by_barcode(self, barcode: str) -> Optional[POSProduct]:
        """Fetch a single product by barcode."""
        pass

    @abstractmethod
    def get_product_by_id(self, product_id: int) -> Optional[POSProduct]:
        """Fetch a single product by ID."""
        pass

    @abstractmethod
    def get_suppliers(self, active_only: bool = True) -> List[POSSupplier]:
        """Fetch suppliers from POS."""
        pass

    @abstractmethod
    def get_stock_levels(
        self,
        location_id: Optional[int] = None,
        product_ids: Optional[List[int]] = None
    ) -> List[POSStockLevel]:
        """Fetch current stock levels."""
        pass

    @abstractmethod
    def get_sales_aggregate(
        self,
        start_date: date,
        end_date: date,
        location_id: Optional[int] = None,
        product_ids: Optional[List[int]] = None
    ) -> List[POSSalesAggregate]:
        """Fetch aggregated sales data for a period."""
        pass

    @abstractmethod
    def get_in_transit_orders(
        self,
        supplier_id: Optional[int] = None,
        product_ids: Optional[List[int]] = None
    ) -> List[POSInTransitOrder]:
        """Fetch pending/in-transit orders."""
        pass


# ============== Local Database Adapter ==============

class LocalDatabaseAdapter(POSAdapterBase):
    """Adapter that reads from the local inventory database.

    This is the default implementation that uses the same database
    as the inventory system. For external POS systems, create a
    separate adapter class.
    """

    def __init__(self, db_session: Session):
        """Initialize with a database session."""
        self.db = db_session

    def get_products(
        self,
        active_only: bool = True,
        supplier_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[POSProduct]:
        """Fetch products from local database."""
        from app.models import Product, Supplier

        query = self.db.query(Product)

        if active_only:
            query = query.filter(Product.active == True)
        if supplier_id:
            query = query.filter(Product.supplier_id == supplier_id)
        # Note: category field not in current schema, would need to add

        products = query.all()

        result = []
        for p in products:
            supplier_name = None
            if p.supplier:
                supplier_name = p.supplier.name

            result.append(POSProduct(
                id=p.id,
                barcode=p.barcode,
                name=p.name,
                sku=p.sku,
                case_pack=p.pack_size or 1,
                supplier_id=p.supplier_id,
                supplier_name=supplier_name,
                cost_price=p.cost_price,
                ai_label=p.ai_label,
                active=p.active,
                par_level=p.target_stock,
                min_stock=p.min_stock,
                lead_time_days=p.lead_time_days or 1,
            ))

        return result

    def get_product_by_barcode(self, barcode: str) -> Optional[POSProduct]:
        """Fetch a single product by barcode."""
        from app.models import Product

        p = self.db.query(Product).filter(Product.barcode == barcode).first()
        if not p:
            return None

        supplier_name = None
        if p.supplier:
            supplier_name = p.supplier.name

        return POSProduct(
            id=p.id,
            barcode=p.barcode,
            name=p.name,
            sku=p.sku,
            case_pack=p.pack_size or 1,
            supplier_id=p.supplier_id,
            supplier_name=supplier_name,
            cost_price=p.cost_price,
            ai_label=p.ai_label,
            active=p.active,
            par_level=p.target_stock,
            min_stock=p.min_stock,
            lead_time_days=p.lead_time_days or 1,
        )

    def get_product_by_id(self, product_id: int) -> Optional[POSProduct]:
        """Fetch a single product by ID."""
        from app.models import Product

        p = self.db.query(Product).filter(Product.id == product_id).first()
        if not p:
            return None

        supplier_name = None
        if p.supplier:
            supplier_name = p.supplier.name

        return POSProduct(
            id=p.id,
            barcode=p.barcode,
            name=p.name,
            sku=p.sku,
            case_pack=p.pack_size or 1,
            supplier_id=p.supplier_id,
            supplier_name=supplier_name,
            cost_price=p.cost_price,
            ai_label=p.ai_label,
            active=p.active,
            par_level=p.target_stock,
            min_stock=p.min_stock,
            lead_time_days=p.lead_time_days or 1,
        )

    def get_suppliers(self, active_only: bool = True) -> List[POSSupplier]:
        """Fetch suppliers from local database."""
        from app.models import Supplier

        suppliers = self.db.query(Supplier).all()

        return [
            POSSupplier(
                id=s.id,
                name=s.name,
                contact_email=s.contact_email,
                contact_phone=s.contact_phone,
                address=s.address,
                notes=s.notes,
            )
            for s in suppliers
        ]

    def get_stock_levels(
        self,
        location_id: Optional[int] = None,
        product_ids: Optional[List[int]] = None
    ) -> List[POSStockLevel]:
        """Fetch current stock levels from local database."""
        from app.models import StockOnHand, Location

        query = self.db.query(StockOnHand)

        if location_id:
            query = query.filter(StockOnHand.location_id == location_id)
        if product_ids:
            query = query.filter(StockOnHand.product_id.in_(product_ids))

        stock_records = query.all()

        result = []
        for s in stock_records:
            location = self.db.query(Location).filter(Location.id == s.location_id).first()
            location_name = location.name if location else "Unknown"

            result.append(POSStockLevel(
                product_id=s.product_id,
                location_id=s.location_id,
                location_name=location_name,
                qty_on_hand=s.qty or Decimal("0"),
                qty_available=s.qty or Decimal("0"),
            ))

        return result

    def get_sales_aggregate(
        self,
        start_date: date,
        end_date: date,
        location_id: Optional[int] = None,
        product_ids: Optional[List[int]] = None
    ) -> List[POSSalesAggregate]:
        """Fetch aggregated sales data from POS sales lines."""
        from app.models import PosSalesLine, Product
        from sqlalchemy import func

        # Convert dates to datetime for comparison
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # Build query with aggregation
        query = self.db.query(
            PosSalesLine.pos_item_id,
            PosSalesLine.name,
            PosSalesLine.location_id,
            func.sum(PosSalesLine.qty).label('total_qty'),
            func.count(PosSalesLine.id).label('num_transactions')
        ).filter(
            PosSalesLine.ts >= start_dt,
            PosSalesLine.ts <= end_dt,
            PosSalesLine.is_refund == False
        )

        if location_id:
            query = query.filter(PosSalesLine.location_id == location_id)

        query = query.group_by(
            PosSalesLine.pos_item_id,
            PosSalesLine.name,
            PosSalesLine.location_id
        )

        results = query.all()

        # Calculate days in period for daily average
        days_in_period = (end_date - start_date).days + 1

        aggregates = []
        for r in results:
            # Try to match POS item to product
            product = None
            if r.pos_item_id:
                product = self.db.query(Product).filter(
                    Product.barcode == r.pos_item_id
                ).first()
                if not product:
                    product = self.db.query(Product).filter(
                        Product.sku == r.pos_item_id
                    ).first()

            product_id = product.id if product else 0
            if product_ids and product_id not in product_ids:
                continue

            total_qty = Decimal(str(r.total_qty or 0))
            avg_daily = total_qty / days_in_period if days_in_period > 0 else Decimal("0")

            aggregates.append(POSSalesAggregate(
                product_id=product_id,
                product_name=r.name or "Unknown",
                location_id=r.location_id,
                period_start=start_date,
                period_end=end_date,
                total_qty_sold=total_qty,
                num_transactions=r.num_transactions,
                avg_daily_qty=avg_daily,
            ))

        return aggregates

    def get_in_transit_orders(
        self,
        supplier_id: Optional[int] = None,
        product_ids: Optional[List[int]] = None
    ) -> List[POSInTransitOrder]:
        """Fetch pending/in-transit orders."""
        from app.models import PurchaseOrder, PurchaseOrderLine, POStatus

        query = self.db.query(PurchaseOrder).filter(
            PurchaseOrder.status.in_([POStatus.DRAFT, POStatus.SENT])
        )

        if supplier_id:
            query = query.filter(PurchaseOrder.supplier_id == supplier_id)

        orders = query.all()

        result = []
        for order in orders:
            for line in order.lines:
                if product_ids and line.product_id not in product_ids:
                    continue

                result.append(POSInTransitOrder(
                    order_id=order.id,
                    supplier_id=order.supplier_id,
                    supplier_name=order.supplier.name if order.supplier else "Unknown",
                    product_id=line.product_id,
                    product_name=line.product.name if line.product else "Unknown",
                    qty_ordered=line.qty,
                    qty_pending=line.qty,  # Assuming not yet received
                    order_date=order.created_at,
                    status="sent" if order.status == POStatus.SENT else "draft",
                ))

        return result


# ============== External POS Database Adapter ==============

class ExternalPOSAdapter(POSAdapterBase):
    """Adapter for connecting to an external POS database.

    Configure via environment variables:
    - EXTERNAL_POS_DB_URL: Database connection URL
    - EXTERNAL_POS_MAPPING: Path to field mapping JSON file

    The mapping file should define how to map POS tables/fields to our DTOs.
    """

    def __init__(
        self,
        db_url: Optional[str] = None,
        mapping_file: Optional[str] = None
    ):
        """Initialize with database URL and mapping configuration."""
        self.db_url = db_url or os.getenv("EXTERNAL_POS_DB_URL")
        mapping_path = mapping_file or os.getenv("EXTERNAL_POS_MAPPING")

        if not self.db_url:
            raise ValueError("External POS database URL not configured")

        # Load field mapping
        self.mapping = self._load_mapping(mapping_path)

        # Create database connection
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)

    def _load_mapping(self, mapping_path: Optional[str]) -> Dict[str, Any]:
        """Load field mapping configuration."""
        if not mapping_path:
            # Return default mapping (assumes similar schema)
            return self._default_mapping()

        try:
            with open(mapping_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Mapping file not found: {mapping_path}, using defaults")
            return self._default_mapping()

    def _default_mapping(self) -> Dict[str, Any]:
        """Default field mapping assuming similar schema."""
        return {
            "products": {
                "table": "products",
                "fields": {
                    "id": "id",
                    "barcode": "barcode",
                    "name": "name",
                    "sku": "sku",
                    "supplier_id": "supplier_id",
                    "cost_price": "cost_price",
                    "pack_size": "pack_size",
                    "active": "active",
                }
            },
            "suppliers": {
                "table": "suppliers",
                "fields": {
                    "id": "id",
                    "name": "name",
                    "contact_email": "contact_email",
                    "contact_phone": "contact_phone",
                }
            },
            "stock": {
                "table": "stock_on_hand",
                "fields": {
                    "product_id": "product_id",
                    "location_id": "location_id",
                    "qty": "qty",
                }
            },
            "sales": {
                "table": "pos_sales_lines",
                "fields": {
                    "timestamp": "ts",
                    "product_id": "pos_item_id",
                    "qty": "qty",
                    "is_refund": "is_refund",
                }
            },
        }

    def _execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """Execute a raw SQL query and return results as dicts."""
        with self.Session() as session:
            result = session.execute(text(query), params or {})
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def get_products(
        self,
        active_only: bool = True,
        supplier_id: Optional[int] = None,
        category: Optional[str] = None
    ) -> List[POSProduct]:
        """Fetch products from external POS database."""
        mapping = self.mapping.get("products", {})
        table = mapping.get("table", "products")
        fields = mapping.get("fields", {})

        # Build SELECT clause
        select_parts = []
        for our_field, pos_field in fields.items():
            select_parts.append(f"{pos_field} as {our_field}")

        query = f"SELECT {', '.join(select_parts)} FROM {table}"
        conditions = []
        params = {}

        if active_only and "active" in fields:
            conditions.append(f"{fields['active']} = :active")
            params["active"] = True

        if supplier_id and "supplier_id" in fields:
            conditions.append(f"{fields['supplier_id']} = :supplier_id")
            params["supplier_id"] = supplier_id

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        rows = self._execute_query(query, params)

        return [
            POSProduct(
                id=row.get("id", 0),
                barcode=row.get("barcode"),
                name=row.get("name", "Unknown"),
                sku=row.get("sku"),
                case_pack=row.get("pack_size", 1) or 1,
                supplier_id=row.get("supplier_id"),
                cost_price=Decimal(str(row["cost_price"])) if row.get("cost_price") else None,
                active=row.get("active", True),
            )
            for row in rows
        ]

    def get_product_by_barcode(self, barcode: str) -> Optional[POSProduct]:
        """Fetch a single product by barcode from external POS."""
        products = self.get_products(active_only=False)
        for p in products:
            if p.barcode == barcode:
                return p
        return None

    def get_product_by_id(self, product_id: int) -> Optional[POSProduct]:
        """Fetch a single product by ID from external POS."""
        mapping = self.mapping.get("products", {})
        table = mapping.get("table", "products")
        fields = mapping.get("fields", {})

        select_parts = [f"{pos_field} as {our_field}" for our_field, pos_field in fields.items()]
        query = f"SELECT {', '.join(select_parts)} FROM {table} WHERE {fields.get('id', 'id')} = :id"

        rows = self._execute_query(query, {"id": product_id})
        if not rows:
            return None

        row = rows[0]
        return POSProduct(
            id=row.get("id", 0),
            barcode=row.get("barcode"),
            name=row.get("name", "Unknown"),
            sku=row.get("sku"),
            case_pack=row.get("pack_size", 1) or 1,
            supplier_id=row.get("supplier_id"),
            cost_price=Decimal(str(row["cost_price"])) if row.get("cost_price") else None,
            active=row.get("active", True),
        )

    def get_suppliers(self, active_only: bool = True) -> List[POSSupplier]:
        """Fetch suppliers from external POS database."""
        mapping = self.mapping.get("suppliers", {})
        table = mapping.get("table", "suppliers")
        fields = mapping.get("fields", {})

        select_parts = [f"{pos_field} as {our_field}" for our_field, pos_field in fields.items()]
        query = f"SELECT {', '.join(select_parts)} FROM {table}"

        rows = self._execute_query(query)

        return [
            POSSupplier(
                id=row.get("id", 0),
                name=row.get("name", "Unknown"),
                contact_email=row.get("contact_email"),
                contact_phone=row.get("contact_phone"),
            )
            for row in rows
        ]

    def get_stock_levels(
        self,
        location_id: Optional[int] = None,
        product_ids: Optional[List[int]] = None
    ) -> List[POSStockLevel]:
        """Fetch stock levels from external POS database."""
        mapping = self.mapping.get("stock", {})
        table = mapping.get("table", "stock_on_hand")
        fields = mapping.get("fields", {})

        select_parts = [f"{pos_field} as {our_field}" for our_field, pos_field in fields.items()]
        query = f"SELECT {', '.join(select_parts)} FROM {table}"

        conditions = []
        params = {}

        if location_id and "location_id" in fields:
            conditions.append(f"{fields['location_id']} = :location_id")
            params["location_id"] = location_id

        if product_ids and "product_id" in fields:
            placeholders = ", ".join([f":pid{i}" for i in range(len(product_ids))])
            conditions.append(f"{fields['product_id']} IN ({placeholders})")
            for i, pid in enumerate(product_ids):
                params[f"pid{i}"] = pid

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        rows = self._execute_query(query, params)

        return [
            POSStockLevel(
                product_id=row.get("product_id", 0),
                location_id=row.get("location_id", 0),
                location_name=str(row.get("location_id", "Unknown")),
                qty_on_hand=Decimal(str(row.get("qty", 0))),
                qty_available=Decimal(str(row.get("qty", 0))),
            )
            for row in rows
        ]

    def get_sales_aggregate(
        self,
        start_date: date,
        end_date: date,
        location_id: Optional[int] = None,
        product_ids: Optional[List[int]] = None
    ) -> List[POSSalesAggregate]:
        """Fetch aggregated sales from external POS database."""
        mapping = self.mapping.get("sales", {})
        table = mapping.get("table", "pos_sales_lines")
        fields = mapping.get("fields", {})

        ts_field = fields.get("timestamp", "ts")
        pid_field = fields.get("product_id", "pos_item_id")
        qty_field = fields.get("qty", "qty")
        refund_field = fields.get("is_refund", "is_refund")
        loc_field = fields.get("location_id", "location_id")

        query = f"""
            SELECT {pid_field} as product_id,
                   {loc_field} as location_id,
                   SUM({qty_field}) as total_qty,
                   COUNT(*) as num_transactions
            FROM {table}
            WHERE {ts_field} >= :start_date
              AND {ts_field} <= :end_date
              AND ({refund_field} = 0 OR {refund_field} IS NULL)
        """

        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

        if location_id:
            query += f" AND {loc_field} = :location_id"
            params["location_id"] = location_id

        query += f" GROUP BY {pid_field}, {loc_field}"

        rows = self._execute_query(query, params)
        days_in_period = (end_date - start_date).days + 1

        return [
            POSSalesAggregate(
                product_id=row.get("product_id", 0),
                product_name="Unknown",  # Would need join to get name
                location_id=row.get("location_id"),
                period_start=start_date,
                period_end=end_date,
                total_qty_sold=Decimal(str(row.get("total_qty", 0))),
                num_transactions=row.get("num_transactions", 0),
                avg_daily_qty=Decimal(str(row.get("total_qty", 0))) / days_in_period if days_in_period > 0 else Decimal("0"),
            )
            for row in rows
        ]

    def get_in_transit_orders(
        self,
        supplier_id: Optional[int] = None,
        product_ids: Optional[List[int]] = None
    ) -> List[POSInTransitOrder]:
        """Fetch in-transit orders from external POS database."""
        # This would require custom mapping for purchase orders
        # Return empty list if not configured
        logger.warning("In-transit orders not implemented for external POS")
        return []


# ============== Adapter Factory ==============

def get_pos_adapter(db_session: Session) -> POSAdapterBase:
    """Get the appropriate POS adapter based on configuration.

    Checks for EXTERNAL_POS_DB_URL environment variable.
    If set, uses ExternalPOSAdapter; otherwise, uses LocalDatabaseAdapter.
    """
    external_url = os.getenv("EXTERNAL_POS_DB_URL")

    if external_url:
        try:
            return ExternalPOSAdapter(db_url=external_url)
        except Exception as e:
            logger.error(f"Failed to create external POS adapter: {e}")
            logger.info("Falling back to local database adapter")

    return LocalDatabaseAdapter(db_session)
