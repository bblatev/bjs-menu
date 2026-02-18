"""Simple alerting system for critical events."""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("alerts")


class AlertManager:
    """Collects and exposes application alerts."""

    LEVELS = {"info": 0, "warning": 1, "critical": 2}

    def __init__(self):
        self.alerts: List[Dict] = []
        self.max_buffer = 200

    def alert(
        self,
        level: str,
        title: str,
        message: str,
        source: str = "system",
    ):
        entry = {
            "level": level,
            "title": title,
            "message": message,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.alerts.append(entry)
        if len(self.alerts) > self.max_buffer:
            self.alerts = self.alerts[-self.max_buffer:]

        log_level = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "critical": logging.CRITICAL,
        }
        logger.log(log_level.get(level, logging.INFO), f"[{source}] {title}: {message}")

    def get_recent(self, limit: int = 20, level: Optional[str] = None) -> List[Dict]:
        alerts = self.alerts
        if level:
            min_level = self.LEVELS.get(level, 0)
            alerts = [a for a in alerts if self.LEVELS.get(a["level"], 0) >= min_level]
        return list(reversed(alerts[-limit:]))


alert_manager = AlertManager()
