"""Time clock, performance, sections & tips"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

from app.core.rate_limit import limiter
from app.db.session import get_db

# Import shared helpers
from app.api.routes.staff._shared import *
from app.api.routes.staff._shared import _init_default_staff, _prefetch_staff_names

router = APIRouter()

# ============== Performance ==============

@router.get("/staff/performance/leaderboard")
@limiter.limit("60/minute")
def get_leaderboard(
    request: Request,
    db: DbSession,
    period: str = Query("month"),
    sort_by: Literal["sales", "orders", "tips", "rating"] = Query("sales"),
):
    """Get performance leaderboard."""
    _init_default_staff(db)

    # Get all active staff
    staff = db.query(StaffUser).filter(StaffUser.is_active == True).all()

    # Determine date range
    today = date.today()
    if period == "day":
        start_date = today
    elif period == "week":
        start_date = today - timedelta(days=7)
    elif period == "year":
        start_date = today - timedelta(days=365)
    else:  # month
        start_date = today - timedelta(days=30)

    leaderboard = []

    # Batch fetch all metrics for the period
    all_metrics = db.query(PerformanceMetric).filter(
        PerformanceMetric.staff_id.in_([s.id for s in staff]),
        PerformanceMetric.period_date >= start_date,
        PerformanceMetric.period_date <= today,
    ).all()
    metrics_by_staff = {}
    for m in all_metrics:
        metrics_by_staff.setdefault(m.staff_id, []).append(m)

    # Batch fetch all time clock entries for the period
    start_date_dt = datetime.combine(start_date, time.min)
    all_entries = db.query(TimeClockEntry).filter(
        TimeClockEntry.staff_id.in_([s.id for s in staff]),
        TimeClockEntry.clock_in >= start_date_dt,
    ).all()
    entries_by_staff = {}
    for e in all_entries:
        entries_by_staff.setdefault(e.staff_id, []).append(e)

    for i, s in enumerate(staff):
        # Get performance metrics for the period
        metrics = metrics_by_staff.get(s.id, [])

        sales = sum(m.sales_amount for m in metrics) if metrics else 0
        orders = sum(m.orders_count for m in metrics) if metrics else 0
        tips = sum(m.tips_received for m in metrics) if metrics else 0
        rating = 0.0
        reviews = sum(m.reviews_count for m in metrics) if metrics else 0

        # Calculate average rating (weighted by reviews)
        if metrics:
            rated = [(m.customer_rating, m.reviews_count) for m in metrics if m.reviews_count > 0]
            if rated:
                total_reviews = sum(r[1] for r in rated)
                rating = sum(r[0] * r[1] for r in rated) / total_reviews if total_reviews > 0 else 0

        # Get hours from time clock entries
        entries = entries_by_staff.get(s.id, [])
        hours = sum(e.total_hours or 0 for e in entries)

        leaderboard.append({
            "rank": i + 1,
            "staff": {
                "id": s.id,
                "name": s.full_name,
                "role": s.role,
                "avatar_initials": "".join([n[0].upper() for n in s.full_name.split()[:2]]),
                "color": s.color or "#3B82F6",
            },
            "metrics": {
                "sales_amount": round(sales, 2),
                "orders_count": orders,
                "avg_ticket": round(sales / orders, 2) if orders > 0 else 0,
                "tips_received": round(tips, 2),
                "hours_worked": round(hours, 1),
                "sales_per_hour": round(sales / hours, 2) if hours > 0 else 0,
                "customer_rating": round(rating, 1),
                "reviews_count": reviews,
            },
            "change": 0,
        })

    # Sort by selected metric
    if sort_by == "sales":
        leaderboard.sort(key=lambda x: x["metrics"]["sales_amount"], reverse=True)
    elif sort_by == "orders":
        leaderboard.sort(key=lambda x: x["metrics"]["orders_count"], reverse=True)
    elif sort_by == "tips":
        leaderboard.sort(key=lambda x: x["metrics"]["tips_received"], reverse=True)
    elif sort_by == "rating":
        leaderboard.sort(key=lambda x: x["metrics"]["customer_rating"], reverse=True)

    # Update ranks
    for i, item in enumerate(leaderboard):
        item["rank"] = i + 1

    return leaderboard


@router.get("/staff/performance/goals")
@limiter.limit("60/minute")
def get_performance_goals(request: Request, db: DbSession):
    """Get performance goals."""
    try:
        goals = db.query(PerformanceGoal).all()
    except Exception as e:
        logger.warning(f"Failed to query performance goals: {e}")
        db.rollback()
        goals = []

    if not goals:
        return []

    return [
        {
            "id": g.id,
            "metric": g.metric,
            "target": g.target_value,
            "value": g.target_value,
            "current": g.current_value,
            "unit": g.unit,
            "period": g.period,
        }
        for g in goals
    ]


@router.put("/staff/performance/goals")
@limiter.limit("30/minute")
def update_performance_goals(request: Request, db: DbSession, current_user: RequireManager, data: List[dict] = Body(...)):
    """Update performance goals."""
    for goal_data in data:
        goal_id = goal_data.get("id")
        if goal_id:
            goal = db.query(PerformanceGoal).filter(PerformanceGoal.id == goal_id).first()
            if goal:
                goal.target_value = goal_data.get("target", goal.target_value)
                goal.current_value = goal_data.get("current", goal.current_value)
        else:
            # Create new goal
            goal = PerformanceGoal(
                metric=goal_data.get("metric", "New Goal"),
                target_value=goal_data.get("target", 0),
                current_value=goal_data.get("current", 0),
                unit=goal_data.get("unit", ""),
                period=goal_data.get("period", "day"),
            )
            db.add(goal)

    db.commit()
    return {"status": "success"}


# ============== Sections ==============

@router.get("/staff/sections/servers")
@limiter.limit("60/minute")
def get_servers_for_sections(request: Request, db: DbSession):
    """Get servers and bartenders for section assignment."""
    _init_default_staff(db)

    staff = db.query(StaffUser).filter(
        StaffUser.is_active == True,
        StaffUser.role.in_(["waiter", "bar"]),
    ).all()

    # Calculate current assignments and sales
    today = date.today()

    result = []
    for s in staff:
        # Get current table assignments
        assignments = db.query(TableAssignment).filter(
            TableAssignment.staff_id == s.id,
            TableAssignment.is_active == True,
        ).count()

        result.append({
            "id": s.id,
            "name": s.full_name,
            "avatar_initials": "".join([n[0].upper() for n in s.full_name.split()[:2]]),
            "color": s.color or "#3B82F6",
            "role": s.role,
            "status": "on_shift",  # Could check time clock
            "current_tables": assignments,
            "current_covers": assignments * 3,  # Estimate
            "sales_today": 0,  # Would need to calculate from orders
        })

    return result


@router.get("/tables/assignments")
@limiter.limit("60/minute")
def get_table_assignments(
    request: Request,
    db: DbSession,
    staff_user_id: Optional[int] = None,
):
    """Get table assignments."""
    query = db.query(TableAssignment).filter(TableAssignment.is_active == True)

    if staff_user_id:
        query = query.filter(TableAssignment.staff_id == staff_user_id)

    assignments = query.all()

    return [
        {
            "id": a.id,
            "staff_user_id": a.staff_id,
            "table_id": a.table_id,
            "area": a.area,
            "venue_id": a.location_id,
            "active": a.is_active,
        }
        for a in assignments
    ]


@router.post("/tables/assignments/bulk")
@limiter.limit("30/minute")
def bulk_assign_tables(request: Request, db: DbSession, data: dict = Body(...)):
    """Bulk assign tables to a staff member."""
    staff_id = data.get("staff_user_id")
    table_ids = data.get("table_ids", [])
    areas = data.get("areas", [])

    if not staff_id:
        raise HTTPException(status_code=400, detail="staff_user_id is required")

    staff = db.query(StaffUser).filter(StaffUser.id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    # Deactivate existing assignments
    db.query(TableAssignment).filter(
        TableAssignment.staff_id == staff_id
    ).update({"is_active": False})

    # Create new table assignments
    for table_id in table_ids:
        assignment = TableAssignment(
            staff_id=staff_id,
            table_id=table_id,
            is_active=True,
        )
        db.add(assignment)

    # Create area assignments
    for area in areas:
        assignment = TableAssignment(
            staff_id=staff_id,
            area=area,
            is_active=True,
        )
        db.add(assignment)

    db.commit()

    return {"status": "success", "tables_assigned": len(table_ids), "areas_assigned": len(areas)}


@router.post("/tables/sections/{section_id}/assign")
@limiter.limit("30/minute")
def assign_section(request: Request, db: DbSession, section_id: int, data: dict = Body(...)):
    """Assign a server to a section."""
    server_id = data.get("server_id")

    if not server_id:
        raise HTTPException(status_code=400, detail="server_id is required")

    # Create assignment for the section
    assignment = TableAssignment(
        staff_id=server_id,
        area=f"Section {section_id}",
        is_active=True,
    )
    db.add(assignment)
    db.commit()

    return {"status": "success", "section_id": section_id, "server_id": server_id}


# ============== Tips ==============

@router.get("/tips/pools")
@limiter.limit("60/minute")
def list_tip_pools(
    request: Request,
    db: DbSession,
    range: str = Query("week"),
):
    """List tip pools for a date range."""
    today = date.today()

    if range == "day":
        start_date = today
    elif range == "week":
        start_date = today - timedelta(days=7)
    elif range == "month":
        start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=7)

    pools = db.query(TipPool).filter(TipPool.date >= start_date).order_by(TipPool.date.desc()).all()

    result = []
    for p in pools:
        distributions = db.query(TipDistribution).filter(TipDistribution.pool_id == p.id).all()
        staff_ids = [d.staff_id for d in distributions]
        staff_names = _prefetch_staff_names(db, staff_ids)
        result.append({
            "id": p.id,
            "date": p.date.isoformat(),
            "shift": p.shift,
            "total_tips_cash": p.total_tips_cash,
            "total_tips_card": p.total_tips_card,
            "total_tips": p.total_tips,
            "participants": p.participants_count,
            "distribution_method": p.distribution_method,
            "status": p.status,
            "distributed_at": p.distributed_at.isoformat() if p.distributed_at else None,
            "distributions": [
                {
                    "staff_id": d.staff_id,
                    "staff_name": staff_names.get(d.staff_id, "Unknown"),
                    "role": "staff",
                    "hours_worked": d.hours_worked,
                    "points": d.points,
                    "share_percentage": d.share_percentage,
                    "amount": d.amount,
                    "paid": d.is_paid,
                }
                for d in distributions
            ],
        })

    return result


@router.post("/tips/pools")
@limiter.limit("30/minute")
def create_tip_pool(request: Request, db: DbSession, data: TipPoolCreate):
    """Create a new tip pool."""
    try:
        pool_date = datetime.strptime(data.date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    total_tips = data.total_tips_cash + data.total_tips_card

    pool = TipPool(
        date=pool_date,
        shift=data.shift,
        total_tips_cash=data.total_tips_cash,
        total_tips_card=data.total_tips_card,
        total_tips=total_tips,
        participants_count=len(data.participant_ids),
        distribution_method=data.distribution_method,
        status="pending",
    )
    db.add(pool)
    db.commit()
    db.refresh(pool)

    # Create distributions if participants specified
    if data.participant_ids:
        share = total_tips / len(data.participant_ids) if data.distribution_method == "equal" else 0
        for staff_id in data.participant_ids:
            dist = TipDistribution(
                pool_id=pool.id,
                staff_id=staff_id,
                share_percentage=100 / len(data.participant_ids),
                amount=share,
            )
            db.add(dist)
        db.commit()

    return {
        "id": pool.id,
        "date": pool.date.isoformat(),
        "total_tips": pool.total_tips,
        "status": pool.status,
    }


@router.get("/tips/stats")
@limiter.limit("60/minute")
def get_tip_stats(
    request: Request,
    db: DbSession,
    range: str = Query("week"),
):
    """Get tip statistics."""
    today = date.today()
    week_start = today - timedelta(days=7)
    month_start = today - timedelta(days=30)

    # Calculate stats from tip pools
    today_tips = db.query(func.sum(TipPool.total_tips)).filter(TipPool.date == today).scalar() or 0
    week_tips = db.query(func.sum(TipPool.total_tips)).filter(TipPool.date >= week_start).scalar() or 0
    month_tips = db.query(func.sum(TipPool.total_tips)).filter(TipPool.date >= month_start).scalar() or 0

    pending = db.query(func.sum(TipPool.total_tips)).filter(TipPool.status == "pending").scalar() or 0

    # Compute topEarner from actual tip distributions
    top_earner = None
    top = db.query(
        TipDistribution.staff_id,
        func.sum(TipDistribution.amount).label("total"),
    ).join(TipPool).filter(
        TipPool.date >= week_start,
    ).group_by(TipDistribution.staff_id).order_by(func.sum(TipDistribution.amount).desc()).first()

    if top:
        staff = db.query(StaffUser).filter(StaffUser.id == top.staff_id).first()
        if staff:
            top_earner = staff.full_name

    return {
        "totalTipsToday": float(today_tips),
        "totalTipsWeek": float(week_tips),
        "totalTipsMonth": float(month_tips),
        "avgTipPerHour": round(float(week_tips) / 168, 2) if week_tips else 0,
        "pendingDistribution": float(pending),
        "topEarner": top_earner,
    }


@router.get("/tips/earnings")
@limiter.limit("60/minute")
def get_tip_earnings(
    request: Request,
    db: DbSession,
    range: str = Query("week"),
):
    """Get individual tip earnings."""
    today = date.today()

    if range == "week":
        start_date = today - timedelta(days=7)
    elif range == "month":
        start_date = today - timedelta(days=30)
    else:
        start_date = today

    # Get distributions with staff info
    distributions = db.query(
        TipDistribution.staff_id,
        func.sum(TipDistribution.amount).label("total"),
        func.sum(TipDistribution.hours_worked).label("hours"),
    ).join(TipPool).filter(
        TipPool.date >= start_date
    ).group_by(TipDistribution.staff_id).all()

    # Calculate paid vs pending per staff
    paid_by_staff = {}
    pending_by_staff = {}
    paid_dists = db.query(
        TipDistribution.staff_id,
        func.sum(TipDistribution.amount).label("total"),
        TipDistribution.is_paid,
    ).join(TipPool).filter(
        TipPool.date >= start_date
    ).group_by(TipDistribution.staff_id, TipDistribution.is_paid).all()
    for pd in paid_dists:
        if pd.is_paid:
            paid_by_staff[pd.staff_id] = float(pd.total or 0)
        else:
            pending_by_staff[pd.staff_id] = float(pd.total or 0)

    result = []
    for d in distributions:
        staff = db.query(StaffUser).filter(StaffUser.id == d.staff_id).first()
        if staff:
            total = float(d.total or 0)
            paid_amt = paid_by_staff.get(d.staff_id, 0)
            pending_amt = pending_by_staff.get(d.staff_id, 0)
            result.append({
                "id": d.staff_id,
                "staff_id": d.staff_id,
                "name": staff.full_name,
                "staff_name": staff.full_name,
                "role": staff.role,
                "hours": float(d.hours or 0),
                "hours_worked": float(d.hours or 0),
                "earned": total,
                "total_tips": total,
                "pending": pending_amt,
                "paid": paid_amt,
                "avg_per_hour": round(total / float(d.hours or 1), 2),
            })

    return result


@router.post("/tips/distributions")
@limiter.limit("30/minute")
def distribute_tips(request: Request, db: DbSession, data: dict = Body(...)):
    """Distribute tips from a pool."""
    pool_id = data.get("pool_id")

    if not pool_id:
        raise HTTPException(status_code=400, detail="pool_id is required")

    pool = db.query(TipPool).filter(TipPool.id == pool_id).first()
    if not pool:
        raise HTTPException(status_code=404, detail="Tip pool not found")

    pool.status = "distributed"
    pool.distributed_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "success", "pool_id": pool_id}


