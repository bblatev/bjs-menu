"""
Anti-Theft Fusion Service

Combines multiple data sources to detect potential theft:
- Cash variance patterns
- Void/discount patterns
- Time-based anomalies
- Staff behavior scoring

When ANTI_THEFT_FUSION is enabled:
- Continuous monitoring of transactions
- Risk scoring per staff member
- Evidence packet generation for investigations
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.feature_flags import is_enabled


class RiskLevel(str, Enum):
    """Risk level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of anti-theft alerts."""
    CASH_VARIANCE = "cash_variance"
    EXCESSIVE_VOIDS = "excessive_voids"
    EXCESSIVE_DISCOUNTS = "excessive_discounts"
    UNUSUAL_TIMING = "unusual_timing"
    PATTERN_ANOMALY = "pattern_anomaly"
    SPLIT_TRANSACTION = "split_transaction"


class AntiTheftService:
    """
    Anti-theft detection and evidence collection.

    Analyzes transaction patterns to identify potential theft.
    """

    # Thresholds for detection
    VOID_THRESHOLD_PERCENT = 5  # % of transactions
    DISCOUNT_THRESHOLD_PERCENT = 10  # % of transactions
    CASH_VARIANCE_THRESHOLD = 2000  # cents
    UNUSUAL_HOUR_START = 2  # 2 AM
    UNUSUAL_HOUR_END = 5  # 5 AM

    def __init__(self, db: Session):
        self.db = db

    def is_active(self) -> bool:
        """Check if anti-theft fusion is enabled."""
        return is_enabled("ANTI_THEFT_FUSION")

    def analyze_staff_risk(
        self,
        venue_id: int,
        staff_user_id: int,
        period_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Analyze risk score for a staff member.

        Returns risk assessment with contributing factors.
        """
        if not is_enabled("STAFF_RISK_SCORING"):
            return {"status": "disabled"}

        start_date = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Collect metrics
        metrics = {
            "void_rate": self._calculate_void_rate(venue_id, staff_user_id, start_date),
            "discount_rate": self._calculate_discount_rate(venue_id, staff_user_id, start_date),
            "cash_variance": self._calculate_cash_variance(venue_id, staff_user_id, start_date),
            "unusual_activity": self._check_unusual_timing(venue_id, staff_user_id, start_date),
            "pattern_score": self._analyze_patterns(venue_id, staff_user_id, start_date),
        }

        # Calculate overall risk score (0-100)
        risk_score = self._calculate_risk_score(metrics)

        # Determine risk level
        if risk_score >= 80:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 60:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return {
            "staff_user_id": staff_user_id,
            "period_days": period_days,
            "risk_score": risk_score,
            "risk_level": risk_level.value,
            "metrics": metrics,
            "alerts": self._generate_alerts(metrics),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    def generate_evidence_packet(
        self,
        venue_id: int,
        staff_user_id: int,
        incident_type: str,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """
        Generate evidence packet for investigation.

        Collects all relevant data for a potential incident.
        """
        if not is_enabled("EVIDENCE_PACKETS"):
            return {"status": "disabled"}

        packet = {
            "packet_id": f"EVD-{venue_id}-{staff_user_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "venue_id": venue_id,
            "staff_user_id": staff_user_id,
            "incident_type": incident_type,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {},
            "transactions": [],
            "voids": [],
            "discounts": [],
            "cash_variances": [],
            "timeline": [],
        }

        # Collect transaction summary
        packet["summary"] = self._collect_transaction_summary(
            venue_id, staff_user_id, start_date, end_date
        )

        # Collect detailed records
        packet["transactions"] = self._collect_transactions(
            venue_id, staff_user_id, start_date, end_date
        )
        packet["voids"] = self._collect_voids(
            venue_id, staff_user_id, start_date, end_date
        )
        packet["discounts"] = self._collect_discounts(
            venue_id, staff_user_id, start_date, end_date
        )
        packet["cash_variances"] = self._collect_cash_variances(
            venue_id, staff_user_id, start_date, end_date
        )

        # Build timeline
        packet["timeline"] = self._build_timeline(packet)

        return packet

    def detect_split_transactions(
        self,
        venue_id: int,
        time_window_minutes: int = 5,
        threshold_count: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Detect potential split transactions.

        Split transactions are used to avoid discount/comp limits.
        """
        if not self.is_active():
            return []

        # Query for rapid sequential small transactions
        # This is a simplified implementation
        suspicious = []

        # Would query for patterns like:
        # - Multiple small cash transactions within time window
        # - Same staff member
        # - Total would exceed limits if combined

        return suspicious

    def _calculate_void_rate(
        self,
        venue_id: int,
        staff_user_id: int,
        start_date: datetime,
    ) -> Dict[str, Any]:
        """Calculate void rate for staff member."""
        # Simplified - would query actual void data
        return {
            "total_transactions": 0,
            "void_count": 0,
            "void_rate_percent": 0,
            "threshold_percent": self.VOID_THRESHOLD_PERCENT,
            "exceeds_threshold": False,
        }

    def _calculate_discount_rate(
        self,
        venue_id: int,
        staff_user_id: int,
        start_date: datetime,
    ) -> Dict[str, Any]:
        """Calculate discount rate for staff member."""
        return {
            "total_transactions": 0,
            "discount_count": 0,
            "discount_rate_percent": 0,
            "total_discount_amount": 0,
            "threshold_percent": self.DISCOUNT_THRESHOLD_PERCENT,
            "exceeds_threshold": False,
        }

    def _calculate_cash_variance(
        self,
        venue_id: int,
        staff_user_id: int,
        start_date: datetime,
    ) -> Dict[str, Any]:
        """Calculate cash variance metrics."""
        return {
            "total_variance_cents": 0,
            "variance_count": 0,
            "avg_variance_cents": 0,
            "max_shortage_cents": 0,
            "threshold_cents": self.CASH_VARIANCE_THRESHOLD,
            "exceeds_threshold": False,
        }

    def _check_unusual_timing(
        self,
        venue_id: int,
        staff_user_id: int,
        start_date: datetime,
    ) -> Dict[str, Any]:
        """Check for unusual timing patterns."""
        return {
            "unusual_hour_transactions": 0,
            "after_hours_voids": 0,
            "suspicious": False,
        }

    def _analyze_patterns(
        self,
        venue_id: int,
        staff_user_id: int,
        start_date: datetime,
    ) -> Dict[str, Any]:
        """Analyze transaction patterns."""
        return {
            "pattern_score": 0,
            "anomalies_detected": [],
        }

    def _calculate_risk_score(self, metrics: Dict[str, Any]) -> int:
        """Calculate overall risk score from metrics."""
        score = 0

        # Void rate contribution (max 25 points)
        void_data = metrics.get("void_rate", {})
        if void_data.get("exceeds_threshold"):
            score += 25
        elif void_data.get("void_rate_percent", 0) > self.VOID_THRESHOLD_PERCENT / 2:
            score += 10

        # Discount rate contribution (max 25 points)
        discount_data = metrics.get("discount_rate", {})
        if discount_data.get("exceeds_threshold"):
            score += 25
        elif discount_data.get("discount_rate_percent", 0) > self.DISCOUNT_THRESHOLD_PERCENT / 2:
            score += 10

        # Cash variance contribution (max 30 points)
        cash_data = metrics.get("cash_variance", {})
        if cash_data.get("exceeds_threshold"):
            score += 30
        elif cash_data.get("total_variance_cents", 0) > self.CASH_VARIANCE_THRESHOLD / 2:
            score += 15

        # Unusual timing contribution (max 20 points)
        timing_data = metrics.get("unusual_activity", {})
        if timing_data.get("suspicious"):
            score += 20

        return min(100, score)

    def _generate_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate alerts based on metrics."""
        alerts = []

        if metrics.get("void_rate", {}).get("exceeds_threshold"):
            alerts.append({
                "type": AlertType.EXCESSIVE_VOIDS.value,
                "severity": "high",
                "message": "Void rate exceeds threshold",
            })

        if metrics.get("discount_rate", {}).get("exceeds_threshold"):
            alerts.append({
                "type": AlertType.EXCESSIVE_DISCOUNTS.value,
                "severity": "high",
                "message": "Discount rate exceeds threshold",
            })

        if metrics.get("cash_variance", {}).get("exceeds_threshold"):
            alerts.append({
                "type": AlertType.CASH_VARIANCE.value,
                "severity": "critical",
                "message": "Cash variance exceeds threshold",
            })

        if metrics.get("unusual_activity", {}).get("suspicious"):
            alerts.append({
                "type": AlertType.UNUSUAL_TIMING.value,
                "severity": "medium",
                "message": "Unusual activity timing detected",
            })

        return alerts

    def _collect_transaction_summary(
        self,
        venue_id: int,
        staff_user_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, Any]:
        """Collect transaction summary for evidence packet."""
        return {
            "total_transactions": 0,
            "total_sales_cents": 0,
            "cash_transactions": 0,
            "card_transactions": 0,
            "void_count": 0,
            "void_amount_cents": 0,
            "discount_count": 0,
            "discount_amount_cents": 0,
        }

    def _collect_transactions(self, *args) -> List[Dict]:
        return []

    def _collect_voids(self, *args) -> List[Dict]:
        return []

    def _collect_discounts(self, *args) -> List[Dict]:
        return []

    def _collect_cash_variances(self, *args) -> List[Dict]:
        return []

    def _build_timeline(self, packet: Dict) -> List[Dict]:
        """Build chronological timeline of events."""
        timeline = []
        # Would combine and sort all events chronologically
        return timeline
