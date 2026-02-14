"""Risk Alerts / Fraud Detection API routes.

Provides fraud detection, risk scoring, and alert management
for the /fraud-detection frontend page.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import DbSession
from app.models.operations import RiskAlert
from app.core.rate_limit import limiter

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class RiskAlertOut(BaseModel):
    id: str
    staff_id: Optional[int] = None
    staff_name: Optional[str] = None
    staff_photo: Optional[str] = None
    alert_type: str
    severity: str
    description: Optional[str] = None
    amount: Optional[float] = None
    created_at: Optional[str] = None
    acknowledged: bool
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None
    case_id: Optional[str] = None
    evidence: List[dict] = []
    transaction_id: Optional[str] = None


class CaseOut(BaseModel):
    id: str
    title: str
    staff_id: Optional[int] = None
    staff_name: Optional[str] = None
    status: str
    severity: str
    total_amount: float
    alerts_count: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: List[dict] = []
    resolution: Optional[str] = None


class RuleOut(BaseModel):
    id: str
    name: str
    condition: str
    enabled: bool


class RiskScoreOut(BaseModel):
    staff_user_id: int
    staff_name: str
    position: Optional[str] = None
    overall_risk_score: float
    is_flagged: bool
    flag_reason: Optional[str] = None


class FraudPatternOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    frequency: int
    total_amount: float
    staff_involved: int
    last_occurrence: Optional[str] = None
    detection_rate: float
    examples: List[str] = []


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_alert(row: RiskAlert) -> dict:
    """Convert a RiskAlert DB row to the alert response dict."""
    details = row.details or {}
    return {
        "id": str(row.id),
        "staff_id": row.staff_id,
        "staff_name": row.staff_name,
        "staff_photo": details.get("staff_photo") if isinstance(details, dict) else None,
        "alert_type": row.type or "",
        "severity": row.severity or "medium",
        "description": row.description,
        "amount": float(row.amount) if row.amount is not None else None,
        "created_at": row.created_at.isoformat() + "Z" if row.created_at else None,
        "acknowledged": row.status in ("acknowledged", "resolved"),
        "acknowledged_by": row.acknowledged_by,
        "acknowledged_at": row.acknowledged_at.isoformat() + "Z" if row.acknowledged_at else None,
        "case_id": details.get("case_id") if isinstance(details, dict) else None,
        "evidence": details.get("evidence", []) if isinstance(details, dict) else [],
        "transaction_id": details.get("transaction_id") if isinstance(details, dict) else None,
    }


def _row_to_case(staff_id: int, rows: List[RiskAlert]) -> dict:
    """Aggregate a group of RiskAlert rows for one staff member into a case dict."""
    first = rows[0]
    details_first = first.details or {}
    latest = max(rows, key=lambda r: r.created_at or datetime.min)
    total = sum(float(r.amount) for r in rows if r.amount is not None)

    # Derive case status from component alerts
    statuses = {r.status for r in rows}
    if "open" in statuses:
        case_status = "investigating" if any(s in statuses for s in ("acknowledged", "resolved")) else "open"
    elif "acknowledged" in statuses:
        case_status = "investigating"
    else:
        case_status = "resolved"

    # Severity = worst severity among alerts
    sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    worst = max(rows, key=lambda r: sev_order.get(r.severity or "low", 0))

    return {
        "id": f"CASE-{staff_id:03d}",
        "title": first.title or first.description or "Risk alert",
        "staff_id": staff_id,
        "staff_name": first.staff_name,
        "status": case_status,
        "severity": worst.severity or "medium",
        "total_amount": round(total, 2),
        "alerts_count": len(rows),
        "created_at": first.created_at.isoformat() + "Z" if first.created_at else None,
        "updated_at": latest.created_at.isoformat() + "Z" if latest.created_at else None,
        "assigned_to": details_first.get("assigned_to") if isinstance(details_first, dict) else None,
        "notes": details_first.get("notes", []) if isinstance(details_first, dict) else [],
        "resolution": details_first.get("resolution") if isinstance(details_first, dict) else None,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
@limiter.limit("60/minute")
async def get_risk_dashboard(request: Request, db: DbSession):
    """Get fraud detection dashboard overview."""
    # Build cases by grouping non-dismissed alerts by staff_id
    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.status.notin_(["dismissed"]))
        .order_by(RiskAlert.created_at.asc())
        .all()
    )

    staff_groups: dict[int, List[RiskAlert]] = {}
    for a in alerts:
        if a.staff_id is not None:
            staff_groups.setdefault(a.staff_id, []).append(a)

    cases = [_row_to_case(sid, rows) for sid, rows in staff_groups.items()]

    # Rules: extract distinct alert types and present as detection rules
    type_rows = db.query(RiskAlert.type).distinct().all()
    alert_types = [r[0] for r in type_rows if r[0]]

    rule_map = {
        "void_pattern": {"name": "Void threshold", "condition": "voids > 5 per shift"},
        "discount_abuse": {"name": "Discount abuse", "condition": "discount > 20% and > 3 times"},
        "cash_variance": {"name": "Cash shortage", "condition": "drawer variance > 10"},
        "time_theft": {"name": "Time theft", "condition": "clock discrepancy > 15 min"},
    }

    rules = []
    for idx, at in enumerate(alert_types, start=1):
        info = rule_map.get(at, {"name": at.replace("_", " ").title(), "condition": at})
        rules.append({
            "id": f"R{idx}",
            "name": info["name"],
            "condition": info["condition"],
            "enabled": True,
        })

    # If no types found in DB, return default rules so the UI is never empty
    if not rules:
        rules = [
            {"id": "R1", "name": "Void threshold", "condition": "voids > 5 per shift", "enabled": True},
            {"id": "R2", "name": "Discount abuse", "condition": "discount > 20% and > 3 times", "enabled": True},
            {"id": "R3", "name": "Cash shortage", "condition": "drawer variance > 10", "enabled": True},
        ]

    return {"cases": cases, "rules": rules}


@router.get("/alerts")
@limiter.limit("60/minute")
async def get_risk_alerts(
    request: Request,
    db: DbSession,
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(50, le=200),
):
    """Get fraud alerts."""
    query = db.query(RiskAlert)

    if severity:
        query = query.filter(RiskAlert.severity == severity)
    if acknowledged is True:
        query = query.filter(RiskAlert.status.in_(["acknowledged", "resolved"]))
    elif acknowledged is False:
        query = query.filter(RiskAlert.status.notin_(["acknowledged", "resolved"]))

    rows = query.order_by(RiskAlert.created_at.desc()).limit(limit).all()
    return [_row_to_alert(r) for r in rows]


@router.get("/scores")
@limiter.limit("60/minute")
async def get_risk_scores(request: Request, db: DbSession):
    """Get staff risk scores."""
    # Compute a risk score per staff member based on alert count and severity
    rows = (
        db.query(RiskAlert)
        .filter(RiskAlert.staff_id.isnot(None))
        .all()
    )

    staff_data: dict[int, dict] = {}
    sev_weight = {"critical": 25, "high": 15, "medium": 8, "low": 3}

    for r in rows:
        sid = r.staff_id
        if sid not in staff_data:
            details = r.details or {}
            staff_data[sid] = {
                "staff_user_id": sid,
                "staff_name": r.staff_name or f"Staff #{sid}",
                "position": details.get("position") if isinstance(details, dict) else None,
                "score": 0,
                "flag_reason": None,
            }
        weight = sev_weight.get(r.severity or "low", 3)
        staff_data[sid]["score"] += weight
        # Keep the reason from the highest-severity alert
        if staff_data[sid]["flag_reason"] is None or weight > sev_weight.get("medium", 8):
            staff_data[sid]["flag_reason"] = r.title or r.description

    results = []
    for info in staff_data.values():
        score = min(info["score"], 100)
        results.append({
            "staff_user_id": info["staff_user_id"],
            "staff_name": info["staff_name"],
            "position": info["position"],
            "overall_risk_score": score,
            "is_flagged": score >= 50,
            "flag_reason": info["flag_reason"] if score >= 50 else None,
        })

    results.sort(key=lambda x: x["overall_risk_score"], reverse=True)
    return results


@router.get("/patterns")
@limiter.limit("60/minute")
async def get_fraud_patterns(request: Request, db: DbSession):
    """Get detected fraud patterns."""
    # Group alerts by type to detect patterns
    rows = db.query(RiskAlert).order_by(RiskAlert.created_at.desc()).all()

    type_groups: dict[str, List[RiskAlert]] = {}
    for r in rows:
        atype = r.type or "unknown"
        type_groups.setdefault(atype, []).append(r)

    pattern_names = {
        "void_pattern": "Void & Re-ring",
        "discount_abuse": "Sweet-hearting",
        "cash_variance": "Skimming",
        "time_theft": "Time theft",
    }

    patterns = []
    for idx, (atype, group) in enumerate(type_groups.items(), start=1):
        total_amount = sum(float(r.amount) for r in group if r.amount is not None)
        staff_ids = {r.staff_id for r in group if r.staff_id is not None}
        latest = group[0]  # already sorted desc

        # Gather example descriptions
        examples = []
        for r in group[:3]:
            if r.description:
                examples.append(r.description)

        patterns.append({
            "id": f"PAT-{idx:03d}",
            "name": pattern_names.get(atype, atype.replace("_", " ").title()),
            "description": latest.description or "",
            "frequency": len(group),
            "total_amount": round(total_amount, 2),
            "staff_involved": len(staff_ids),
            "last_occurrence": latest.created_at.isoformat() + "Z" if latest.created_at else None,
            "detection_rate": round(min(len(group) * 20.0, 100.0), 1),
            "examples": examples,
        })

    return patterns


@router.post("/alerts/{alert_id}/acknowledge")
@limiter.limit("30/minute")
async def acknowledge_risk_alert(request: Request, alert_id: str, db: DbSession):
    """Acknowledge a risk alert."""
    alert = db.query(RiskAlert).filter(RiskAlert.id == int(alert_id)).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    alert.acknowledged_by = "Manager"
    db.commit()
    db.refresh(alert)

    return {"success": True, "alert_id": str(alert.id)}
