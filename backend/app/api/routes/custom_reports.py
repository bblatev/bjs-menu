"""Custom Report Builder API routes.

Drag-and-drop report builder for creating custom reports.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request
from app.core.rate_limit import limiter
from pydantic import BaseModel

from app.services.custom_report_builder_service import (
    get_custom_report_builder_service,
    DataSourceType,
    ChartType,
)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ColumnRequest(BaseModel):
    column_id: str
    display_name: Optional[str] = None
    aggregation: Optional[str] = None  # sum, count, avg, min, max
    format_string: Optional[str] = None
    width: Optional[int] = None
    sort_order: Optional[str] = None  # asc, desc
    sort_priority: int = 0


class FilterRequest(BaseModel):
    column_id: str
    operator: str  # equals, not_equals, greater_than, less_than, etc.
    value: str | int | float | list | None
    value2: str | int | float | None = None  # For between operator


class GroupingRequest(BaseModel):
    column_id: str
    sort_order: str = "asc"


class CreateReportRequest(BaseModel):
    name: str
    description: str = ""
    data_source: str  # orders, sales, inventory, staff, customers, products
    columns: List[ColumnRequest] = []
    filters: List[FilterRequest] = []
    groupings: List[GroupingRequest] = []
    chart_type: str = "table"  # table, bar, line, pie, area, donut
    chart_config: dict = {}
    venue_id: Optional[int] = None


class UpdateReportRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    columns: Optional[List[ColumnRequest]] = None
    filters: Optional[List[FilterRequest]] = None
    groupings: Optional[List[GroupingRequest]] = None
    chart_type: Optional[str] = None
    chart_config: Optional[dict] = None
    is_public: Optional[bool] = None


class ExecuteReportRequest(BaseModel):
    data_source_id: str  # orders, sales, inventory, staff, customers, products
    columns: List[ColumnRequest] = []
    filters: List[FilterRequest] = []
    groupings: List[GroupingRequest] = []
    sort_direction: str = "asc"
    limit: int = 100
    chart_type: str = "table"
    chart_config: dict = {}


class RunReportRequest(BaseModel):
    parameters: dict = {}
    limit: int = 100


class ImportReportRequest(BaseModel):
    json_data: str
    venue_id: Optional[int] = None


class ReportResponse(BaseModel):
    report_id: str
    name: str
    description: str
    data_source: str
    columns: List[dict]
    filters: List[dict]
    groupings: List[dict]
    chart_type: str
    chart_config: dict
    is_public: bool
    owner_id: Optional[int] = None
    venue_id: Optional[int] = None
    created_at: str
    updated_at: str


# ============================================================================
# Data Sources & Columns
# ============================================================================

@router.get("/data-sources")
@limiter.limit("60/minute")
async def get_data_sources(request: Request):
    """
    Get available data sources for reports.

    Data sources define what type of data can be queried.
    """
    service = get_custom_report_builder_service()

    return {
        "sources": service.get_data_sources(),
    }


@router.get("/data-sources/{source}/columns")
@limiter.limit("60/minute")
async def get_columns(request: Request, source: str):
    """
    Get available columns for a data source.

    Returns column definitions including name, type, and capabilities.
    """
    service = get_custom_report_builder_service()

    try:
        data_source = DataSourceType(source)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid data source: {source}")

    columns = service.get_columns_for_source(data_source)

    return {
        "data_source": source,
        "columns": [
            {
                "column_id": col.column_id,
                "name": col.name,
                "display_name": col.display_name,
                "type": col.column_type.value,
                "description": col.description,
                "is_aggregatable": col.is_aggregatable,
                "is_groupable": col.is_groupable,
                "is_filterable": col.is_filterable,
            }
            for col in columns
        ],
    }


# ============================================================================
# Report CRUD
# ============================================================================

@router.post("/reports", response_model=ReportResponse)
@limiter.limit("30/minute")
async def create_report(request: Request, body: CreateReportRequest = None):
    """
    Create a new custom report.

    Configure data source, columns, filters, groupings, and visualization.
    """
    service = get_custom_report_builder_service()

    try:
        data_source = DataSourceType(body.data_source)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid data source: {body.data_source}")

    try:
        chart_type = ChartType(body.chart_type)
    except ValueError:
        chart_type = ChartType.TABLE

    columns = [col.model_dump() for col in body.columns]
    filters = [flt.model_dump() for flt in body.filters]
    groupings = [grp.model_dump() for grp in body.groupings]

    report = service.create_report(
        name=body.name,
        description=body.description,
        data_source=data_source,
        columns=columns,
        filters=filters,
        groupings=groupings,
        chart_type=chart_type,
        chart_config=body.chart_config,
        venue_id=body.venue_id,
    )

    return _report_to_response(report)


@router.get("/reports", response_model=List[ReportResponse])
@limiter.limit("60/minute")
async def list_reports(
    request: Request,
    venue_id: Optional[int] = None,
    owner_id: Optional[int] = None,
    include_public: bool = True,
):
    """List custom reports."""
    service = get_custom_report_builder_service()

    reports = service.list_reports(
        owner_id=owner_id,
        venue_id=venue_id,
        include_public=include_public,
    )

    return [_report_to_response(r) for r in reports]


@router.get("/reports/{report_id}", response_model=ReportResponse)
@limiter.limit("60/minute")
async def get_report(request: Request, report_id: str):
    """Get a specific report."""
    service = get_custom_report_builder_service()

    report = service.get_report(report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return _report_to_response(report)


@router.put("/reports/{report_id}", response_model=ReportResponse)
@limiter.limit("30/minute")
async def update_report(request: Request, report_id: str, body: UpdateReportRequest = None):
    """Update a custom report."""
    service = get_custom_report_builder_service()

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.description is not None:
        updates["description"] = body.description
    if body.columns is not None:
        updates["columns"] = [col.model_dump() for col in body.columns]
    if body.filters is not None:
        updates["filters"] = [flt.model_dump() for flt in body.filters]
    if body.groupings is not None:
        updates["groupings"] = [grp.model_dump() for grp in body.groupings]
    if body.chart_type is not None:
        updates["chart_type"] = body.chart_type
    if body.chart_config is not None:
        updates["chart_config"] = body.chart_config
    if body.is_public is not None:
        updates["is_public"] = body.is_public

    report = service.update_report(report_id, **updates)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return _report_to_response(report)


@router.delete("/reports/{report_id}")
@limiter.limit("30/minute")
async def delete_report(request: Request, report_id: str):
    """Delete a custom report."""
    service = get_custom_report_builder_service()

    if not service.delete_report(report_id):
        raise HTTPException(status_code=404, detail="Report not found")

    return {"success": True, "message": "Report deleted"}


@router.post("/reports/{report_id}/duplicate", response_model=ReportResponse)
@limiter.limit("30/minute")
async def duplicate_report(request: Request, report_id: str, new_name: str):
    """Duplicate an existing report."""
    service = get_custom_report_builder_service()

    report = service.duplicate_report(report_id, new_name)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return _report_to_response(report)


# ============================================================================
# Report Execution
# ============================================================================

@router.post("/reports/execute")
@limiter.limit("30/minute")
async def execute_report(request: Request, body: ExecuteReportRequest = None):
    """
    Execute an ad-hoc report without saving it.

    Accepts a report configuration directly and returns results.
    Useful for previewing reports before saving.
    """
    service = get_custom_report_builder_service()

    try:
        data_source = DataSourceType(body.data_source_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid data source: {body.data_source_id}",
        )

    try:
        chart_type = ChartType(body.chart_type)
    except ValueError:
        chart_type = ChartType.TABLE

    columns = [col.model_dump() for col in body.columns]
    filters = [flt.model_dump() for flt in body.filters]
    groupings = [grp.model_dump() for grp in body.groupings]

    # Create a temporary report to execute
    temp_report = service.create_report(
        name="__adhoc_execute__",
        data_source=data_source,
        columns=columns,
        filters=filters,
        groupings=groupings,
        chart_type=chart_type,
        chart_config=body.chart_config,
    )

    try:
        result = service.run_report(
            temp_report.report_id,
            {"limit": body.limit, "sort_direction": body.sort_direction},
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return result
    finally:
        # Clean up the temporary report
        service.delete_report(temp_report.report_id)


@router.post("/reports/{report_id}/run")
@limiter.limit("30/minute")
async def run_report(request: Request, report_id: str, body: RunReportRequest = None):
    """
    Execute a custom report and get results.

    Returns data rows, column metadata, and chart configuration.
    """
    service = get_custom_report_builder_service()

    params = body.parameters.copy()
    params["limit"] = body.limit

    result = service.run_report(report_id, params)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/reports/{report_id}/preview")
@limiter.limit("60/minute")
async def preview_report(request: Request, report_id: str, limit: int = 10):
    """Get a quick preview of report data."""
    service = get_custom_report_builder_service()

    result = service.run_report(report_id, {"limit": limit})

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ============================================================================
# Import/Export
# ============================================================================

@router.get("/reports/{report_id}/export")
@limiter.limit("60/minute")
async def export_report(request: Request, report_id: str):
    """Export report definition as JSON."""
    service = get_custom_report_builder_service()

    json_data = service.export_report_definition(report_id)

    if not json_data:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "report_id": report_id,
        "format": "json",
        "data": json_data,
    }


@router.post("/reports/import", response_model=ReportResponse)
@limiter.limit("30/minute")
async def import_report(request: Request, body: ImportReportRequest = None):
    """Import a report from JSON definition."""
    service = get_custom_report_builder_service()

    report = service.import_report_definition(
        body.json_data,
        venue_id=body.venue_id,
    )

    if not report:
        raise HTTPException(status_code=400, detail="Invalid report JSON")

    return _report_to_response(report)


# ============================================================================
# Reference Data
# ============================================================================

@router.get("/aggregations")
@limiter.limit("60/minute")
async def get_aggregations(request: Request):
    """Get available aggregation functions."""
    return {
        "aggregations": [
            {"id": "sum", "name": "Sum", "description": "Sum of values"},
            {"id": "count", "name": "Count", "description": "Count of rows"},
            {"id": "avg", "name": "Average", "description": "Average value"},
            {"id": "min", "name": "Minimum", "description": "Minimum value"},
            {"id": "max", "name": "Maximum", "description": "Maximum value"},
            {"id": "count_distinct", "name": "Count Distinct", "description": "Count of unique values"},
        ],
    }


@router.get("/operators")
@limiter.limit("60/minute")
async def get_operators(request: Request):
    """Get available filter operators."""
    return {
        "operators": [
            {"id": "equals", "name": "Equals", "symbol": "="},
            {"id": "not_equals", "name": "Not Equals", "symbol": "!="},
            {"id": "greater_than", "name": "Greater Than", "symbol": ">"},
            {"id": "less_than", "name": "Less Than", "symbol": "<"},
            {"id": "greater_or_equal", "name": "Greater or Equal", "symbol": ">="},
            {"id": "less_or_equal", "name": "Less or Equal", "symbol": "<="},
            {"id": "contains", "name": "Contains", "symbol": "LIKE"},
            {"id": "starts_with", "name": "Starts With", "symbol": "LIKE"},
            {"id": "ends_with", "name": "Ends With", "symbol": "LIKE"},
            {"id": "in_list", "name": "In List", "symbol": "IN"},
            {"id": "between", "name": "Between", "symbol": "BETWEEN"},
            {"id": "is_null", "name": "Is Empty", "symbol": "IS NULL"},
            {"id": "is_not_null", "name": "Is Not Empty", "symbol": "IS NOT NULL"},
        ],
    }


@router.get("/chart-types")
@limiter.limit("60/minute")
async def get_chart_types(request: Request):
    """Get available chart/visualization types."""
    return {
        "types": [
            {"id": "table", "name": "Table", "description": "Tabular data view", "icon": "table"},
            {"id": "bar", "name": "Bar Chart", "description": "Vertical bar chart", "icon": "bar-chart"},
            {"id": "line", "name": "Line Chart", "description": "Line/trend chart", "icon": "line-chart"},
            {"id": "pie", "name": "Pie Chart", "description": "Pie chart for proportions", "icon": "pie-chart"},
            {"id": "area", "name": "Area Chart", "description": "Filled area chart", "icon": "area-chart"},
            {"id": "donut", "name": "Donut Chart", "description": "Donut/ring chart", "icon": "donut"},
            {"id": "scatter", "name": "Scatter Plot", "description": "X-Y scatter plot", "icon": "scatter"},
            {"id": "heatmap", "name": "Heatmap", "description": "Color-coded matrix", "icon": "heatmap"},
        ],
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _report_to_response(report) -> ReportResponse:
    """Convert report to response model."""
    return ReportResponse(
        report_id=report.report_id,
        name=report.name,
        description=report.description,
        data_source=report.data_source.value,
        columns=[
            {
                "column_id": c.column_id,
                "display_name": c.display_name,
                "aggregation": c.aggregation.value if c.aggregation else None,
                "format_string": c.format_string,
                "width": c.width,
                "sort_order": c.sort_order,
                "sort_priority": c.sort_priority,
            }
            for c in report.columns
        ],
        filters=[
            {
                "filter_id": f.filter_id,
                "column_id": f.column_id,
                "operator": f.operator.value,
                "value": f.value,
                "value2": f.value2,
            }
            for f in report.filters
        ],
        groupings=[
            {"column_id": g.column_id, "sort_order": g.sort_order}
            for g in report.groupings
        ],
        chart_type=report.chart_type.value,
        chart_config=report.chart_config,
        is_public=report.is_public,
        owner_id=report.owner_id,
        venue_id=report.venue_id,
        created_at=report.created_at.isoformat(),
        updated_at=report.updated_at.isoformat(),
    )
