"""Custom Report Builder Service.

Allows users to create custom reports by selecting data sources,
columns, filters, grouping, and visualizations.
"""

import logging
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
import json

logger = logging.getLogger(__name__)


class DataSourceType(str, Enum):
    ORDERS = "orders"
    SALES = "sales"
    INVENTORY = "inventory"
    STAFF = "staff"
    CUSTOMERS = "customers"
    PRODUCTS = "products"
    PAYMENTS = "payments"
    RESERVATIONS = "reservations"


class ColumnType(str, Enum):
    STRING = "string"
    NUMBER = "number"
    CURRENCY = "currency"
    DATE = "date"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    PERCENTAGE = "percentage"


class AggregationType(str, Enum):
    SUM = "sum"
    COUNT = "count"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT_DISTINCT = "count_distinct"


class FilterOperator(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN_LIST = "in_list"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class ChartType(str, Enum):
    TABLE = "table"
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    AREA = "area"
    DONUT = "donut"
    SCATTER = "scatter"
    HEATMAP = "heatmap"


@dataclass
class ColumnDefinition:
    """Definition of a data source column."""
    column_id: str
    name: str
    display_name: str
    column_type: ColumnType
    data_source: DataSourceType
    description: str = ""
    is_aggregatable: bool = True
    is_groupable: bool = True
    is_filterable: bool = True
    format_string: Optional[str] = None


@dataclass
class ReportColumn:
    """A column in a custom report."""
    column_id: str
    display_name: Optional[str] = None
    aggregation: Optional[AggregationType] = None
    format_string: Optional[str] = None
    width: Optional[int] = None
    sort_order: Optional[str] = None  # asc, desc
    sort_priority: int = 0


@dataclass
class ReportFilter:
    """A filter in a custom report."""
    filter_id: str
    column_id: str
    operator: FilterOperator
    value: Any
    value2: Optional[Any] = None  # For BETWEEN operator


@dataclass
class ReportGrouping:
    """A grouping in a custom report."""
    column_id: str
    sort_order: str = "asc"


@dataclass
class CustomReport:
    """A custom report definition."""
    report_id: str
    name: str
    description: str = ""
    data_source: DataSourceType = DataSourceType.ORDERS
    columns: List[ReportColumn] = field(default_factory=list)
    filters: List[ReportFilter] = field(default_factory=list)
    groupings: List[ReportGrouping] = field(default_factory=list)
    chart_type: ChartType = ChartType.TABLE
    chart_config: Dict[str, Any] = field(default_factory=dict)
    is_public: bool = False
    owner_id: Optional[int] = None
    venue_id: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SavedReportRun:
    """A saved execution of a custom report."""
    run_id: str
    report_id: str
    parameters: Dict[str, Any]
    row_count: int
    executed_at: datetime
    execution_time_ms: int
    cached_until: Optional[datetime] = None


class CustomReportBuilderService:
    """Service for building and running custom reports."""

    def __init__(self):
        # In-memory storage
        self._reports: Dict[str, CustomReport] = {}
        self._runs: Dict[str, SavedReportRun] = {}

        # Define available columns per data source
        self._column_definitions: Dict[str, List[ColumnDefinition]] = {}
        self._init_column_definitions()

    def _init_column_definitions(self):
        """Initialize available column definitions."""
        # Orders data source
        self._column_definitions[DataSourceType.ORDERS.value] = [
            ColumnDefinition("order_id", "order_id", "Order ID", ColumnType.STRING, DataSourceType.ORDERS),
            ColumnDefinition("order_date", "order_date", "Order Date", ColumnType.DATE, DataSourceType.ORDERS),
            ColumnDefinition("order_time", "order_time", "Order Time", ColumnType.DATETIME, DataSourceType.ORDERS),
            ColumnDefinition("table_number", "table_number", "Table", ColumnType.STRING, DataSourceType.ORDERS),
            ColumnDefinition("server_name", "server_name", "Server", ColumnType.STRING, DataSourceType.ORDERS),
            ColumnDefinition("order_type", "order_type", "Order Type", ColumnType.STRING, DataSourceType.ORDERS, description="Dine-in, Takeout, Delivery"),
            ColumnDefinition("subtotal", "subtotal", "Subtotal", ColumnType.CURRENCY, DataSourceType.ORDERS),
            ColumnDefinition("tax", "tax", "Tax", ColumnType.CURRENCY, DataSourceType.ORDERS),
            ColumnDefinition("discount", "discount", "Discount", ColumnType.CURRENCY, DataSourceType.ORDERS),
            ColumnDefinition("total", "total", "Total", ColumnType.CURRENCY, DataSourceType.ORDERS),
            ColumnDefinition("tip", "tip", "Tip", ColumnType.CURRENCY, DataSourceType.ORDERS),
            ColumnDefinition("item_count", "item_count", "Items", ColumnType.NUMBER, DataSourceType.ORDERS),
            ColumnDefinition("guest_count", "guest_count", "Guests", ColumnType.NUMBER, DataSourceType.ORDERS),
            ColumnDefinition("payment_method", "payment_method", "Payment", ColumnType.STRING, DataSourceType.ORDERS),
            ColumnDefinition("status", "status", "Status", ColumnType.STRING, DataSourceType.ORDERS),
            ColumnDefinition("hour_of_day", "hour_of_day", "Hour", ColumnType.NUMBER, DataSourceType.ORDERS),
            ColumnDefinition("day_of_week", "day_of_week", "Day of Week", ColumnType.STRING, DataSourceType.ORDERS),
        ]

        # Sales data source
        self._column_definitions[DataSourceType.SALES.value] = [
            ColumnDefinition("sale_date", "sale_date", "Date", ColumnType.DATE, DataSourceType.SALES),
            ColumnDefinition("product_id", "product_id", "Product ID", ColumnType.STRING, DataSourceType.SALES),
            ColumnDefinition("product_name", "product_name", "Product", ColumnType.STRING, DataSourceType.SALES),
            ColumnDefinition("category", "category", "Category", ColumnType.STRING, DataSourceType.SALES),
            ColumnDefinition("quantity_sold", "quantity_sold", "Qty Sold", ColumnType.NUMBER, DataSourceType.SALES),
            ColumnDefinition("unit_price", "unit_price", "Unit Price", ColumnType.CURRENCY, DataSourceType.SALES),
            ColumnDefinition("revenue", "revenue", "Revenue", ColumnType.CURRENCY, DataSourceType.SALES),
            ColumnDefinition("cost", "cost", "Cost", ColumnType.CURRENCY, DataSourceType.SALES),
            ColumnDefinition("profit", "profit", "Profit", ColumnType.CURRENCY, DataSourceType.SALES),
            ColumnDefinition("margin_percent", "margin_percent", "Margin %", ColumnType.PERCENTAGE, DataSourceType.SALES),
        ]

        # Inventory data source
        self._column_definitions[DataSourceType.INVENTORY.value] = [
            ColumnDefinition("item_id", "item_id", "Item ID", ColumnType.STRING, DataSourceType.INVENTORY),
            ColumnDefinition("item_name", "item_name", "Item Name", ColumnType.STRING, DataSourceType.INVENTORY),
            ColumnDefinition("category", "category", "Category", ColumnType.STRING, DataSourceType.INVENTORY),
            ColumnDefinition("current_stock", "current_stock", "Current Stock", ColumnType.NUMBER, DataSourceType.INVENTORY),
            ColumnDefinition("unit", "unit", "Unit", ColumnType.STRING, DataSourceType.INVENTORY),
            ColumnDefinition("reorder_level", "reorder_level", "Reorder Level", ColumnType.NUMBER, DataSourceType.INVENTORY),
            ColumnDefinition("unit_cost", "unit_cost", "Unit Cost", ColumnType.CURRENCY, DataSourceType.INVENTORY),
            ColumnDefinition("total_value", "total_value", "Total Value", ColumnType.CURRENCY, DataSourceType.INVENTORY),
            ColumnDefinition("supplier", "supplier", "Supplier", ColumnType.STRING, DataSourceType.INVENTORY),
            ColumnDefinition("last_received", "last_received", "Last Received", ColumnType.DATE, DataSourceType.INVENTORY),
            ColumnDefinition("days_until_expiry", "days_until_expiry", "Days to Expiry", ColumnType.NUMBER, DataSourceType.INVENTORY),
        ]

        # Staff data source
        self._column_definitions[DataSourceType.STAFF.value] = [
            ColumnDefinition("staff_id", "staff_id", "Staff ID", ColumnType.STRING, DataSourceType.STAFF),
            ColumnDefinition("staff_name", "staff_name", "Name", ColumnType.STRING, DataSourceType.STAFF),
            ColumnDefinition("role", "role", "Role", ColumnType.STRING, DataSourceType.STAFF),
            ColumnDefinition("shift_date", "shift_date", "Date", ColumnType.DATE, DataSourceType.STAFF),
            ColumnDefinition("hours_worked", "hours_worked", "Hours", ColumnType.NUMBER, DataSourceType.STAFF),
            ColumnDefinition("orders_served", "orders_served", "Orders", ColumnType.NUMBER, DataSourceType.STAFF),
            ColumnDefinition("sales_total", "sales_total", "Sales", ColumnType.CURRENCY, DataSourceType.STAFF),
            ColumnDefinition("tips_total", "tips_total", "Tips", ColumnType.CURRENCY, DataSourceType.STAFF),
            ColumnDefinition("avg_ticket", "avg_ticket", "Avg Ticket", ColumnType.CURRENCY, DataSourceType.STAFF),
        ]

        # Customers data source
        self._column_definitions[DataSourceType.CUSTOMERS.value] = [
            ColumnDefinition("customer_id", "customer_id", "Customer ID", ColumnType.STRING, DataSourceType.CUSTOMERS),
            ColumnDefinition("customer_name", "customer_name", "Name", ColumnType.STRING, DataSourceType.CUSTOMERS),
            ColumnDefinition("email", "email", "Email", ColumnType.STRING, DataSourceType.CUSTOMERS),
            ColumnDefinition("phone", "phone", "Phone", ColumnType.STRING, DataSourceType.CUSTOMERS),
            ColumnDefinition("first_visit", "first_visit", "First Visit", ColumnType.DATE, DataSourceType.CUSTOMERS),
            ColumnDefinition("last_visit", "last_visit", "Last Visit", ColumnType.DATE, DataSourceType.CUSTOMERS),
            ColumnDefinition("visit_count", "visit_count", "Visits", ColumnType.NUMBER, DataSourceType.CUSTOMERS),
            ColumnDefinition("total_spent", "total_spent", "Total Spent", ColumnType.CURRENCY, DataSourceType.CUSTOMERS),
            ColumnDefinition("avg_ticket", "avg_ticket", "Avg Ticket", ColumnType.CURRENCY, DataSourceType.CUSTOMERS),
            ColumnDefinition("loyalty_points", "loyalty_points", "Points", ColumnType.NUMBER, DataSourceType.CUSTOMERS),
            ColumnDefinition("loyalty_tier", "loyalty_tier", "Tier", ColumnType.STRING, DataSourceType.CUSTOMERS),
        ]

        # Products data source
        self._column_definitions[DataSourceType.PRODUCTS.value] = [
            ColumnDefinition("product_id", "product_id", "Product ID", ColumnType.STRING, DataSourceType.PRODUCTS),
            ColumnDefinition("product_name", "product_name", "Name", ColumnType.STRING, DataSourceType.PRODUCTS),
            ColumnDefinition("category", "category", "Category", ColumnType.STRING, DataSourceType.PRODUCTS),
            ColumnDefinition("price", "price", "Price", ColumnType.CURRENCY, DataSourceType.PRODUCTS),
            ColumnDefinition("cost", "cost", "Cost", ColumnType.CURRENCY, DataSourceType.PRODUCTS),
            ColumnDefinition("margin", "margin", "Margin", ColumnType.CURRENCY, DataSourceType.PRODUCTS),
            ColumnDefinition("is_active", "is_active", "Active", ColumnType.BOOLEAN, DataSourceType.PRODUCTS),
            ColumnDefinition("total_sold", "total_sold", "Total Sold", ColumnType.NUMBER, DataSourceType.PRODUCTS),
            ColumnDefinition("revenue", "revenue", "Revenue", ColumnType.CURRENCY, DataSourceType.PRODUCTS),
        ]

    # =========================================================================
    # Data Source Definitions
    # =========================================================================

    def get_data_sources(self) -> List[Dict[str, Any]]:
        """Get available data sources."""
        return [
            {"id": ds.value, "name": ds.value.replace("_", " ").title(), "description": f"Data from {ds.value}"}
            for ds in DataSourceType
        ]

    def get_columns_for_source(self, data_source: DataSourceType) -> List[ColumnDefinition]:
        """Get available columns for a data source."""
        return self._column_definitions.get(data_source.value, [])

    # =========================================================================
    # Report Management
    # =========================================================================

    def create_report(
        self,
        name: str,
        data_source: DataSourceType,
        description: str = "",
        columns: Optional[List[Dict[str, Any]]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        groupings: Optional[List[Dict[str, Any]]] = None,
        chart_type: ChartType = ChartType.TABLE,
        chart_config: Optional[Dict[str, Any]] = None,
        owner_id: Optional[int] = None,
        venue_id: Optional[int] = None,
    ) -> CustomReport:
        """Create a new custom report."""
        report_id = f"rpt-{uuid.uuid4().hex[:8]}"

        report_columns = []
        if columns:
            for col in columns:
                agg = None
                if col.get("aggregation"):
                    try:
                        agg = AggregationType(col["aggregation"])
                    except ValueError:
                        pass

                report_columns.append(ReportColumn(
                    column_id=col.get("column_id", ""),
                    display_name=col.get("display_name"),
                    aggregation=agg,
                    format_string=col.get("format_string"),
                    width=col.get("width"),
                    sort_order=col.get("sort_order"),
                    sort_priority=col.get("sort_priority", 0),
                ))

        report_filters = []
        if filters:
            for flt in filters:
                try:
                    op = FilterOperator(flt.get("operator", "equals"))
                except ValueError:
                    op = FilterOperator.EQUALS

                report_filters.append(ReportFilter(
                    filter_id=f"flt-{uuid.uuid4().hex[:6]}",
                    column_id=flt.get("column_id", ""),
                    operator=op,
                    value=flt.get("value"),
                    value2=flt.get("value2"),
                ))

        report_groupings = []
        if groupings:
            for grp in groupings:
                report_groupings.append(ReportGrouping(
                    column_id=grp.get("column_id", ""),
                    sort_order=grp.get("sort_order", "asc"),
                ))

        report = CustomReport(
            report_id=report_id,
            name=name,
            description=description,
            data_source=data_source,
            columns=report_columns,
            filters=report_filters,
            groupings=report_groupings,
            chart_type=chart_type,
            chart_config=chart_config or {},
            owner_id=owner_id,
            venue_id=venue_id,
        )

        self._reports[report_id] = report
        logger.info(f"Created custom report {report_id}: {name}")

        return report

    def update_report(self, report_id: str, **updates) -> Optional[CustomReport]:
        """Update a custom report."""
        report = self._reports.get(report_id)
        if not report:
            return None

        if "columns" in updates and updates["columns"] is not None:
            report_columns = []
            for col in updates["columns"]:
                agg = None
                if col.get("aggregation"):
                    try:
                        agg = AggregationType(col["aggregation"])
                    except ValueError:
                        pass

                report_columns.append(ReportColumn(
                    column_id=col.get("column_id", ""),
                    display_name=col.get("display_name"),
                    aggregation=agg,
                    format_string=col.get("format_string"),
                    width=col.get("width"),
                    sort_order=col.get("sort_order"),
                    sort_priority=col.get("sort_priority", 0),
                ))
            report.columns = report_columns
            del updates["columns"]

        if "filters" in updates and updates["filters"] is not None:
            report_filters = []
            for flt in updates["filters"]:
                try:
                    op = FilterOperator(flt.get("operator", "equals"))
                except ValueError:
                    op = FilterOperator.EQUALS

                report_filters.append(ReportFilter(
                    filter_id=f"flt-{uuid.uuid4().hex[:6]}",
                    column_id=flt.get("column_id", ""),
                    operator=op,
                    value=flt.get("value"),
                    value2=flt.get("value2"),
                ))
            report.filters = report_filters
            del updates["filters"]

        if "groupings" in updates and updates["groupings"] is not None:
            report_groupings = []
            for grp in updates["groupings"]:
                report_groupings.append(ReportGrouping(
                    column_id=grp.get("column_id", ""),
                    sort_order=grp.get("sort_order", "asc"),
                ))
            report.groupings = report_groupings
            del updates["groupings"]

        for key, value in updates.items():
            if hasattr(report, key) and value is not None:
                if key == "chart_type":
                    try:
                        value = ChartType(value)
                    except ValueError:
                        continue
                elif key == "data_source":
                    try:
                        value = DataSourceType(value)
                    except ValueError:
                        continue
                setattr(report, key, value)

        report.updated_at = datetime.now(timezone.utc)

        return report

    def get_report(self, report_id: str) -> Optional[CustomReport]:
        """Get a report by ID."""
        return self._reports.get(report_id)

    def list_reports(
        self,
        owner_id: Optional[int] = None,
        venue_id: Optional[int] = None,
        include_public: bool = True,
    ) -> List[CustomReport]:
        """List custom reports."""
        reports = list(self._reports.values())

        if owner_id is not None:
            reports = [r for r in reports if r.owner_id == owner_id or (include_public and r.is_public)]

        if venue_id is not None:
            reports = [r for r in reports if r.venue_id == venue_id or r.venue_id is None]

        return sorted(reports, key=lambda r: r.updated_at, reverse=True)

    def delete_report(self, report_id: str) -> bool:
        """Delete a report."""
        if report_id in self._reports:
            del self._reports[report_id]
            return True
        return False

    def duplicate_report(self, report_id: str, new_name: str) -> Optional[CustomReport]:
        """Duplicate an existing report."""
        original = self._reports.get(report_id)
        if not original:
            return None

        new_report = CustomReport(
            report_id=f"rpt-{uuid.uuid4().hex[:8]}",
            name=new_name,
            description=original.description,
            data_source=original.data_source,
            columns=original.columns.copy(),
            filters=original.filters.copy(),
            groupings=original.groupings.copy(),
            chart_type=original.chart_type,
            chart_config=original.chart_config.copy(),
            owner_id=original.owner_id,
            venue_id=original.venue_id,
        )

        self._reports[new_report.report_id] = new_report

        return new_report

    # =========================================================================
    # Report Execution
    # =========================================================================

    def run_report(
        self,
        report_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a custom report and return results.

        In production, this would query the actual database.
        For now, returns sample data.
        """
        report = self._reports.get(report_id)
        if not report:
            return {"error": "Report not found"}

        start_time = datetime.now(timezone.utc)
        params = parameters or {}

        # Generate sample data based on report configuration
        data = self._generate_sample_data(report, params)

        execution_time = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

        # Save run record
        run = SavedReportRun(
            run_id=f"run-{uuid.uuid4().hex[:8]}",
            report_id=report_id,
            parameters=params,
            row_count=len(data),
            executed_at=datetime.now(timezone.utc),
            execution_time_ms=execution_time,
        )
        self._runs[run.run_id] = run

        # Build column metadata
        column_meta = []
        for col in report.columns:
            col_def = self._find_column_definition(report.data_source, col.column_id)
            column_meta.append({
                "column_id": col.column_id,
                "display_name": col.display_name or (col_def.display_name if col_def else col.column_id),
                "type": col_def.column_type.value if col_def else "string",
                "aggregation": col.aggregation.value if col.aggregation else None,
            })

        return {
            "report_id": report_id,
            "run_id": run.run_id,
            "name": report.name,
            "columns": column_meta,
            "data": data,
            "row_count": len(data),
            "execution_time_ms": execution_time,
            "chart_type": report.chart_type.value,
            "chart_config": report.chart_config,
        }

    def _find_column_definition(
        self,
        data_source: DataSourceType,
        column_id: str,
    ) -> Optional[ColumnDefinition]:
        """Find column definition by ID."""
        columns = self._column_definitions.get(data_source.value, [])
        for col in columns:
            if col.column_id == column_id:
                return col
        return None

    def _generate_sample_data(
        self,
        report: CustomReport,
        params: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate sample data for report preview."""
        # In production, this would execute actual queries
        # For now, generate realistic sample data

        rows = []
        num_rows = params.get("limit", 10)

        for i in range(num_rows):
            row = {}
            for col in report.columns:
                col_def = self._find_column_definition(report.data_source, col.column_id)
                if col_def:
                    row[col.column_id] = self._generate_sample_value(col_def, i)
            rows.append(row)

        return rows

    def _generate_sample_value(self, col_def: ColumnDefinition, index: int) -> Any:
        """Generate a sample value for a column."""
        if col_def.column_type == ColumnType.NUMBER:
            return (index + 1) * 10
        elif col_def.column_type == ColumnType.CURRENCY:
            return round((index + 1) * 25.50, 2)
        elif col_def.column_type == ColumnType.PERCENTAGE:
            return round(20 + (index * 5), 1)
        elif col_def.column_type == ColumnType.DATE:
            return (date.today() - timedelta(days=index)).isoformat()
        elif col_def.column_type == ColumnType.DATETIME:
            return datetime.now(timezone.utc).isoformat()
        elif col_def.column_type == ColumnType.BOOLEAN:
            return index % 2 == 0
        else:
            return f"{col_def.display_name} {index + 1}"

    # =========================================================================
    # Export
    # =========================================================================

    def export_report_definition(self, report_id: str) -> Optional[str]:
        """Export report definition as JSON."""
        report = self._reports.get(report_id)
        if not report:
            return None

        export_data = {
            "name": report.name,
            "description": report.description,
            "data_source": report.data_source.value,
            "columns": [
                {
                    "column_id": c.column_id,
                    "display_name": c.display_name,
                    "aggregation": c.aggregation.value if c.aggregation else None,
                }
                for c in report.columns
            ],
            "filters": [
                {
                    "column_id": f.column_id,
                    "operator": f.operator.value,
                    "value": f.value,
                    "value2": f.value2,
                }
                for f in report.filters
            ],
            "groupings": [
                {"column_id": g.column_id, "sort_order": g.sort_order}
                for g in report.groupings
            ],
            "chart_type": report.chart_type.value,
            "chart_config": report.chart_config,
        }

        return json.dumps(export_data, indent=2)

    def import_report_definition(
        self,
        json_data: str,
        owner_id: Optional[int] = None,
        venue_id: Optional[int] = None,
    ) -> Optional[CustomReport]:
        """Import report from JSON definition."""
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError:
            return None

        return self.create_report(
            name=data.get("name", "Imported Report"),
            data_source=DataSourceType(data.get("data_source", "orders")),
            description=data.get("description", ""),
            columns=data.get("columns", []),
            filters=data.get("filters", []),
            groupings=data.get("groupings", []),
            chart_type=ChartType(data.get("chart_type", "table")),
            chart_config=data.get("chart_config", {}),
            owner_id=owner_id,
            venue_id=venue_id,
        )


# Singleton instance
_report_builder_service: Optional[CustomReportBuilderService] = None


def get_custom_report_builder_service() -> CustomReportBuilderService:
    """Get the custom report builder service singleton."""
    global _report_builder_service
    if _report_builder_service is None:
        _report_builder_service = CustomReportBuilderService()
    return _report_builder_service
