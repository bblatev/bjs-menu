"""Enhanced Table Management Service.

Closes the 5% gap vs TouchBistro with:
- Extended table states (dirty, maintenance, out_of_service)
- Guest-facing waitlist display with position tracking
- Turn time alerts for slow tables
- Server auto-load balancing
- Smart party-to-table matching
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Extended Table States
# ---------------------------------------------------------------------------

EXTENDED_TABLE_STATES = [
    "available",
    "occupied",
    "reserved",
    "cleaning",
    "dirty",           # needs bussing
    "maintenance",     # under repair
    "out_of_service",  # permanently offline
]

TABLE_STATE_TRANSITIONS = {
    "available": ["occupied", "reserved", "maintenance", "out_of_service"],
    "occupied": ["dirty", "cleaning", "available"],
    "reserved": ["occupied", "available"],
    "cleaning": ["available", "maintenance"],
    "dirty": ["cleaning", "available", "maintenance"],
    "maintenance": ["available", "out_of_service"],
    "out_of_service": ["maintenance", "available"],
}


class TableEnhancementsService:
    """Enhanced table management features."""

    def __init__(self):
        # In-memory store for demo; production uses DB
        self._table_metadata: Dict[int, Dict[str, Any]] = {}
        self._turn_alerts: List[Dict[str, Any]] = []
        self._maintenance_log: List[Dict[str, Any]] = []
        self._server_workloads: Dict[int, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Extended States
    # ------------------------------------------------------------------

    def validate_state_transition(self, current_state: str, new_state: str) -> bool:
        """Check if a state transition is allowed."""
        allowed = TABLE_STATE_TRANSITIONS.get(current_state, [])
        return new_state in allowed

    def get_extended_states(self) -> List[Dict[str, Any]]:
        """Return all supported table states with descriptions."""
        state_info = {
            "available": {"color": "#22c55e", "icon": "check-circle", "description": "Ready for guests"},
            "occupied": {"color": "#3b82f6", "icon": "users", "description": "Currently in use"},
            "reserved": {"color": "#a855f7", "icon": "clock", "description": "Reserved for upcoming party"},
            "cleaning": {"color": "#f59e0b", "icon": "sparkles", "description": "Being cleaned"},
            "dirty": {"color": "#ef4444", "icon": "alert-triangle", "description": "Needs bussing"},
            "maintenance": {"color": "#6b7280", "icon": "wrench", "description": "Under repair"},
            "out_of_service": {"color": "#1f2937", "icon": "x-circle", "description": "Offline"},
        }
        return [
            {"state": s, **state_info.get(s, {})}
            for s in EXTENDED_TABLE_STATES
        ]

    def set_table_metadata(
        self,
        table_id: int,
        server_name: Optional[str] = None,
        estimated_clear_time: Optional[datetime] = None,
        maintenance_notes: Optional[str] = None,
        accessibility: Optional[bool] = None,
        high_chair_available: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Set extended metadata for a table (server, clear time, etc.)."""
        meta = self._table_metadata.get(table_id, {})
        if server_name is not None:
            meta["server_name"] = server_name
        if estimated_clear_time is not None:
            meta["estimated_clear_time"] = estimated_clear_time.isoformat()
        if maintenance_notes is not None:
            meta["maintenance_notes"] = maintenance_notes
        if accessibility is not None:
            meta["accessibility"] = accessibility
        if high_chair_available is not None:
            meta["high_chair_available"] = high_chair_available
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._table_metadata[table_id] = meta
        return meta

    def get_table_metadata(self, table_id: int) -> Dict[str, Any]:
        return self._table_metadata.get(table_id, {})

    # ------------------------------------------------------------------
    # Maintenance Tracking
    # ------------------------------------------------------------------

    def schedule_maintenance(
        self,
        table_id: int,
        reason: str,
        scheduled_at: Optional[datetime] = None,
        estimated_duration_minutes: int = 30,
        assigned_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Schedule table for maintenance."""
        entry = {
            "id": len(self._maintenance_log) + 1,
            "table_id": table_id,
            "reason": reason,
            "scheduled_at": (scheduled_at or datetime.now(timezone.utc)).isoformat(),
            "estimated_duration_minutes": estimated_duration_minutes,
            "assigned_to": assigned_to,
            "status": "scheduled",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        self._maintenance_log.append(entry)
        return entry

    def complete_maintenance(self, maintenance_id: int, notes: Optional[str] = None) -> Dict[str, Any]:
        """Mark maintenance as complete."""
        for entry in self._maintenance_log:
            if entry["id"] == maintenance_id:
                entry["status"] = "completed"
                entry["completed_at"] = datetime.now(timezone.utc).isoformat()
                if notes:
                    entry["completion_notes"] = notes
                return entry
        return {"error": "Maintenance entry not found"}

    def get_maintenance_history(
        self, table_id: Optional[int] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get maintenance history, optionally filtered."""
        results = self._maintenance_log
        if table_id is not None:
            results = [m for m in results if m["table_id"] == table_id]
        if status:
            results = [m for m in results if m["status"] == status]
        return results

    # ------------------------------------------------------------------
    # Guest-Facing Waitlist Display
    # ------------------------------------------------------------------

    def get_guest_waitlist_display(
        self, waitlist_entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate guest-facing waitlist data with positions and estimates.

        Takes a list of waitlist entries (from the Waitlist model) and returns
        display-friendly data for a public kiosk or guest web page.
        """
        active = [e for e in waitlist_entries if e.get("status") in ("waiting", "notified")]
        active.sort(key=lambda e: e.get("created_at", ""))

        display_entries = []
        for i, entry in enumerate(active):
            display_entries.append({
                "position": i + 1,
                "party_name": self._mask_name(entry.get("guest_name", "Guest")),
                "party_size": entry.get("party_size", 0),
                "quoted_wait_minutes": entry.get("estimated_wait_minutes", 0),
                "elapsed_minutes": self._elapsed_minutes(entry.get("created_at")),
                "status": entry.get("status"),
            })

        avg_wait = 0
        if display_entries:
            waits = [e["quoted_wait_minutes"] for e in display_entries if e["quoted_wait_minutes"] > 0]
            avg_wait = sum(waits) // max(len(waits), 1)

        return {
            "total_waiting": len(display_entries),
            "average_wait_minutes": avg_wait,
            "entries": display_entries,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_guest_position(
        self, waitlist_entries: List[Dict[str, Any]], guest_id: int
    ) -> Dict[str, Any]:
        """Get a specific guest's position in the waitlist."""
        active = [e for e in waitlist_entries if e.get("status") in ("waiting", "notified")]
        active.sort(key=lambda e: e.get("created_at", ""))

        for i, entry in enumerate(active):
            if entry.get("id") == guest_id:
                return {
                    "position": i + 1,
                    "total_in_queue": len(active),
                    "estimated_wait_minutes": entry.get("estimated_wait_minutes", 0),
                    "elapsed_minutes": self._elapsed_minutes(entry.get("created_at")),
                    "status": entry.get("status"),
                }
        return {"error": "Guest not found in waitlist"}

    @staticmethod
    def _mask_name(name: str) -> str:
        """Mask guest name for privacy (show first letter + last initial)."""
        parts = name.strip().split()
        if not parts:
            return "Guest"
        if len(parts) == 1:
            return parts[0][0] + "***"
        return parts[0][0] + "*** " + parts[-1][0] + "."

    @staticmethod
    def _elapsed_minutes(created_at: Optional[str]) -> int:
        if not created_at:
            return 0
        try:
            if isinstance(created_at, str):
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                dt = created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elapsed = datetime.now(timezone.utc) - dt
            return max(0, int(elapsed.total_seconds() / 60))
        except (ValueError, TypeError):
            return 0

    # ------------------------------------------------------------------
    # Turn Time Alerts
    # ------------------------------------------------------------------

    def check_turn_time_alerts(
        self,
        active_turns: List[Dict[str, Any]],
        threshold_minutes: int = 90,
    ) -> List[Dict[str, Any]]:
        """Check active table turns for slow tables that exceed threshold.

        Returns alerts for tables exceeding expected turn time.
        """
        alerts = []
        now = datetime.now(timezone.utc)

        for turn in active_turns:
            seated_at_str = turn.get("seated_at")
            if not seated_at_str:
                continue

            try:
                if isinstance(seated_at_str, str):
                    seated_at = datetime.fromisoformat(seated_at_str.replace("Z", "+00:00"))
                else:
                    seated_at = seated_at_str
                if seated_at.tzinfo is None:
                    seated_at = seated_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            elapsed = (now - seated_at).total_seconds() / 60
            expected = turn.get("expected_turn_minutes", threshold_minutes)

            if elapsed > expected:
                overage = int(elapsed - expected)
                severity = "warning"
                if overage > 30:
                    severity = "critical"
                elif overage > 15:
                    severity = "high"

                alert = {
                    "table_id": turn.get("table_id"),
                    "table_number": turn.get("table_number"),
                    "elapsed_minutes": int(elapsed),
                    "expected_minutes": expected,
                    "overage_minutes": overage,
                    "severity": severity,
                    "guest_count": turn.get("guest_count", 0),
                    "server_name": turn.get("server_name"),
                    "suggestions": self._get_turn_suggestions(turn, elapsed),
                }
                alerts.append(alert)

        self._turn_alerts = alerts
        return alerts

    @staticmethod
    def _get_turn_suggestions(turn: Dict[str, Any], elapsed_minutes: float) -> List[str]:
        """Generate actionable suggestions for slow tables."""
        suggestions = []
        check_requested = turn.get("check_requested_at")
        food_delivered = turn.get("food_delivered_at")

        if not food_delivered and elapsed_minutes > 30:
            suggestions.append("Food has not been delivered - check kitchen status")
        if food_delivered and not check_requested and elapsed_minutes > 60:
            suggestions.append("Suggest dessert or present the check")
        if check_requested and elapsed_minutes > 75:
            suggestions.append("Check has been requested - expedite payment processing")
        if elapsed_minutes > 120:
            suggestions.append("Table has been occupied for 2+ hours - consider gentle check-in")

        return suggestions

    # ------------------------------------------------------------------
    # Server Load Balancing
    # ------------------------------------------------------------------

    def calculate_server_workload(
        self,
        servers: List[Dict[str, Any]],
        table_assignments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Calculate workload per server for load balancing."""
        workloads = []
        for server in servers:
            server_id = server.get("id")
            assigned = [
                t for t in table_assignments
                if t.get("server_id") == server_id
            ]
            total_guests = sum(t.get("guest_count", 0) for t in assigned)

            workload = {
                "server_id": server_id,
                "server_name": server.get("name", ""),
                "table_count": len(assigned),
                "guest_count": total_guests,
                "tables": [t.get("table_number") for t in assigned],
                "workload_score": len(assigned) * 2 + total_guests,
                "available_capacity": max(0, 6 - len(assigned)),
            }
            workloads.append(workload)

        workloads.sort(key=lambda w: w["workload_score"])
        self._server_workloads = {w["server_id"]: w for w in workloads}
        return workloads

    def suggest_server_for_table(
        self,
        table: Dict[str, Any],
        servers: List[Dict[str, Any]],
        table_assignments: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Suggest the best server for a new table based on load balancing."""
        workloads = self.calculate_server_workload(servers, table_assignments)
        table_area = table.get("area", "")

        # Prefer servers already assigned to the same area
        area_servers = [
            w for w in workloads
            if w["available_capacity"] > 0
            and any(
                t_area == table_area
                for t in table_assignments
                if t.get("server_id") == w["server_id"]
                for t_area in [t.get("area", "")]
            )
        ]

        if area_servers:
            best = area_servers[0]
        elif workloads:
            available = [w for w in workloads if w["available_capacity"] > 0]
            best = available[0] if available else workloads[0]
        else:
            return {"error": "No servers available"}

        return {
            "suggested_server_id": best["server_id"],
            "suggested_server_name": best["server_name"],
            "current_table_count": best["table_count"],
            "current_guest_count": best["guest_count"],
            "reason": "Lowest workload score in section" if area_servers else "Lowest overall workload",
        }

    # ------------------------------------------------------------------
    # Smart Party-to-Table Matching
    # ------------------------------------------------------------------

    def match_party_to_table(
        self,
        party_size: int,
        available_tables: List[Dict[str, Any]],
        preferences: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Smart matching of party size to available tables.

        Considers:
        - Capacity fit (don't seat 2 at an 8-top if a 2-top is free)
        - Seating preferences (indoor, outdoor, booth, window, bar)
        - Accessibility requirements
        - VIP tables
        """
        prefs = preferences or {}
        preferred_area = prefs.get("area")
        needs_accessibility = prefs.get("accessibility", False)
        is_vip = prefs.get("vip", False)
        prefers_booth = prefs.get("booth", False)
        prefers_window = prefs.get("window", False)

        scored: List[Tuple[float, Dict[str, Any]]] = []

        for table in available_tables:
            capacity = table.get("capacity", 4)
            if capacity < party_size:
                continue  # Table too small

            score = 100.0

            # Penalize waste (seating 2 at an 8-top)
            waste = capacity - party_size
            score -= waste * 8

            # Prefer exact fit
            if waste == 0:
                score += 20
            elif waste == 1:
                score += 10

            # Area preference
            if preferred_area and table.get("area", "").lower() == preferred_area.lower():
                score += 25

            # Accessibility
            meta = self._table_metadata.get(table.get("id", 0), {})
            if needs_accessibility:
                if meta.get("accessibility"):
                    score += 30
                else:
                    score -= 50

            # Booth / window
            table_type = table.get("type", "").lower()
            if prefers_booth and "booth" in table_type:
                score += 15
            if prefers_window and "window" in table_type:
                score += 15

            # VIP priority
            if is_vip and table.get("area", "").lower() == "vip":
                score += 30

            # High chair availability
            if prefs.get("high_chair") and meta.get("high_chair_available"):
                score += 10

            scored.append((score, {
                **table,
                "match_score": round(score, 1),
                "waste_seats": waste,
            }))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in scored[:5]]


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service: Optional[TableEnhancementsService] = None


def get_table_enhancements_service() -> TableEnhancementsService:
    global _service
    if _service is None:
        _service = TableEnhancementsService()
    return _service
