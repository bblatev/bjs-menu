"""Background task scheduler for periodic jobs (POS sync, cleanup, etc.)."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Lightweight asyncio-based task scheduler.

    Runs registered tasks at fixed intervals. Does not survive restarts
    — state is ephemeral. For durable scheduling, use Celery/APScheduler.
    """

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._task_handle: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler loop."""
        self._running = True
        logger.info("Task scheduler started")

        while self._running:
            now = datetime.now(timezone.utc)
            for name, task in list(self._tasks.items()):
                if now >= task["next_run"]:
                    try:
                        if asyncio.iscoroutinefunction(task["func"]):
                            await task["func"]()
                        else:
                            task["func"]()
                        task["last_run"] = now
                        task["run_count"] = task.get("run_count", 0) + 1
                        task["next_run"] = now + task["interval"]
                        task["last_error"] = None
                        logger.debug(f"Scheduled task '{name}' completed")
                    except Exception as e:
                        task["last_error"] = str(e)
                        task["next_run"] = now + task["interval"]
                        logger.error(f"Scheduled task '{name}' failed: {e}")
            await asyncio.sleep(60)

    def stop(self):
        self._running = False
        if self._task_handle:
            self._task_handle.cancel()

    def add_task(self, name: str, func: Callable, interval_seconds: int):
        self._tasks[name] = {
            "func": func,
            "interval": timedelta(seconds=interval_seconds),
            "next_run": datetime.now(timezone.utc) + timedelta(seconds=10),
            "last_run": None,
            "run_count": 0,
            "last_error": None,
        }
        logger.info(f"Scheduled task '{name}' every {interval_seconds}s")

    def remove_task(self, name: str):
        self._tasks.pop(name, None)

    def get_status(self) -> Dict[str, Any]:
        return {
            name: {
                "last_run": t["last_run"].isoformat() if t["last_run"] else None,
                "next_run": t["next_run"].isoformat(),
                "interval_seconds": int(t["interval"].total_seconds()),
                "run_count": t.get("run_count", 0),
                "last_error": t.get("last_error"),
            }
            for name, t in self._tasks.items()
        }


scheduler = TaskScheduler()
