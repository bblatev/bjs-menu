"""Industry benchmarking API routes."""

from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


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


@router.get("/summary")
async def get_benchmark_summary(period: str = Query("month")):
    """Get benchmarking summary."""
    return BenchmarkSummary(
        food_cost_pct=28.5,
        beverage_cost_pct=22.0,
        labor_cost_pct=32.0,
        avg_check=45.50,
        table_turnover=2.8,
        industry_food_cost=30.0,
        industry_beverage_cost=24.0,
        industry_labor_cost=30.0,
        industry_avg_check=42.00,
        industry_turnover=2.5,
        performance_score=78
    )


@router.get("/peers")
async def get_peer_comparisons():
    """Get peer comparison data."""
    return [
        PeerComparison(metric="Food Cost %", your_value=28.5, peer_avg=30.0, peer_best=25.0, percentile=72),
        PeerComparison(metric="Labor Cost %", your_value=32.0, peer_avg=30.0, peer_best=26.0, percentile=38),
        PeerComparison(metric="Average Check", your_value=45.50, peer_avg=42.00, peer_best=55.00, percentile=68),
        PeerComparison(metric="Table Turnover", your_value=2.8, peer_avg=2.5, peer_best=3.5, percentile=65),
        PeerComparison(metric="Customer Satisfaction", your_value=4.2, peer_avg=4.0, peer_best=4.8, percentile=58),
    ]


@router.get("/recommendations")
async def get_recommendations():
    """Get improvement recommendations."""
    return [
        Recommendation(id="1", category="Labor", title="Optimize Scheduling", description="Reduce overstaffing during slow periods", potential_impact="Save 2-3% on labor costs", priority="high", effort="moderate"),
        Recommendation(id="2", category="Menu", title="Menu Engineering", description="Promote high-margin items more prominently", potential_impact="Increase margins by 1.5%", priority="medium", effort="easy"),
        Recommendation(id="3", category="Inventory", title="Reduce Waste", description="Implement better portion control", potential_impact="Reduce food cost by 2%", priority="high", effort="moderate"),
    ]
