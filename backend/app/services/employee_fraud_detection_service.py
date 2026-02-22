"""
Employee Fraud Detection Service - Enterprise Grade
Implements NCR Aloha-style Employee Fraud Index with ML anomaly detection

Features:
- Real-time transaction monitoring
- Behavioral pattern analysis
- Fraud risk scoring (0-100)
- Automated alerts for suspicious activity
- Void/discount pattern detection
- Cash handling anomalies
- Time clock fraud detection
- Manager override tracking
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy.orm import Session
from enum import Enum
import statistics
import math

logger = logging.getLogger(__name__)


class FraudCategory(str, Enum):
    VOID_ABUSE = "void_abuse"
    DISCOUNT_ABUSE = "discount_abuse"
    CASH_HANDLING = "cash_handling"
    TIME_FRAUD = "time_fraud"
    REFUND_ABUSE = "refund_abuse"
    SWEET_HEARTING = "sweet_hearting"  # Giving away items
    SKIMMING = "skimming"  # Not ringing up sales
    MANAGER_OVERRIDE = "manager_override_abuse"
    TIP_MANIPULATION = "tip_manipulation"
    INVENTORY_THEFT = "inventory_theft"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmployeeFraudDetectionService:
    """
    ML-powered employee fraud detection matching NCR Aloha's Fraud Index.
    Monitors transactions, behaviors, and patterns to identify potential fraud.
    """
    
    # Default threshold values
    DEFAULT_THRESHOLDS = {
        "void_rate_threshold": 5.0,  # % of transactions
        "discount_rate_threshold": 15.0,  # % of sales
        "cash_variance_threshold": 50.0,  # EUR
        "refund_rate_threshold": 3.0,  # % of transactions
        "manager_override_threshold": 10,  # per shift
        "unusual_hours_threshold": 2,  # hours before/after shift
        "short_transaction_threshold": 30,  # seconds
        "high_value_void_threshold": 50.0,  # EUR
        "consecutive_voids_threshold": 3,
        "tip_adjustment_threshold": 5  # per shift
    }

    def __init__(self, db: Session, thresholds: Optional[Dict[str, Any]] = None):
        self.db = db
        self.baseline_metrics = {}  # Store baseline metrics per venue
        self.alerts = []  # Active alerts
        self.fraud_scores = {}  # Current fraud scores by employee

        # Configurable thresholds: merge defaults with any provided overrides
        self.thresholds = dict(self.DEFAULT_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)
    
    # ==================== FRAUD INDEX CALCULATION ====================
    
    def calculate_fraud_index(
        self,
        staff_id: int,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive Fraud Index score (0-100) for an employee
        Similar to NCR Aloha's Employee Fraud Index
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=period_days)
        
        # Get employee transaction data
        transactions = self._get_employee_transactions(staff_id, start_date, end_date)
        voids = self._get_employee_voids(staff_id, start_date, end_date)
        discounts = self._get_employee_discounts(staff_id, start_date, end_date)
        refunds = self._get_employee_refunds(staff_id, start_date, end_date)
        cash_reports = self._get_employee_cash_reports(staff_id, start_date, end_date)
        time_entries = self._get_employee_time_entries(staff_id, start_date, end_date)
        
        # Calculate individual risk scores
        scores = {
            "void_risk": self._calculate_void_risk(transactions, voids),
            "discount_risk": self._calculate_discount_risk(transactions, discounts),
            "cash_handling_risk": self._calculate_cash_risk(cash_reports),
            "refund_risk": self._calculate_refund_risk(transactions, refunds),
            "time_fraud_risk": self._calculate_time_fraud_risk(time_entries),
            "pattern_anomaly_risk": self._calculate_pattern_anomaly_risk(staff_id, transactions),
            "manager_override_risk": self._calculate_manager_override_risk(staff_id, start_date, end_date)
        }
        
        # Weight the scores
        weights = {
            "void_risk": 0.20,
            "discount_risk": 0.15,
            "cash_handling_risk": 0.25,
            "refund_risk": 0.10,
            "time_fraud_risk": 0.10,
            "pattern_anomaly_risk": 0.10,
            "manager_override_risk": 0.10
        }
        
        # Calculate weighted fraud index
        fraud_index = sum(
            scores[key] * weights[key]
            for key in scores
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(fraud_index)
        
        # Get specific concerns
        concerns = self._identify_specific_concerns(scores)
        
        # Compare to peer average
        peer_comparison = self._compare_to_peers(staff_id, fraud_index)
        
        result = {
            "staff_id": staff_id,
            "fraud_index": round(fraud_index, 1),
            "risk_level": risk_level,
            "category_scores": scores,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": period_days
            },
            "concerns": concerns,
            "peer_comparison": peer_comparison,
            "trend": self._calculate_trend(staff_id, fraud_index),
            "recommendations": self._get_recommendations(scores, concerns),
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store the score in memory
        self.fraud_scores[staff_id] = result

        # Save to database
        self._save_fraud_score_to_db(staff_id, result, scores, start_date, end_date, len(transactions))

        # Generate alerts if needed
        if fraud_index >= 70:
            self._generate_fraud_alert(staff_id, result, AlertSeverity.CRITICAL)
        elif fraud_index >= 50:
            self._generate_fraud_alert(staff_id, result, AlertSeverity.HIGH)
        elif fraud_index >= 30:
            self._generate_fraud_alert(staff_id, result, AlertSeverity.MEDIUM)

        return result
    
    def _calculate_void_risk(
        self,
        transactions: List[Dict],
        voids: List[Dict]
    ) -> float:
        """Calculate void abuse risk score (0-100)"""
        if not transactions:
            return 0
        
        total_trans = len(transactions)
        total_voids = len(voids)
        
        # Base void rate
        void_rate = (total_voids / total_trans) * 100 if total_trans else 0
        
        # Check for patterns
        void_score = 0
        
        # 1. High void rate
        if void_rate > self.thresholds["void_rate_threshold"]:
            void_score += min(40, (void_rate - self.thresholds["void_rate_threshold"]) * 5)
        
        # 2. High-value voids
        high_value_voids = [v for v in voids if v.get("amount", 0) > self.thresholds["high_value_void_threshold"]]
        if high_value_voids:
            void_score += min(20, len(high_value_voids) * 5)
        
        # 3. Consecutive voids (same order voided multiple times)
        consecutive = self._detect_consecutive_voids(voids)
        if consecutive:
            void_score += 20
        
        # 4. End-of-shift voids
        end_shift_voids = self._detect_end_of_shift_voids(voids)
        if end_shift_voids:
            void_score += min(20, len(end_shift_voids) * 5)
        
        # 5. Voids after payment
        post_payment_voids = [v for v in voids if v.get("after_payment", False)]
        if post_payment_voids:
            void_score += min(20, len(post_payment_voids) * 10)
        
        return min(100, void_score)
    
    def _calculate_discount_risk(
        self,
        transactions: List[Dict],
        discounts: List[Dict]
    ) -> float:
        """Calculate discount abuse risk score (0-100)"""
        if not transactions:
            return 0
        
        total_sales = sum(t.get("total", 0) for t in transactions)
        total_discounts = sum(d.get("amount", 0) for d in discounts)
        
        discount_rate = (total_discounts / total_sales) * 100 if total_sales else 0
        
        discount_score = 0
        
        # 1. High discount rate
        if discount_rate > self.thresholds["discount_rate_threshold"]:
            discount_score += min(30, (discount_rate - self.thresholds["discount_rate_threshold"]) * 3)
        
        # 2. Unauthorized discounts (no manager approval)
        unauthorized = [d for d in discounts if not d.get("manager_approved", True)]
        if unauthorized:
            discount_score += min(30, len(unauthorized) * 5)
        
        # 3. Discounts to same customers
        repeat_customers = self._detect_repeat_discount_customers(discounts)
        if repeat_customers:
            discount_score += 20
        
        # 4. Maximum discounts frequently applied
        max_discounts = [d for d in discounts if d.get("percentage", 0) >= 50]
        if max_discounts:
            discount_score += min(20, len(max_discounts) * 5)
        
        return min(100, discount_score)
    
    def _calculate_cash_risk(self, cash_reports: List[Dict]) -> float:
        """Calculate cash handling risk score (0-100)"""
        if not cash_reports:
            return 0
        
        cash_score = 0
        
        # 1. Cash shortages
        shortages = [r for r in cash_reports if r.get("variance", 0) < -5]
        if shortages:
            total_shortage = abs(sum(r.get("variance", 0) for r in shortages))
            cash_score += min(40, total_shortage / 5)
        
        # 2. Frequent small discrepancies (possible skimming)
        small_variances = [r for r in cash_reports if -20 < r.get("variance", 0) < -5]
        if len(small_variances) > 3:
            cash_score += 30
        
        # 3. Cash overages (possible float manipulation)
        overages = [r for r in cash_reports if r.get("variance", 0) > 10]
        if overages:
            cash_score += min(15, len(overages) * 5)
        
        # 4. No-sale opens
        no_sales = sum(r.get("no_sale_count", 0) for r in cash_reports)
        if no_sales > 10:
            cash_score += min(20, no_sales - 10)
        
        return min(100, cash_score)
    
    def _calculate_refund_risk(
        self,
        transactions: List[Dict],
        refunds: List[Dict]
    ) -> float:
        """Calculate refund abuse risk score (0-100)"""
        if not transactions:
            return 0
        
        refund_rate = (len(refunds) / len(transactions)) * 100
        
        refund_score = 0
        
        # 1. High refund rate
        if refund_rate > self.thresholds["refund_rate_threshold"]:
            refund_score += min(40, (refund_rate - self.thresholds["refund_rate_threshold"]) * 10)
        
        # 2. Cash refunds without receipt
        no_receipt = [r for r in refunds if not r.get("has_receipt", True)]
        if no_receipt:
            refund_score += min(30, len(no_receipt) * 10)
        
        # 3. Refunds to same tender type
        same_tender = self._detect_refund_tender_patterns(refunds)
        if same_tender:
            refund_score += 20
        
        # 4. Refunds after close
        after_close = [r for r in refunds if r.get("after_business_hours", False)]
        if after_close:
            refund_score += min(20, len(after_close) * 10)
        
        return min(100, refund_score)
    
    def _calculate_time_fraud_risk(self, time_entries: List[Dict]) -> float:
        """Calculate time clock fraud risk score (0-100)"""
        if not time_entries:
            return 0
        
        time_score = 0
        
        # 1. Buddy punching indicators (unusual clock-in locations)
        unusual_locations = [e for e in time_entries if e.get("unusual_location", False)]
        if unusual_locations:
            time_score += min(25, len(unusual_locations) * 5)
        
        # 2. Excessive overtime
        total_overtime = sum(e.get("overtime_hours", 0) for e in time_entries)
        if total_overtime > 20:
            time_score += min(20, total_overtime - 20)
        
        # 3. Missed punches (manual corrections)
        missed_punches = [e for e in time_entries if e.get("manual_correction", False)]
        if len(missed_punches) > 5:
            time_score += min(25, (len(missed_punches) - 5) * 5)
        
        # 4. Early clock-in / late clock-out patterns
        padding = self._detect_time_padding(time_entries)
        if padding:
            time_score += min(30, padding * 5)
        
        return min(100, time_score)
    
    def _calculate_pattern_anomaly_risk(
        self,
        staff_id: int,
        transactions: List[Dict]
    ) -> float:
        """Calculate behavioral pattern anomaly risk score (0-100)"""
        if not transactions:
            return 0
        
        anomaly_score = 0
        
        # 1. Unusual transaction timing
        timing_anomalies = self._detect_timing_anomalies(transactions)
        anomaly_score += min(25, timing_anomalies * 5)
        
        # 2. Transaction velocity changes
        velocity_change = self._detect_velocity_changes(transactions)
        if velocity_change > 0.5:  # 50% change from baseline
            anomaly_score += min(25, velocity_change * 20)
        
        # 3. Average ticket deviation
        ticket_deviation = self._calculate_ticket_deviation(staff_id, transactions)
        if ticket_deviation > 2:  # 2 standard deviations
            anomaly_score += min(25, ticket_deviation * 10)
        
        # 4. Suspicious item combinations
        suspicious_combos = self._detect_suspicious_combos(transactions)
        anomaly_score += min(25, suspicious_combos * 10)
        
        return min(100, anomaly_score)
    
    def _calculate_manager_override_risk(
        self,
        staff_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """Calculate manager override abuse risk score (0-100)"""
        overrides = self._get_manager_overrides(staff_id, start_date, end_date)
        
        if not overrides:
            return 0
        
        override_score = 0
        
        # 1. High frequency of overrides requested
        override_count = len(overrides)
        if override_count > self.thresholds["manager_override_threshold"] * 7:  # Per week
            override_score += min(40, (override_count - self.thresholds["manager_override_threshold"] * 7) * 2)
        
        # 2. Same manager always approving
        managers = [o.get("manager_id") for o in overrides]
        if managers and len(set(managers)) == 1 and len(managers) > 10:
            override_score += 30  # Possible collusion
        
        # 3. Self-approvals (if somehow possible)
        self_approvals = [o for o in overrides if o.get("manager_id") == staff_id]
        if self_approvals:
            override_score += 30
        
        return min(100, override_score)
    
    # ==================== REAL-TIME MONITORING ====================
    
    def monitor_transaction(
        self,
        transaction: Dict,
        staff_id: int
    ) -> Dict[str, Any]:
        """
        Monitor a transaction in real-time for fraud indicators
        Called after each transaction is processed
        """
        alerts = []
        risk_factors = []
        
        # Check void on recently closed order
        if transaction.get("is_void") and transaction.get("minutes_since_order", 0) > 30:
            alerts.append({
                "type": FraudCategory.VOID_ABUSE.value,
                "severity": AlertSeverity.MEDIUM.value,
                "message": "Void on order older than 30 minutes"
            })
            risk_factors.append("late_void")
        
        # Check high-value void
        if transaction.get("is_void") and transaction.get("amount", 0) > self.thresholds["high_value_void_threshold"]:
            alerts.append({
                "type": FraudCategory.VOID_ABUSE.value,
                "severity": AlertSeverity.HIGH.value,
                "message": f"High-value void: €{transaction.get('amount', 0):.2f}"
            })
            risk_factors.append("high_value_void")
        
        # Check unusual discount
        if transaction.get("discount_percentage", 0) > 50:
            alerts.append({
                "type": FraudCategory.DISCOUNT_ABUSE.value,
                "severity": AlertSeverity.MEDIUM.value,
                "message": f"Large discount applied: {transaction.get('discount_percentage')}%"
            })
            risk_factors.append("large_discount")
        
        # Check for suspicious timing
        if self._is_suspicious_time(transaction):
            alerts.append({
                "type": FraudCategory.SKIMMING.value,
                "severity": AlertSeverity.LOW.value,
                "message": "Transaction during unusual hours"
            })
            risk_factors.append("unusual_timing")
        
        # Check for no-sale
        if transaction.get("is_no_sale"):
            recent_no_sales = self._get_recent_no_sales(staff_id, minutes=60)
            if recent_no_sales > 3:
                alerts.append({
                    "type": FraudCategory.CASH_HANDLING.value,
                    "severity": AlertSeverity.MEDIUM.value,
                    "message": f"Multiple no-sale drawer opens: {recent_no_sales} in last hour"
                })
                risk_factors.append("frequent_no_sales")
        
        # Calculate real-time risk
        risk_score = len(risk_factors) * 20
        
        # Store alerts if any
        for alert in alerts:
            self._generate_fraud_alert(staff_id, {"transaction": transaction, "alert": alert}, 
                                      AlertSeverity(alert["severity"]))
        
        return {
            "transaction_id": transaction.get("id"),
            "staff_id": staff_id,
            "risk_score": min(100, risk_score),
            "risk_factors": risk_factors,
            "alerts": alerts,
            "requires_review": risk_score >= 40,
            "requires_immediate_action": risk_score >= 80
        }
    
    def monitor_shift_activity(
        self,
        staff_id: int,
        shift_id: str
    ) -> Dict[str, Any]:
        """
        Monitor ongoing shift for fraud patterns
        Called periodically during a shift
        """
        shift_start = self._get_shift_start_time(shift_id)
        transactions = self._get_transactions_since(staff_id, shift_start)
        
        metrics = {
            "transaction_count": len(transactions),
            "void_count": len([t for t in transactions if t.get("is_void")]),
            "discount_count": len([t for t in transactions if t.get("has_discount")]),
            "refund_count": len([t for t in transactions if t.get("is_refund")]),
            "total_sales": sum(t.get("total", 0) for t in transactions),
            "total_voids": sum(t.get("void_amount", 0) for t in transactions if t.get("is_void")),
            "total_discounts": sum(t.get("discount_amount", 0) for t in transactions if t.get("has_discount"))
        }
        
        # Compare to baseline
        baseline = self._get_staff_baseline(staff_id)
        anomalies = []
        
        if baseline:
            # Check void rate
            current_void_rate = (metrics["void_count"] / max(1, metrics["transaction_count"])) * 100
            if current_void_rate > baseline.get("avg_void_rate", 0) * 2:
                anomalies.append({
                    "type": "high_void_rate",
                    "current": current_void_rate,
                    "baseline": baseline.get("avg_void_rate", 0)
                })
            
            # Check discount rate
            current_discount_rate = (metrics["total_discounts"] / max(1, metrics["total_sales"])) * 100
            if current_discount_rate > baseline.get("avg_discount_rate", 0) * 1.5:
                anomalies.append({
                    "type": "high_discount_rate",
                    "current": current_discount_rate,
                    "baseline": baseline.get("avg_discount_rate", 0)
                })
        
        return {
            "shift_id": shift_id,
            "staff_id": staff_id,
            "shift_duration_minutes": self._calculate_shift_duration(shift_start),
            "metrics": metrics,
            "anomalies": anomalies,
            "risk_level": "high" if anomalies else "normal",
            "requires_attention": len(anomalies) > 0
        }
    
    # ==================== ALERTS & REPORTING ====================
    
    def get_active_alerts(
        self,
        venue_id: Optional[int] = None,
        severity: Optional[AlertSeverity] = None,
        category: Optional[FraudCategory] = None
    ) -> List[Dict[str, Any]]:
        """Get active fraud alerts"""
        alerts = self.alerts
        
        if venue_id:
            alerts = [a for a in alerts if a.get("venue_id") == venue_id]
        
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity.value]
        
        if category:
            alerts = [a for a in alerts if a.get("category") == category.value]
        
        return sorted(alerts, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: int,
        action_taken: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Acknowledge and optionally act on a fraud alert"""
        alert = next((a for a in self.alerts if a.get("alert_id") == alert_id), None)
        
        if not alert:
            return {"success": False, "error": "Alert not found"}
        
        alert["acknowledged"] = True
        alert["acknowledged_at"] = datetime.now(timezone.utc).isoformat()
        alert["acknowledged_by"] = acknowledged_by
        alert["action_taken"] = action_taken
        alert["notes"] = notes
        
        return {
            "success": True,
            "alert_id": alert_id,
            "status": "acknowledged"
        }
    
    def get_fraud_dashboard(
        self,
        venue_id: int,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get comprehensive fraud detection dashboard
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=period_days)
        
        # Get all staff fraud indexes
        staff_list = self._get_venue_staff(venue_id)
        fraud_indexes = []
        
        for staff in staff_list:
            index = self.calculate_fraud_index(staff["id"], period_days)
            fraud_indexes.append({
                "staff_id": staff["id"],
                "name": staff.get("name", "Unknown"),
                "role": staff.get("role", ""),
                "fraud_index": index["fraud_index"],
                "risk_level": index["risk_level"],
                "top_concern": index["concerns"][0] if index["concerns"] else None
            })
        
        # Sort by fraud index
        fraud_indexes.sort(key=lambda x: x["fraud_index"], reverse=True)
        
        # Get alerts summary
        venue_alerts = [a for a in self.alerts if a.get("venue_id") == venue_id]
        alerts_by_category = {}
        for category in FraudCategory:
            category_alerts = [a for a in venue_alerts if a.get("category") == category.value]
            alerts_by_category[category.value] = len(category_alerts)
        
        # Calculate venue-wide metrics
        all_transactions = self._get_venue_transactions(venue_id, start_date, end_date)
        all_voids = self._get_venue_voids(venue_id, start_date, end_date)
        
        venue_void_rate = (len(all_voids) / max(1, len(all_transactions))) * 100
        
        return {
            "venue_id": venue_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": period_days
            },
            "summary": {
                "staff_count": len(staff_list),
                "high_risk_count": len([f for f in fraud_indexes if f["risk_level"] == "high"]),
                "medium_risk_count": len([f for f in fraud_indexes if f["risk_level"] == "medium"]),
                "active_alerts": len([a for a in venue_alerts if not a.get("acknowledged")]),
                "venue_void_rate": round(venue_void_rate, 2)
            },
            "top_risk_employees": fraud_indexes[:5],
            "alerts_by_category": alerts_by_category,
            "recent_alerts": sorted(venue_alerts, key=lambda x: x.get("created_at", ""), reverse=True)[:10],
            "trend": self._calculate_venue_fraud_trend(venue_id, period_days),
            "recommendations": self._get_venue_recommendations(fraud_indexes, venue_alerts)
        }
    
    def generate_fraud_report(
        self,
        venue_id: int,
        staff_id: Optional[int] = None,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Generate detailed fraud investigation report
        """
        if not end_date:
            end_date = datetime.now(timezone.utc)
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        if staff_id:
            # Individual employee report
            return self._generate_employee_fraud_report(staff_id, start_date, end_date)
        else:
            # Venue-wide report
            return self._generate_venue_fraud_report(venue_id, start_date, end_date)
    
    def _generate_employee_fraud_report(
        self,
        staff_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Generate detailed fraud report for an employee"""
        fraud_index = self.calculate_fraud_index(staff_id, (end_date - start_date).days)
        
        # Get all relevant data
        transactions = self._get_employee_transactions(staff_id, start_date, end_date)
        voids = self._get_employee_voids(staff_id, start_date, end_date)
        discounts = self._get_employee_discounts(staff_id, start_date, end_date)
        refunds = self._get_employee_refunds(staff_id, start_date, end_date)
        
        # Detailed breakdowns
        void_analysis = self._analyze_voids_detail(voids)
        discount_analysis = self._analyze_discounts_detail(discounts)
        pattern_analysis = self._analyze_patterns_detail(transactions)
        
        return {
            "report_type": "employee_fraud_investigation",
            "staff_id": staff_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "fraud_index": fraud_index,
            "transaction_summary": {
                "total_transactions": len(transactions),
                "total_sales": sum(t.get("total", 0) for t in transactions),
                "void_count": len(voids),
                "void_amount": sum(v.get("amount", 0) for v in voids),
                "discount_count": len(discounts),
                "discount_amount": sum(d.get("amount", 0) for d in discounts),
                "refund_count": len(refunds),
                "refund_amount": sum(r.get("amount", 0) for r in refunds)
            },
            "void_analysis": void_analysis,
            "discount_analysis": discount_analysis,
            "pattern_analysis": pattern_analysis,
            "related_alerts": [a for a in self.alerts if a.get("staff_id") == staff_id],
            "investigation_recommendations": self._get_investigation_recommendations(fraud_index),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    # ==================== HELPER METHODS ====================
    
    def _determine_risk_level(self, fraud_index: float) -> str:
        """Determine risk level from fraud index"""
        if fraud_index >= 70:
            return "critical"
        elif fraud_index >= 50:
            return "high"
        elif fraud_index >= 30:
            return "medium"
        elif fraud_index >= 15:
            return "low"
        else:
            return "normal"
    
    def _identify_specific_concerns(self, scores: Dict[str, float]) -> List[str]:
        """Identify specific concerns from category scores"""
        concerns = []
        
        if scores["void_risk"] >= 50:
            concerns.append("High void activity - possible theft or error patterns")
        if scores["discount_risk"] >= 50:
            concerns.append("Excessive discounting - possible unauthorized discounts")
        if scores["cash_handling_risk"] >= 50:
            concerns.append("Cash handling issues - variances detected")
        if scores["refund_risk"] >= 50:
            concerns.append("High refund rate - review refund legitimacy")
        if scores["time_fraud_risk"] >= 50:
            concerns.append("Time clock irregularities - possible time fraud")
        if scores["pattern_anomaly_risk"] >= 50:
            concerns.append("Behavioral anomalies detected")
        if scores["manager_override_risk"] >= 50:
            concerns.append("Excessive manager overrides requested")
        
        return concerns
    
    def _compare_to_peers(self, staff_id: int, fraud_index: float) -> Dict[str, Any]:
        """Compare employee fraud index to peers"""
        peer_indexes = [v["fraud_index"] for k, v in self.fraud_scores.items() if k != staff_id]
        
        if not peer_indexes:
            return {"comparison": "no_peers", "percentile": None}
        
        avg = statistics.mean(peer_indexes)
        percentile = len([p for p in peer_indexes if p < fraud_index]) / len(peer_indexes) * 100
        
        return {
            "peer_average": round(avg, 1),
            "percentile": round(percentile, 1),
            "comparison": "above_average" if fraud_index > avg else "below_average"
        }
    
    def _calculate_trend(self, staff_id: int, current_index: float) -> Dict[str, Any]:
        """Calculate fraud index trend by comparing to historical indexes"""
        from app.models import FraudScore
        from datetime import timedelta

        try:
            # Get fraud score history for this employee over the past 30 days
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

            historical_indexes = self.db.query(FraudScore).filter(
                FraudScore.employee_id == staff_id,
                FraudScore.calculated_at >= thirty_days_ago
            ).order_by(FraudScore.calculated_at.desc()).limit(30).all()

            if not historical_indexes or len(historical_indexes) < 3:
                # Not enough history - check in-memory scores
                if staff_id in self.fraud_scores:
                    history = self.fraud_scores[staff_id].get("history", [])
                    if len(history) >= 3:
                        recent_avg = sum(history[-7:]) / len(history[-7:]) if len(history) >= 7 else sum(history) / len(history)
                        older_avg = sum(history[:-7]) / len(history[:-7]) if len(history) > 7 else recent_avg

                        change = current_index - older_avg
                        change_pct = (change / older_avg * 100) if older_avg > 0 else 0

                        if change_pct > 15:
                            direction = "rising"
                        elif change_pct < -15:
                            direction = "declining"
                        else:
                            direction = "stable"

                        return {
                            "direction": direction,
                            "change": round(change, 2),
                            "change_percent": round(change_pct, 1),
                            "data_points": len(history)
                        }

                return {"direction": "stable", "change": 0, "change_percent": 0, "data_points": 0}

            # Calculate averages for comparison
            indexes = [h.overall_score for h in historical_indexes]

            # Recent (last 7 entries) vs older
            recent_indexes = indexes[:7] if len(indexes) >= 7 else indexes
            older_indexes = indexes[7:] if len(indexes) > 7 else []

            recent_avg = sum(recent_indexes) / len(recent_indexes)

            if older_indexes:
                older_avg = sum(older_indexes) / len(older_indexes)
            else:
                # Compare to first recorded index
                older_avg = indexes[-1]

            # Calculate change
            change = current_index - older_avg
            change_pct = (change / older_avg * 100) if older_avg > 0 else 0

            # Determine direction
            if change_pct > 15:
                direction = "rising"
            elif change_pct < -15:
                direction = "declining"
            else:
                direction = "stable"

            # Calculate additional trend metrics
            trend_data = {
                "direction": direction,
                "change": round(change, 2),
                "change_percent": round(change_pct, 1),
                "recent_average": round(recent_avg, 2),
                "older_average": round(older_avg, 2),
                "data_points": len(indexes),
                "highest_30d": round(max(indexes), 2),
                "lowest_30d": round(min(indexes), 2)
            }

            # Check for concerning patterns
            if direction == "rising" and current_index > 50:
                trend_data["alert"] = "Fraud index trending up and above threshold"
            elif all(idx > 40 for idx in recent_indexes):
                trend_data["alert"] = "Consistently elevated fraud index"

            return trend_data

        except Exception as e:
            logger.warning(f"Failed to calculate fraud index trend from database for staff_id={staff_id}: {e}")
            # Fallback to in-memory data if database fails
            if staff_id in self.fraud_scores:
                prev_index = self.fraud_scores[staff_id].get("previous_index", current_index)
                change = current_index - prev_index

                if change > 5:
                    direction = "rising"
                elif change < -5:
                    direction = "declining"
                else:
                    direction = "stable"

                return {"direction": direction, "change": round(change, 2), "change_percent": 0}

            return {"direction": "stable", "change": 0, "change_percent": 0}
    
    def _get_recommendations(
        self,
        scores: Dict[str, float],
        concerns: List[str]
    ) -> List[str]:
        """Get actionable recommendations"""
        recommendations = []
        
        if scores["void_risk"] >= 30:
            recommendations.append("Implement manager approval for all voids over €20")
        if scores["discount_risk"] >= 30:
            recommendations.append("Review discount authorization levels")
        if scores["cash_handling_risk"] >= 30:
            recommendations.append("Increase cash count frequency")
        if scores["time_fraud_risk"] >= 30:
            recommendations.append("Enable biometric time tracking")
        
        if not recommendations:
            recommendations.append("Continue standard monitoring")
        
        return recommendations
    
    def _save_fraud_score_to_db(
        self,
        staff_id: int,
        result: Dict,
        scores: Dict[str, float],
        start_date: datetime,
        end_date: datetime,
        transactions_count: int
    ):
        """Save fraud score to database for historical tracking"""
        from app.models import FraudScore, StaffUser

        try:
            # Get venue_id from staff member
            staff = self.db.query(StaffUser).filter(StaffUser.id == staff_id).first()
            if not staff:
                return

            # Calculate score change from previous score
            prev_score = self.db.query(FraudScore).filter(
                FraudScore.employee_id == staff_id
            ).order_by(FraudScore.calculated_at.desc()).first()

            score_change = None
            if prev_score:
                score_change = result["fraud_index"] - prev_score.overall_score

            # Create new fraud score record
            fraud_score = FraudScore(
                venue_id=staff.venue_id,
                employee_id=staff_id,
                overall_score=result["fraud_index"],
                void_risk_score=scores.get("void_risk", 0.0),
                discount_risk_score=scores.get("discount_risk", 0.0),
                cash_risk_score=scores.get("cash_handling_risk", 0.0),
                refund_risk_score=scores.get("refund_risk", 0.0),
                time_fraud_score=scores.get("time_fraud_risk", 0.0),
                pattern_anomaly_score=scores.get("pattern_anomaly_risk", 0.0),
                manager_override_score=scores.get("manager_override_risk", 0.0),
                risk_level=result["risk_level"],
                period_start=start_date,
                period_end=end_date,
                transactions_analyzed=transactions_count,
                score_change=score_change,
                trend_direction=result.get("trend", {}).get("direction")
            )

            self.db.add(fraud_score)
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.warning(f"Failed to save fraud score to database for staff_id={staff_id}: {e}")

    def _generate_fraud_alert(
        self,
        staff_id: int,
        data: Dict,
        severity: AlertSeverity
    ):
        """Generate and store a fraud alert"""
        import uuid

        alert = {
            "alert_id": str(uuid.uuid4()),
            "staff_id": staff_id,
            "severity": severity.value,
            "category": data.get("alert", {}).get("type", "unknown"),
            "message": data.get("alert", {}).get("message", "Fraud risk detected"),
            "data": data,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "acknowledged": False
        }

        self.alerts.append(alert)
    
    # Database query methods for fraud analysis
    def _get_employee_transactions(self, staff_id: int, start: datetime, end: datetime) -> List[Dict]:
        """Get employee transactions from database"""
        from app.models import Order, OrderItem

        try:
            orders = self.db.query(Order).filter(
                Order.waiter_id == staff_id,
                Order.created_at >= start,
                Order.created_at <= end
            ).all()

            return [{
                "id": o.id,
                "total": float(o.total or 0),
                "status": o.status.value if hasattr(o.status, 'value') else str(o.status),
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "payment_method": o.payment_method,
                "payment_status": o.payment_status,
                "is_void": o.status.value == "cancelled" if hasattr(o.status, 'value') else str(o.status) == "cancelled",
                "has_discount": (o.total or 0) > 0,  # Will be enhanced with actual discount check
                "is_refund": o.payment_status == "refunded",
                "void_amount": float(o.total or 0) if (o.status.value == "cancelled" if hasattr(o.status, 'value') else str(o.status) == "cancelled") else 0,
                "discount_amount": 0,  # Placeholder - would need to calculate from items
                "customer_id": o.customer_id,
                "tip_amount": float(o.tip_amount or 0)
            } for o in orders]
        except Exception as e:
            logger.warning(f"Failed to fetch employee transactions for staff_id={staff_id}: {e}")
            return []

    def _get_employee_voids(self, staff_id: int, start: datetime, end: datetime) -> List[Dict]:
        """Get employee void transactions from database"""
        from app.models import Order, OrderStatus

        try:
            voids = self.db.query(Order).filter(
                Order.waiter_id == staff_id,
                Order.status == OrderStatus.CANCELLED,
                Order.created_at >= start,
                Order.created_at <= end
            ).all()

            results = []
            for o in voids:
                # Calculate time between order creation and void
                minutes_since_order = 0
                if o.created_at and o.updated_at:
                    minutes_since_order = (o.updated_at - o.created_at).total_seconds() / 60

                # Check if payment was already processed
                after_payment = o.payment_status in ["paid", "refunded"] if o.payment_status else False

                results.append({
                    "id": o.id,
                    "amount": float(o.total or 0),
                    "voided_at": o.updated_at.isoformat() if o.updated_at else None,
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                    "reason": getattr(o, 'cancel_reason', None),
                    "minutes_since_order": minutes_since_order,
                    "after_payment": after_payment,
                    "payment_method": o.payment_method,
                    "order_number": o.order_number
                })

            return results
        except Exception as e:
            logger.warning(f"Failed to fetch employee voids for staff_id={staff_id}: {e}")
            return []

    def _get_employee_discounts(self, staff_id: int, start: datetime, end: datetime) -> List[Dict]:
        """Get employee discount applications from database"""
        from app.models import PromotionUsage, Order, Promotion

        try:
            # Get promotion usages (discounts) for orders created by this staff member
            discounts = self.db.query(PromotionUsage).join(
                Order, PromotionUsage.order_id == Order.id
            ).filter(
                Order.waiter_id == staff_id,
                PromotionUsage.created_at >= start,
                PromotionUsage.created_at <= end
            ).all()

            results = []
            for discount in discounts:
                discount_amount = float(discount.discount_applied or 0)

                # Get the order and promotion details
                order = self.db.query(Order).filter(Order.id == discount.order_id).first()
                promotion = self.db.query(Promotion).filter(Promotion.id == discount.promotion_id).first()

                original_total = float(order.total or 0) + discount_amount if order else discount_amount

                # Calculate percentage
                discount_percent = (discount_amount / original_total * 100) if original_total > 0 else 0

                # Check if this is an unauthorized or manual discount
                # System promotions are approved, but we flag high discounts
                manager_approved = True
                if discount_percent >= 50:
                    # High discount - should have been approved
                    manager_approved = promotion is not None

                results.append({
                    "id": discount.id,
                    "amount": discount_amount,  # Using 'amount' for consistency
                    "discount_amount": discount_amount,
                    "percentage": discount_percent,  # Using 'percentage' for consistency
                    "discount_percent": discount_percent,
                    "original_total": original_total,
                    "customer_id": discount.customer_id,
                    "order_id": discount.order_id,
                    "applied_at": discount.created_at.isoformat() if discount.created_at else None,
                    "manager_approved": manager_approved,
                    "promotion_id": discount.promotion_id,
                    "promotion_name": promotion.name if promotion else "Manual Discount"
                })

            return results

        except Exception as e:
            logger.warning(f"Failed to fetch employee discounts for staff_id={staff_id}: {e}")
            return []

    def _get_employee_refunds(self, staff_id: int, start: datetime, end: datetime) -> List[Dict]:
        """Get employee refund transactions from database"""
        from app.models import OrderCancellation, Order

        try:
            # Get refunded orders - either through OrderCancellation or Order payment_status
            refunds = []

            # Method 1: OrderCancellation with refunds
            cancellations = self.db.query(OrderCancellation).filter(
                OrderCancellation.cancelled_by == staff_id,
                OrderCancellation.was_refunded == True,
                OrderCancellation.cancelled_at >= start,
                OrderCancellation.cancelled_at <= end
            ).all()

            for cancel in cancellations:
                # Get the order to check timing
                order = self.db.query(Order).filter(Order.id == cancel.order_id).first() if cancel.order_id else None

                # Check if refund was after business hours (assume 6am-11pm)
                after_business_hours = False
                if cancel.cancelled_at:
                    hour = cancel.cancelled_at.hour
                    after_business_hours = hour < 6 or hour >= 23

                refunds.append({
                    "id": cancel.id,
                    "amount": float(cancel.refund_amount or 0),
                    "method": cancel.refund_method,
                    "order_id": cancel.order_id,
                    "refunded_at": cancel.cancelled_at.isoformat() if cancel.cancelled_at else None,
                    "has_receipt": True,  # Cancellations are tracked, so assume receipt exists
                    "after_business_hours": after_business_hours,
                    "reason": cancel.reason if hasattr(cancel, 'reason') else None,
                    "customer_id": order.customer_id if order else None
                })

            # Method 2: Orders with refunded payment status
            refunded_orders = self.db.query(Order).filter(
                Order.waiter_id == staff_id,
                Order.payment_status == "refunded",
                Order.updated_at >= start,
                Order.updated_at <= end
            ).all()

            for order in refunded_orders:
                # Avoid duplicates
                if not any(r.get("order_id") == order.id for r in refunds):
                    # Check if refund was after business hours
                    after_business_hours = False
                    if order.updated_at:
                        hour = order.updated_at.hour
                        after_business_hours = hour < 6 or hour >= 23

                    refunds.append({
                        "id": order.id,
                        "amount": float(order.total or 0),
                        "method": order.payment_method,
                        "order_id": order.id,
                        "refunded_at": order.updated_at.isoformat() if order.updated_at else None,
                        "has_receipt": order.payment_status == "refunded",  # Payment tracked = receipt
                        "after_business_hours": after_business_hours,
                        "reason": None,
                        "customer_id": order.customer_id
                    })

            return refunds

        except Exception as e:
            logger.warning(f"Failed to fetch employee refunds for staff_id={staff_id}: {e}")
            return []

    def _get_employee_cash_reports(self, staff_id: int, start: datetime, end: datetime) -> List[Dict]:
        """Get employee cash drawer reports from database"""
        from app.models import CashDrawer, CashDrawerTransaction

        try:
            drawers = self.db.query(CashDrawer).filter(
                CashDrawer.staff_user_id == staff_id,
                CashDrawer.opened_at >= start,
                CashDrawer.opened_at <= end
            ).all()

            reports = []
            for drawer in drawers:
                # Count no-sale transactions for this drawer
                no_sale_count = self.db.query(CashDrawerTransaction).filter(
                    CashDrawerTransaction.drawer_id == drawer.id,
                    CashDrawerTransaction.transaction_type == "no_sale"
                ).count()

                expected = float(drawer.expected_balance or 0) if drawer.expected_balance else float(drawer.opening_balance or 0) + float(drawer.cash_sales or 0)
                actual = float(drawer.actual_balance or 0) if drawer.actual_balance else 0

                reports.append({
                    "id": drawer.id,
                    "expected": expected,
                    "actual": actual,
                    "variance": float(drawer.variance or 0) if drawer.variance else (actual - expected),
                    "no_sale_count": no_sale_count,
                    "opened_at": drawer.opened_at.isoformat() if drawer.opened_at else None,
                    "closed_at": drawer.closed_at.isoformat() if drawer.closed_at else None
                })

            return reports
        except Exception as e:
            logger.warning(f"Failed to fetch employee cash reports for staff_id={staff_id}: {e}")
            return []

    def _get_employee_time_entries(self, staff_id: int, start: datetime, end: datetime) -> List[Dict]:
        """Get employee time clock entries from database"""
        from app.models import StaffShift, ClockEvent

        try:
            shifts = self.db.query(StaffShift).filter(
                StaffShift.staff_user_id == staff_id,
                StaffShift.scheduled_start >= start,
                StaffShift.scheduled_start <= end
            ).all()

            entries = []
            for shift in shifts:
                # Calculate hours worked
                hours_worked = 0
                if shift.actual_start and shift.actual_end:
                    duration = shift.actual_end - shift.actual_start
                    hours_worked = duration.total_seconds() / 3600
                    # Subtract break time
                    hours_worked -= (shift.total_break_minutes or 0) / 60

                # Check for early clock-in or late clock-out (manual correction indicator)
                manual_correction = False
                early_minutes = 0
                late_minutes = 0

                if shift.actual_start and shift.scheduled_start:
                    early_minutes = (shift.scheduled_start - shift.actual_start).total_seconds() / 60
                    manual_correction = abs(early_minutes) > 10  # More than 10 minutes difference

                if shift.actual_end and shift.scheduled_end:
                    late_minutes = (shift.actual_end - shift.scheduled_end).total_seconds() / 60
                    manual_correction = manual_correction or abs(late_minutes) > 10

                # Check for unusual location (would need GPS/location data in ClockEvent)
                # For now, we'll check if there are clock events with location data
                unusual_location = False
                if hasattr(shift, 'clock_events'):
                    # If clock events exist, check for location anomalies
                    # This is a placeholder - would need actual location validation
                    unusual_location = False

                entries.append({
                    "id": shift.id,
                    "clock_in": shift.actual_start.isoformat() if shift.actual_start else None,
                    "clock_out": shift.actual_end.isoformat() if shift.actual_end else None,
                    "hours_worked": float(hours_worked),
                    "break_minutes": int(shift.total_break_minutes or 0),
                    "scheduled_start": shift.scheduled_start.isoformat() if shift.scheduled_start else None,
                    "scheduled_end": shift.scheduled_end.isoformat() if shift.scheduled_end else None,
                    "overtime_hours": max(0, hours_worked - 8) if hours_worked > 8 else 0,
                    "manual_correction": manual_correction,
                    "unusual_location": unusual_location,
                    "early_minutes": early_minutes if early_minutes > 0 else 0,
                    "late_minutes": late_minutes if late_minutes > 0 else 0,
                    "status": shift.status.value if hasattr(shift.status, 'value') else str(shift.status) if hasattr(shift, 'status') else "completed"
                })

            return entries
        except Exception as e:
            logger.warning(f"Failed to fetch employee time entries for staff_id={staff_id}: {e}")
            return []

    def _get_manager_overrides(self, staff_id: int, start: datetime, end: datetime) -> List[Dict]:
        """Get manager override actions from database"""
        from app.models import AuditLog

        try:
            # Query for override-related actions for this staff member
            overrides = self.db.query(AuditLog).filter(
                AuditLog.staff_user_id == staff_id,
                AuditLog.action.in_(["manager_override", "void_approval", "discount_approval", "refund_approval", "void", "discount", "refund"]),
                AuditLog.created_at >= start,
                AuditLog.created_at <= end
            ).all()

            results = []
            for override in overrides:
                # Extract details from JSON fields
                old_vals = override.old_values if override.old_values else {}
                new_vals = override.new_values if override.new_values else {}

                results.append({
                    "id": override.id,
                    "action": override.action,
                    "manager_id": override.staff_user_id,
                    "target_staff_id": new_vals.get("staff_id") if isinstance(new_vals, dict) else None,
                    "amount": new_vals.get("amount") if isinstance(new_vals, dict) else None,
                    "performed_at": override.created_at.isoformat() if override.created_at else None
                })

            return results
        except Exception as e:
            logger.warning(f"Failed to fetch manager overrides for staff_id={staff_id}: {e}")
            return []

    def _get_venue_staff(self, venue_id: int) -> List[Dict]:
        """Get all staff for a venue"""
        from app.models import StaffUser

        try:
            staff = self.db.query(StaffUser).filter(
                StaffUser.venue_id == venue_id,
                StaffUser.active == True
            ).all()

            return [{
                "id": s.id,
                "name": s.full_name,
                "role": s.role.value if hasattr(s.role, 'value') else str(s.role)
            } for s in staff]
        except Exception as e:
            logger.warning(f"Failed to fetch venue staff for venue_id={venue_id}: {e}")
            return []

    def _get_venue_transactions(self, venue_id: int, start: datetime, end: datetime) -> List[Dict]:
        """Get all venue transactions for a period"""
        from app.models import Order, VenueStation

        try:
            # Join through station to get venue_id
            orders = self.db.query(Order).join(
                VenueStation, Order.station_id == VenueStation.id
            ).filter(
                VenueStation.venue_id == venue_id,
                Order.created_at >= start,
                Order.created_at <= end
            ).all()

            return [{
                "id": o.id,
                "staff_id": o.waiter_id,
                "total": float(o.total or 0),
                "created_at": o.created_at.isoformat() if o.created_at else None
            } for o in orders]
        except Exception as e:
            logger.warning(f"Failed to fetch venue transactions for venue_id={venue_id}: {e}")
            return []

    def _get_venue_voids(self, venue_id: int, start: datetime, end: datetime) -> List[Dict]:
        """Get all venue void transactions for a period"""
        from app.models import Order, VenueStation, OrderStatus

        try:
            # Join through station to get venue_id
            voids = self.db.query(Order).join(
                VenueStation, Order.station_id == VenueStation.id
            ).filter(
                VenueStation.venue_id == venue_id,
                Order.status == OrderStatus.CANCELLED,
                Order.created_at >= start,
                Order.created_at <= end
            ).all()

            return [{
                "id": o.id,
                "staff_id": o.waiter_id,
                "amount": float(o.total or 0),
                "voided_at": o.updated_at.isoformat() if o.updated_at else None
            } for o in voids]
        except Exception as e:
            logger.warning(f"Failed to fetch venue voids for venue_id={venue_id}: {e}")
            return []

    def _detect_consecutive_voids(self, voids: List[Dict]) -> bool:
        """Detect if voids occurred consecutively (within 5 minutes of each other)"""
        if len(voids) < 2:
            return False
            
        sorted_voids = sorted(voids, key=lambda x: x.get("voided_at", ""))
        for i in range(1, len(sorted_voids)):
            try:
                prev_time = datetime.fromisoformat(sorted_voids[i-1].get("voided_at", ""))
                curr_time = datetime.fromisoformat(sorted_voids[i].get("voided_at", ""))
                if (curr_time - prev_time).total_seconds() < 300:  # 5 minutes
                    return True
            except (ValueError, TypeError):
                continue
        return False
    
    def _detect_end_of_shift_voids(self, voids: List[Dict]) -> List[Dict]:
        """Detect voids that occurred near end of shift (suspicious timing)"""
        end_of_shift_voids = []
        shift_end_hours = [14, 22, 23]  # Typical shift end hours
        
        for void in voids:
            try:
                void_time = datetime.fromisoformat(void.get("voided_at", ""))
                if void_time.hour in shift_end_hours and void_time.minute > 45:
                    end_of_shift_voids.append(void)
            except (ValueError, TypeError):
                continue
                
        return end_of_shift_voids
    
    def _detect_repeat_discount_customers(self, discounts: List[Dict]) -> bool:
        """Detect if same customers receive multiple discounts"""
        customer_counts = {}
        for discount in discounts:
            customer_id = discount.get("customer_id")
            if customer_id:
                customer_counts[customer_id] = customer_counts.get(customer_id, 0) + 1
                
        # Flag if any customer received 3+ discounts
        return any(count >= 3 for count in customer_counts.values())
    
    def _detect_refund_tender_patterns(self, refunds: List[Dict]) -> bool:
        """Detect suspicious refund tender patterns (e.g., all cash refunds)"""
        if len(refunds) < 3:
            return False
            
        cash_refunds = sum(1 for r in refunds if r.get("method") == "cash")
        return cash_refunds / len(refunds) > 0.8  # 80%+ cash refunds is suspicious
    
    def _detect_time_padding(self, entries: List[Dict]) -> int:
        """Detect early clock-in and late clock-out patterns"""
        padding_instances = 0

        for entry in entries:
            try:
                clock_in = datetime.fromisoformat(entry.get("clock_in", ""))
                clock_out_str = entry.get("clock_out")

                # Check early clock-in (more than 10 minutes before scheduled)
                # Assuming shifts typically start at standard times (6am, 2pm, 10pm)
                clock_in_hour = clock_in.hour
                clock_in_minute = clock_in.minute

                # If clocking in more than 15 minutes early
                if clock_in_minute <= 45 and clock_in_hour in [5, 1, 9]:  # Hour before typical shift starts
                    padding_instances += 1

                # Check late clock-out (more than 10 minutes after shift end)
                if clock_out_str:
                    clock_out = datetime.fromisoformat(clock_out_str)
                    clock_out_hour = clock_out.hour
                    clock_out_minute = clock_out.minute

                    # If clocking out more than 15 minutes late
                    if clock_out_minute >= 15 and clock_out_hour in [15, 23, 7]:  # Hour after typical shift ends
                        padding_instances += 1

            except (ValueError, TypeError, AttributeError):
                continue

        return padding_instances
    
    def _detect_timing_anomalies(self, transactions: List[Dict]) -> int:
        """Detect transactions at unusual times (very late night, very early morning)"""
        anomaly_count = 0

        for transaction in transactions:
            try:
                created_at = datetime.fromisoformat(transaction.get("created_at", ""))
                hour = created_at.hour

                # Transactions between 2 AM - 5 AM are unusual for most restaurants
                if 2 <= hour < 5:
                    anomaly_count += 1
                # Transactions right after closing (11 PM - 1 AM) can be suspicious
                elif 23 <= hour or hour < 1:
                    # Check if it's a high-value transaction
                    if transaction.get("total", 0) > 100:
                        anomaly_count += 1

            except (ValueError, TypeError, AttributeError):
                continue

        return anomaly_count
    
    def _detect_velocity_changes(self, transactions: List[Dict]) -> float:
        """Detect sudden changes in transaction velocity (transactions per hour)"""
        if len(transactions) < 10:
            return 0.0

        try:
            # Group transactions by hour
            hourly_counts = {}
            for transaction in transactions:
                created_at = datetime.fromisoformat(transaction.get("created_at", ""))
                hour_key = created_at.strftime("%Y-%m-%d %H:00")
                hourly_counts[hour_key] = hourly_counts.get(hour_key, 0) + 1

            if len(hourly_counts) < 3:
                return 0.0

            counts = list(hourly_counts.values())
            avg_velocity = statistics.mean(counts)

            if avg_velocity == 0:
                return 0.0

            # Find maximum deviation from average
            max_deviation = max(abs(c - avg_velocity) for c in counts)
            velocity_change = max_deviation / avg_velocity

            return velocity_change

        except (ValueError, TypeError, ZeroDivisionError, statistics.StatisticsError):
            return 0.0
    
    def _calculate_ticket_deviation(self, staff_id: int, transactions: List[Dict]) -> float:
        """Calculate how much the average ticket deviates from the employee's baseline"""
        if len(transactions) < 5:
            return 0.0

        try:
            # Calculate current average ticket
            totals = [t.get("total", 0) for t in transactions if t.get("total", 0) > 0]

            if len(totals) < 5:
                return 0.0

            current_avg = statistics.mean(totals)
            current_stdev = statistics.stdev(totals) if len(totals) > 1 else 0

            if current_stdev == 0:
                return 0.0

            # Get baseline from stored metrics (if available)
            baseline = self.baseline_metrics.get(staff_id, {})
            baseline_avg = baseline.get("avg_ticket", current_avg)

            # Calculate deviation in standard deviations
            deviation = abs(current_avg - baseline_avg) / current_stdev

            return deviation

        except (ValueError, TypeError, ZeroDivisionError, statistics.StatisticsError):
            return 0.0
    
    def _detect_suspicious_combos(self, transactions: List[Dict]) -> int:
        """Detect suspicious item combinations (e.g., all discounted items, all high-value voids)"""
        suspicious_count = 0

        # Look for patterns in transaction types
        if len(transactions) < 3:
            return 0

        # Check for streaks of same transaction types
        void_streak = 0
        discount_streak = 0
        max_void_streak = 0
        max_discount_streak = 0

        for transaction in transactions:
            status = transaction.get("status", "")
            payment_method = transaction.get("payment_method", "")

            # Count void streaks
            if status == "cancelled":
                void_streak += 1
                max_void_streak = max(max_void_streak, void_streak)
            else:
                void_streak = 0

            # Count high discount streaks
            if transaction.get("total", 0) < 5 and payment_method == "cash":
                discount_streak += 1
                max_discount_streak = max(max_discount_streak, discount_streak)
            else:
                discount_streak = 0

        # Flag if we see suspicious streaks
        if max_void_streak >= 3:
            suspicious_count += max_void_streak
        if max_discount_streak >= 3:
            suspicious_count += max_discount_streak

        return suspicious_count
    
    def _is_suspicious_time(self, transaction: Dict) -> bool:
        """Check if transaction occurred at a suspicious time"""
        try:
            created_at_str = transaction.get("created_at")
            if not created_at_str:
                return False

            created_at = datetime.fromisoformat(created_at_str)
            hour = created_at.hour

            # Very late night / very early morning transactions
            if 1 <= hour < 5:
                return True

            # Check for transactions during typical closed hours for restaurants
            if hour < 6 or hour >= 23:
                return True

            return False

        except (ValueError, TypeError, AttributeError):
            return False
    
    def _get_recent_no_sales(self, staff_id: int, minutes: int) -> int:
        """Get count of no-sale drawer opens in recent minutes"""
        from app.models import CashDrawerTransaction

        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)

            no_sales = self.db.query(CashDrawerTransaction).join(
                CashDrawerTransaction.drawer
            ).filter(
                CashDrawerTransaction.drawer.has(staff_user_id=staff_id),
                CashDrawerTransaction.transaction_type == "no_sale",
                CashDrawerTransaction.created_at >= cutoff_time
            ).count()

            return no_sales

        except Exception as e:
            logger.warning(f"Failed to fetch recent no-sale transactions for staff_id={staff_id}: {e}")
            return 0

    def _get_shift_start_time(self, shift_id: str) -> datetime:
        """Get the start time of a shift from the database"""
        from app.models import StaffShift

        try:
            shift = self.db.query(StaffShift).filter(
                StaffShift.id == int(shift_id)
            ).first()

            if shift and shift.actual_start:
                return shift.actual_start
            elif shift and shift.scheduled_start:
                return shift.scheduled_start
            else:
                # Default to 4 hours ago if shift not found
                return datetime.now(timezone.utc) - timedelta(hours=4)

        except (ValueError, TypeError):
            return datetime.now(timezone.utc) - timedelta(hours=4)
    
    def _get_transactions_since(self, staff_id: int, since: datetime) -> List[Dict]:
        """Get all transactions for a staff member since a specific time"""
        from app.models import Order

        try:
            orders = self.db.query(Order).filter(
                Order.waiter_id == staff_id,
                Order.created_at >= since
            ).all()

            return [{
                "id": o.id,
                "total": float(o.total or 0),
                "status": o.status,
                "is_void": o.status == "cancelled",
                "has_discount": (o.total or 0) < (o.total or 0) * 1.1,  # Simplified check
                "is_refund": o.payment_status == "refunded",
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "payment_method": o.payment_method,
                "void_amount": float(o.total or 0) if o.status == "cancelled" else 0,
                "discount_amount": 0  # Would need to calculate from order items
            } for o in orders]

        except Exception as e:
            logger.warning(f"Failed to fetch transactions since {since} for staff_id={staff_id}: {e}")
            return []

    def _get_staff_baseline(self, staff_id: int) -> Optional[Dict]:
        """Get baseline metrics for a staff member from historical data"""
        from app.models import Order, OrderCancellation
        from sqlalchemy import func

        try:
            # Get historical data from last 60-90 days for baseline
            end_date = datetime.now(timezone.utc) - timedelta(days=30)
            start_date = end_date - timedelta(days=60)

            # Calculate baseline metrics
            orders = self.db.query(Order).filter(
                Order.waiter_id == staff_id,
                Order.created_at >= start_date,
                Order.created_at <= end_date
            ).all()

            if len(orders) < 10:
                return None

            total_orders = len(orders)
            total_sales = sum(float(o.total or 0) for o in orders)
            cancelled_orders = sum(1 for o in orders if o.status == "cancelled")

            # Get void rate
            void_rate = (cancelled_orders / total_orders) * 100 if total_orders > 0 else 0

            # Get average ticket
            avg_ticket = total_sales / total_orders if total_orders > 0 else 0

            # Get discount rate (simplified)
            avg_discount_rate = 5.0  # Default placeholder

            return {
                "avg_void_rate": void_rate,
                "avg_discount_rate": avg_discount_rate,
                "avg_ticket": avg_ticket,
                "total_transactions": total_orders
            }

        except Exception as e:
            logger.warning(f"Failed to fetch staff baseline metrics for staff_id={staff_id}: {e}")
            return None

    def _calculate_shift_duration(self, start: datetime) -> int:
        return int((datetime.now(timezone.utc) - start).total_seconds() / 60)
    
    def _calculate_venue_fraud_trend(self, venue_id: int, days: int) -> str:
        """Calculate fraud trend for a venue over time"""
        from app.models import Order

        try:
            # Compare current period to previous period
            end_date = datetime.now(timezone.utc)
            mid_date = end_date - timedelta(days=days // 2)
            start_date = end_date - timedelta(days=days)

            # Get void rates for both periods
            recent_orders = self.db.query(Order).filter(
                Order.created_at >= mid_date,
                Order.created_at <= end_date
            ).all()

            previous_orders = self.db.query(Order).filter(
                Order.created_at >= start_date,
                Order.created_at < mid_date
            ).all()

            if len(recent_orders) < 5 or len(previous_orders) < 5:
                return "stable"

            recent_void_rate = sum(1 for o in recent_orders if o.status == "cancelled") / len(recent_orders)
            previous_void_rate = sum(1 for o in previous_orders if o.status == "cancelled") / len(previous_orders)

            # Determine trend
            if recent_void_rate > previous_void_rate * 1.3:
                return "increasing"
            elif recent_void_rate < previous_void_rate * 0.7:
                return "decreasing"
            else:
                return "stable"

        except Exception as e:
            logger.warning(f"Failed to calculate venue fraud trend for venue_id={venue_id}: {e}")
            return "stable"

    def _get_venue_recommendations(self, indexes: List[Dict], alerts: List[Dict]) -> List[str]:
        """Generate venue-wide recommendations based on fraud analysis"""
        recommendations = []

        # Count high-risk employees
        high_risk_count = sum(1 for idx in indexes if idx.get("fraud_index", 0) >= 50)
        medium_risk_count = sum(1 for idx in indexes if 30 <= idx.get("fraud_index", 0) < 50)

        # Count unacknowledged alerts
        unack_alerts = sum(1 for alert in alerts if not alert.get("acknowledged", False))

        if high_risk_count > 0:
            recommendations.append(f"Immediate action required: {high_risk_count} high-risk employee(s) detected")
            recommendations.append("Schedule individual meetings with high-risk employees")
            recommendations.append("Review transaction logs for suspicious patterns")

        if medium_risk_count > 2:
            recommendations.append(f"Monitor {medium_risk_count} medium-risk employees closely")
            recommendations.append("Increase manager oversight for medium-risk staff")

        if unack_alerts > 10:
            recommendations.append(f"Address {unack_alerts} unacknowledged alerts")
            recommendations.append("Implement daily alert review process")

        # General recommendations
        if high_risk_count > 0 or medium_risk_count > 3:
            recommendations.append("Consider additional staff training on POS procedures")
            recommendations.append("Implement manager approval for voids over €20")
            recommendations.append("Enable real-time fraud alerts for critical actions")
        else:
            recommendations.append("Continue standard monitoring")
            recommendations.append("Review high-risk employees weekly")

        return recommendations
    
    def _generate_venue_fraud_report(self, venue_id: int, start: datetime, end: datetime) -> Dict:
        return self.get_fraud_dashboard(venue_id, (end - start).days)
    
    def _analyze_voids_detail(self, voids: List[Dict]) -> Dict:
        """Detailed analysis of void patterns"""
        patterns = []

        if not voids:
            return {"total": 0, "patterns": [], "total_amount": 0}

        # Calculate metrics
        total_amount = sum(v.get("amount", 0) for v in voids)
        avg_amount = total_amount / len(voids) if voids else 0
        high_value_voids = [v for v in voids if v.get("amount", 0) > 50]

        # Detect patterns
        if len(high_value_voids) > len(voids) * 0.3:
            patterns.append("High proportion of high-value voids (>30%)")

        # Check for time-based patterns
        if self._detect_end_of_shift_voids(voids):
            patterns.append("Voids occurring near end of shift detected")

        if self._detect_consecutive_voids(voids):
            patterns.append("Consecutive void pattern detected")

        # Check void frequency
        if len(voids) > 20:
            patterns.append(f"High void frequency: {len(voids)} voids in period")

        return {
            "total": len(voids),
            "total_amount": round(total_amount, 2),
            "average_amount": round(avg_amount, 2),
            "high_value_count": len(high_value_voids),
            "patterns": patterns
        }
    
    def _analyze_discounts_detail(self, discounts: List[Dict]) -> Dict:
        """Detailed analysis of discount patterns"""
        patterns = []

        if not discounts:
            return {"total": 0, "patterns": [], "total_amount": 0}

        # Calculate metrics
        total_amount = sum(d.get("discount_amount", 0) for d in discounts)
        avg_amount = total_amount / len(discounts) if discounts else 0
        avg_percent = statistics.mean([d.get("discount_percent", 0) for d in discounts]) if discounts else 0

        # Detect patterns
        large_discounts = [d for d in discounts if d.get("discount_percent", 0) >= 50]
        if len(large_discounts) > len(discounts) * 0.2:
            patterns.append(f"High proportion of large discounts (≥50%): {len(large_discounts)}")

        # Check for repeat customers
        if self._detect_repeat_discount_customers(discounts):
            patterns.append("Same customers receiving multiple discounts")

        # Check unauthorized discounts
        unauthorized = [d for d in discounts if not d.get("manager_approved", True)]
        if len(unauthorized) > 0:
            patterns.append(f"Unauthorized discounts detected: {len(unauthorized)}")

        # Check discount frequency
        if len(discounts) > 30:
            patterns.append(f"High discount frequency: {len(discounts)} discounts in period")

        return {
            "total": len(discounts),
            "total_amount": round(total_amount, 2),
            "average_amount": round(avg_amount, 2),
            "average_percent": round(avg_percent, 2),
            "large_discount_count": len(large_discounts),
            "unauthorized_count": len(unauthorized),
            "patterns": patterns
        }
    
    def _analyze_patterns_detail(self, transactions: List[Dict]) -> Dict:
        """Detailed analysis of transaction patterns and anomalies"""
        anomalies = []

        if not transactions:
            return {"anomalies": [], "summary": "No transactions to analyze"}

        # Transaction timing analysis
        timing_anomalies = self._detect_timing_anomalies(transactions)
        if timing_anomalies > 0:
            anomalies.append(f"{timing_anomalies} transaction(s) at unusual hours")

        # Velocity analysis
        velocity_change = self._detect_velocity_changes(transactions)
        if velocity_change > 0.5:
            anomalies.append(f"Transaction velocity variation detected: {velocity_change:.1%}")

        # Suspicious combinations
        suspicious_combos = self._detect_suspicious_combos(transactions)
        if suspicious_combos > 0:
            anomalies.append(f"{suspicious_combos} suspicious transaction patterns detected")

        # Calculate average transaction values
        totals = [t.get("total", 0) for t in transactions if t.get("total", 0) > 0]
        if totals:
            avg_ticket = statistics.mean(totals)
            if len(totals) > 1:
                stdev = statistics.stdev(totals)
                # Check for outliers (transactions > 2 std devs from mean)
                outliers = [t for t in totals if abs(t - avg_ticket) > 2 * stdev]
                if len(outliers) > len(totals) * 0.1:
                    anomalies.append(f"{len(outliers)} outlier transaction values detected")

        # Payment method analysis
        payment_methods = {}
        for t in transactions:
            method = t.get("payment_method", "unknown")
            payment_methods[method] = payment_methods.get(method, 0) + 1

        # Flag if cash is disproportionately high
        total_trans = len(transactions)
        cash_count = payment_methods.get("cash", 0)
        if cash_count > total_trans * 0.8 and total_trans > 10:
            anomalies.append(f"Unusually high cash transaction rate: {cash_count/total_trans:.1%}")

        summary = "No anomalies detected" if not anomalies else f"{len(anomalies)} anomaly type(s) detected"

        return {
            "anomalies": anomalies,
            "summary": summary,
            "transaction_count": len(transactions),
            "payment_method_distribution": payment_methods
        }
    
    def _get_investigation_recommendations(self, fraud_index: Dict) -> List[str]:
        recommendations = []
        if fraud_index["fraud_index"] >= 70:
            recommendations.append("Immediate investigation required")
            recommendations.append("Review all transactions from past 30 days")
            recommendations.append("Consider temporary suspension pending review")
        elif fraud_index["fraud_index"] >= 50:
            recommendations.append("Schedule manager review meeting")
            recommendations.append("Increase monitoring frequency")
        return recommendations
