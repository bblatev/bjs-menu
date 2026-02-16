"""Industry benchmarking API routes."""

import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.core.rate_limit import limiter
from app.db.session import DbSession
from app.models.operations import AppSetting

logger = logging.getLogger(__name__)

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


@router.get("/")
@limiter.limit("60/minute")
async def get_benchmarking_root(request: Request, db: DbSession):
    """Benchmarking summary."""
    return await get_benchmark_summary(request=request, db=db)


@router.get("/summary")
@limiter.limit("60/minute")
async def get_benchmark_summary(request: Request, db: DbSession, period: str = Query("month")):
    """Get benchmarking summary."""
    stored = _get_setting_value(db, f"summary_{period}")
    if stored and isinstance(stored, dict):
        try:
            return BenchmarkSummary(**stored)
        except Exception as e:
            logger.warning(f"Failed to parse stored benchmark summary: {e}")
    return _DEFAULT_SUMMARY


@router.put("/summary")
@limiter.limit("30/minute")
async def update_benchmark_summary(
    request: Request, data: BenchmarkSummary, db: DbSession, period: str = Query("month")
):
    """Update benchmarking summary."""
    _upsert_setting(db, f"summary_{period}", data.model_dump())
    return {"success": True}


@router.get("/peers")
@limiter.limit("60/minute")
async def get_peer_comparisons(request: Request, db: DbSession):
    """Get peer comparison data."""
    stored = _get_setting_value(db, "peers")
    if stored and isinstance(stored, list):
        try:
            return [PeerComparison(**item) for item in stored]
        except Exception as e:
            logger.warning(f"Failed to parse stored peer comparisons: {e}")
    return []


@router.put("/peers")
@limiter.limit("30/minute")
async def update_peer_comparisons(request: Request, data: List[PeerComparison], db: DbSession):
    """Update peer comparison data."""
    _upsert_setting(db, "peers", [item.model_dump() for item in data])
    return {"success": True}


@router.get("/recommendations")
@limiter.limit("60/minute")
async def get_recommendations(request: Request, db: DbSession):
    """Get improvement recommendations."""
    stored = _get_setting_value(db, "recommendations")
    if stored and isinstance(stored, list):
        try:
            return [Recommendation(**item) for item in stored]
        except Exception as e:
            logger.warning(f"Failed to parse stored recommendations: {e}")
    return []


@router.put("/recommendations")
@limiter.limit("30/minute")
async def update_recommendations(request: Request, data: List[Recommendation], db: DbSession):
    """Update improvement recommendations."""
    _upsert_setting(db, "recommendations", [item.model_dump() for item in data])
    return {"success": True}
