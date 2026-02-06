"""Risk Alerts / Fraud Detection API routes.

Provides fraud detection, risk scoring, and alert management
for the /fraud-detection frontend page.
"""

from typing import Optional
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/dashboard")
async def get_risk_dashboard():
    """Get fraud detection dashboard overview."""
    return {
        "cases": [
            {
                "id": "CASE-001", "title": "Suspicious void pattern", "staff_id": 3,
                "staff_name": "John D.", "status": "investigating", "severity": "high",
                "total_amount": 450.00, "alerts_count": 5, "created_at": "2026-02-01T10:00:00Z",
                "updated_at": "2026-02-03T14:30:00Z", "assigned_to": "Manager",
                "notes": [], "resolution": None,
            },
            {
                "id": "CASE-002", "title": "Excessive discounts", "staff_id": 7,
                "staff_name": "Maria S.", "status": "open", "severity": "medium",
                "total_amount": 180.00, "alerts_count": 3, "created_at": "2026-02-03T09:00:00Z",
                "updated_at": "2026-02-03T09:00:00Z", "assigned_to": None,
                "notes": [], "resolution": None,
            },
        ],
        "rules": [
            {"id": "R1", "name": "Void threshold", "condition": "voids > 5 per shift", "enabled": True},
            {"id": "R2", "name": "Discount abuse", "condition": "discount > 20% and > 3 times", "enabled": True},
            {"id": "R3", "name": "Cash shortage", "condition": "drawer variance > 10", "enabled": True},
        ],
    }


@router.get("/alerts")
async def get_risk_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(50, le=200),
):
    """Get fraud alerts."""
    alerts = [
        {
            "id": "ALT-001", "staff_id": 3, "staff_name": "John D.", "staff_photo": None,
            "alert_type": "excessive_voids", "severity": "high",
            "description": "5 voids in the last 2 hours totaling 150 lv",
            "amount": 150.00, "created_at": "2026-02-05T14:30:00Z",
            "acknowledged": False, "acknowledged_by": None, "acknowledged_at": None,
            "case_id": "CASE-001",
            "evidence": [
                {"type": "transaction", "timestamp": "2026-02-05T14:20:00Z", "description": "Void order #1234 - 35 lv"},
                {"type": "pos_log", "timestamp": "2026-02-05T14:25:00Z", "description": "Void order #1236 - 42 lv"},
            ],
            "transaction_id": "TXN-1234",
        },
        {
            "id": "ALT-002", "staff_id": 7, "staff_name": "Maria S.", "staff_photo": None,
            "alert_type": "discount_abuse", "severity": "medium",
            "description": "Applied 25% discount 4 times today without manager approval",
            "amount": 180.00, "created_at": "2026-02-05T12:00:00Z",
            "acknowledged": False, "acknowledged_by": None, "acknowledged_at": None,
            "case_id": "CASE-002",
            "evidence": [
                {"type": "transaction", "timestamp": "2026-02-05T11:30:00Z", "description": "25% discount on order #1220"},
            ],
            "transaction_id": "TXN-1220",
        },
        {
            "id": "ALT-003", "staff_id": 5, "staff_name": "Peter K.", "staff_photo": None,
            "alert_type": "cash_shortage", "severity": "low",
            "description": "Cash drawer short by 8.50 lv at shift end",
            "amount": 8.50, "created_at": "2026-02-04T22:00:00Z",
            "acknowledged": True, "acknowledged_by": "Manager", "acknowledged_at": "2026-02-05T09:00:00Z",
            "case_id": None,
            "evidence": [
                {"type": "pos_log", "timestamp": "2026-02-04T22:00:00Z", "description": "Drawer count: expected 1250, actual 1241.50"},
            ],
            "transaction_id": None,
        },
    ]

    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    if acknowledged is not None:
        alerts = [a for a in alerts if a["acknowledged"] == acknowledged]

    return alerts[:limit]


@router.get("/scores")
async def get_risk_scores():
    """Get staff risk scores."""
    return [
        {"staff_user_id": 3, "staff_name": "John D.", "position": "Waiter", "overall_risk_score": 72, "is_flagged": True, "flag_reason": "Excessive voids pattern"},
        {"staff_user_id": 7, "staff_name": "Maria S.", "position": "Cashier", "overall_risk_score": 55, "is_flagged": True, "flag_reason": "Discount abuse"},
        {"staff_user_id": 5, "staff_name": "Peter K.", "position": "Bartender", "overall_risk_score": 25, "is_flagged": False, "flag_reason": None},
        {"staff_user_id": 1, "staff_name": "Admin", "position": "Manager", "overall_risk_score": 5, "is_flagged": False, "flag_reason": None},
        {"staff_user_id": 8, "staff_name": "Elena V.", "position": "Waiter", "overall_risk_score": 12, "is_flagged": False, "flag_reason": None},
    ]


@router.get("/patterns")
async def get_fraud_patterns():
    """Get detected fraud patterns."""
    return [
        {
            "id": "PAT-001", "name": "Void & Re-ring",
            "description": "Staff voids an order and re-rings it at a lower price or with a discount",
            "frequency": 3, "total_amount": 250.00, "staff_involved": 1,
            "last_occurrence": "2026-02-05T14:30:00Z", "detection_rate": 85.0,
            "examples": ["Void #1234 then re-ring as #1235 with 15% discount"],
        },
        {
            "id": "PAT-002", "name": "Sweet-hearting",
            "description": "Staff gives free items or excessive discounts to friends/family",
            "frequency": 5, "total_amount": 180.00, "staff_involved": 2,
            "last_occurrence": "2026-02-05T12:00:00Z", "detection_rate": 60.0,
            "examples": ["Multiple 25% discounts to same customer phone number"],
        },
        {
            "id": "PAT-003", "name": "Skimming",
            "description": "Cash transactions not rung up or rung at lower amounts",
            "frequency": 1, "total_amount": 50.00, "staff_involved": 1,
            "last_occurrence": "2026-02-03T20:00:00Z", "detection_rate": 40.0,
            "examples": ["Camera shows cash payment but no POS transaction for table 5"],
        },
    ]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_risk_alert(alert_id: str):
    """Acknowledge a risk alert."""
    return {"success": True, "alert_id": alert_id}
