"""Industry benchmarking API routes."""

from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db.session import DbSession
from app.models.operations import AppSetting

router = APIRouter()

BENCHMARK_CATEGORY = "benchmark"


# --------------- Pydantic schemas ---------------


class BenchmarkSummary(BaseModel):
    food_cost_pct: float
    beverage_cost_pct: float
    labor_cost_pct: float
    avg_check: float
    table_turnover: float
    industry_food_cost: float
    industry_beverage_cost: float
    industry_labor_cost: float
    industry_avg_check: float
    industry_turnover: float
    performance_score: int


class PeerComparison(BaseModel):
    metric: str
    your_value: float
    peer_avg: float
    peer_best: float
    percentile: int


class Recommendation(BaseModel):
    id: str
    category: str
    title: str
    description: str
    potential_impact: str
    priority: str  # high, medium, low
    effort: str  # easy, moderate, hard


# --------------- helper utilities ---------------


def _get_setting_value(db: DbSession, key: str) -> Any:
    """Return the JSON value for a benchmark key, or None if not found."""
    row = (
        db.query(AppSetting)
        .filter(AppSetting.category == BENCHMARK_CATEGORY, AppSetting.key == key)
        .first()
    )
    return row.value if row else None


def _upsert_setting(db: DbSession, key: str, value: Any) -> AppSetting:
    """Insert or update a benchmark setting row and commit."""
    row = (
        db.query(AppSetting)
        .filter(AppSetting.category == BENCHMARK_CATEGORY, AppSetting.key == key)
        .first()
    )
    if row:
        row.value = value
        row.updated_at = datetime.now(timezone.utc)
    else:
        row = AppSetting(category=BENCHMARK_CATEGORY, key=key, value=value)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


# --------------- default empty values ---------------

_DEFAULT_SUMMARY = BenchmarkSummary(
    food_cost_pct=0.0,
    beverage_cost_pct=0.0,
    labor_cost_pct=0.0,
    avg_check=0.0,
    table_turnover=0.0,
    industry_food_cost=0.0,
    industry_beverage_cost=0.0,
    industry_labor_cost=0.0,
    industry_avg_check=0.0,
    industry_turnover=0.0,
    performance_score=0,
)


# --------------- endpoints ---------------


@router.get("/summary")
async def get_benchmark_summary(db: DbSession, period: str = Query("month")):
    """Get benchmarking summary."""
    stored = _get_setting_value(db, f"summary_{period}")
    if stored and isinstance(stored, dict):
        try:
            return BenchmarkSummary(**stored)
        except Exception:
            pass
    return _DEFAULT_SUMMARY


@router.put("/summary")
async def update_benchmark_summary(
    data: BenchmarkSummary, db: DbSession, period: str = Query("month")
):
    """Update benchmarking summary."""
    _upsert_setting(db, f"summary_{period}", data.model_dump())
    return {"success": True}


@router.get("/peers")
async def get_peer_comparisons(db: DbSession):
    """Get peer comparison data."""
    stored = _get_setting_value(db, "peers")
    if stored and isinstance(stored, list):
        try:
            return [PeerComparison(**item) for item in stored]
        except Exception:
            pass
    return []


@router.put("/peers")
async def update_peer_comparisons(data: List[PeerComparison], db: DbSession):
    """Update peer comparison data."""
    _upsert_setting(db, "peers", [item.model_dump() for item in data])
    return {"success": True}


@router.get("/recommendations")
async def get_recommendations(db: DbSession):
    """Get improvement recommendations."""
    stored = _get_setting_value(db, "recommendations")
    if stored and isinstance(stored, list):
        try:
            return [Recommendation(**item) for item in stored]
        except Exception:
            pass
    return []


@router.put("/recommendations")
async def update_recommendations(data: List[Recommendation], db: DbSession):
    """Update improvement recommendations."""
    _upsert_setting(db, "recommendations", [item.model_dump() for item in data])
    return {"success": True}
