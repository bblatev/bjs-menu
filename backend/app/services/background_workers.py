"""
Background Workers Service
Implements scheduled and async background tasks for gap features
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import traceback

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Background task status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Background task priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BackgroundTask:
    """Background task definition"""
    id: str
    name: str
    task_type: str
    venue_id: Optional[int] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    scheduled_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[Dict[str, Any]] = None


class BackgroundWorkerManager:
    """
    Manages background workers and task queue.
    Uses asyncio for concurrent task execution.
    """

    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self.running = False
        self.task_handlers: Dict[str, Callable] = {}
        self.task_history: Dict[str, BackgroundTask] = {}
        self.stats = defaultdict(int)

        # Register built-in handlers
        self._register_handlers()

    def _register_handlers(self):
        """Register built-in task handlers."""
        self.task_handlers = {
            # Review automation
            "process_review_requests": self._process_review_requests,
            "aggregate_reviews": self._aggregate_reviews,

            # Integration syncs
            "sync_7shifts": self._sync_7shifts,
            "sync_homebase": self._sync_homebase,
            "sync_marginedge": self._sync_marginedge,
            "sync_accounting": self._sync_accounting,

            # A/B Testing
            "check_experiment_significance": self._check_experiment_significance,
            "auto_complete_experiments": self._auto_complete_experiments,

            # Labor compliance
            "check_compliance": self._check_compliance,
            "send_break_reminders": self._send_break_reminders,
            "check_overtime": self._check_overtime,

            # Webhooks
            "deliver_webhook": self._deliver_webhook,
            "retry_failed_webhooks": self._retry_failed_webhooks,

            # Mobile sync
            "process_offline_transactions": self._process_offline_transactions,
            "send_push_notifications": self._send_push_notifications,

            # Hardware monitoring
            "check_device_health": self._check_device_health,
            "process_sensor_data": self._process_sensor_data,

            # BNPL
            "process_bnpl_captures": self._process_bnpl_captures,
            "reconcile_bnpl_transactions": self._reconcile_bnpl_transactions,

            # SSO
            "sync_sso_users": self._sync_sso_users,

            # Developer portal
            "cleanup_expired_tokens": self._cleanup_expired_tokens,
            "update_api_analytics": self._update_api_analytics,
        }

    async def start(self, db_session_factory):
        """Start the worker manager."""
        if self.running:
            return

        self.running = True
        self.db_session_factory = db_session_factory

        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        # Start scheduler
        self.scheduler = asyncio.create_task(self._scheduler())

        logger.info(f"Background worker manager started with {self.max_workers} workers")

    async def stop(self):
        """Stop the worker manager."""
        self.running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        if hasattr(self, 'scheduler'):
            self.scheduler.cancel()

        # Wait for tasks to finish
        await asyncio.gather(*self.workers, return_exceptions=True)

        logger.info("Background worker manager stopped")

    async def enqueue(self, task: BackgroundTask):
        """Add a task to the queue."""
        self.task_history[task.id] = task
        await self.task_queue.put(task)
        self.stats["tasks_enqueued"] += 1
        logger.debug(f"Task enqueued: {task.name} ({task.id})")

    async def schedule(
        self,
        task_type: str,
        name: str,
        payload: Dict[str, Any] = None,
        venue_id: int = None,
        delay_seconds: int = 0,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """Schedule a task for execution."""
        import uuid

        task = BackgroundTask(
            id=str(uuid.uuid4()),
            name=name,
            task_type=task_type,
            venue_id=venue_id,
            payload=payload or {},
            priority=priority,
            scheduled_at=datetime.utcnow() + timedelta(seconds=delay_seconds)
        )

        await self.enqueue(task)
        return task.id

    def get_task_status(self, task_id: str) -> Optional[BackgroundTask]:
        """Get task status by ID."""
        return self.task_history.get(task_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics."""
        return {
            **dict(self.stats),
            "queue_size": self.task_queue.qsize(),
            "active_workers": sum(1 for w in self.workers if not w.done()),
            "pending_tasks": sum(1 for t in self.task_history.values()
                                 if t.status == TaskStatus.PENDING),
            "running_tasks": sum(1 for t in self.task_history.values()
                                 if t.status == TaskStatus.RUNNING)
        }

    async def _worker(self, worker_name: str):
        """Worker coroutine that processes tasks from the queue."""
        logger.info(f"Worker {worker_name} started")

        while self.running:
            try:
                # Get task with timeout
                try:
                    task = await asyncio.wait_for(
                        self.task_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Check if scheduled time has arrived
                if task.scheduled_at > datetime.utcnow():
                    # Re-queue for later
                    await self.task_queue.put(task)
                    await asyncio.sleep(0.1)
                    continue

                # Process task
                await self._process_task(task, worker_name)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                self.stats["worker_errors"] += 1

        logger.info(f"Worker {worker_name} stopped")

    async def _process_task(self, task: BackgroundTask, worker_name: str):
        """Process a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        self.stats["tasks_started"] += 1

        logger.info(f"[{worker_name}] Processing task: {task.name} ({task.task_type})")

        try:
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"Unknown task type: {task.task_type}")

            # Execute handler
            async with self.db_session_factory() as db:
                result = await handler(db, task)
                task.result = result

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            self.stats["tasks_completed"] += 1

            logger.info(f"[{worker_name}] Task completed: {task.name}")

        except Exception as e:
            task.error_message = str(e)
            task.retry_count += 1

            if task.retry_count < task.max_retries:
                # Re-queue for retry with exponential backoff
                task.status = TaskStatus.PENDING
                task.scheduled_at = datetime.utcnow() + timedelta(
                    seconds=min(300, 2 ** task.retry_count * 10)
                )
                await self.task_queue.put(task)
                self.stats["tasks_retried"] += 1
                logger.warning(f"Task {task.name} failed, retry {task.retry_count}/{task.max_retries}")
            else:
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow()
                self.stats["tasks_failed"] += 1
                logger.error(f"Task {task.name} failed permanently: {e}\n{traceback.format_exc()}")

    async def _scheduler(self):
        """Scheduler for recurring tasks."""
        logger.info("Task scheduler started")

        while self.running:
            try:
                now = datetime.utcnow()

                # Schedule recurring tasks
                # Every 5 minutes: process review requests
                if now.minute % 5 == 0 and now.second < 5:
                    await self.schedule(
                        "process_review_requests",
                        "Process pending review requests",
                        priority=TaskPriority.NORMAL
                    )

                # Every 15 minutes: check experiment significance
                if now.minute % 15 == 0 and now.second < 5:
                    await self.schedule(
                        "check_experiment_significance",
                        "Check A/B experiment significance",
                        priority=TaskPriority.LOW
                    )

                # Every hour: sync integrations
                if now.minute == 0 and now.second < 5:
                    for sync_type in ["sync_7shifts", "sync_homebase", "sync_marginedge"]:
                        await self.schedule(
                            sync_type,
                            f"Hourly {sync_type} sync",
                            priority=TaskPriority.NORMAL
                        )

                # Every 30 minutes: check compliance
                if now.minute % 30 == 0 and now.second < 5:
                    await self.schedule(
                        "check_compliance",
                        "Check labor compliance",
                        priority=TaskPriority.HIGH
                    )
                    await self.schedule(
                        "send_break_reminders",
                        "Send break reminders",
                        priority=TaskPriority.HIGH
                    )

                # Every 10 minutes: retry failed webhooks
                if now.minute % 10 == 0 and now.second < 5:
                    await self.schedule(
                        "retry_failed_webhooks",
                        "Retry failed webhooks",
                        priority=TaskPriority.NORMAL
                    )

                # Every 5 minutes: check device health
                if now.minute % 5 == 0 and now.second < 5:
                    await self.schedule(
                        "check_device_health",
                        "Check hardware device health",
                        priority=TaskPriority.NORMAL
                    )

                # Daily at midnight: cleanup tasks
                if now.hour == 0 and now.minute == 0 and now.second < 5:
                    await self.schedule(
                        "cleanup_expired_tokens",
                        "Cleanup expired API tokens",
                        priority=TaskPriority.LOW
                    )
                    await self.schedule(
                        "update_api_analytics",
                        "Update API analytics",
                        priority=TaskPriority.LOW
                    )

                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(30)

        logger.info("Task scheduler stopped")

    # =============================================================================
    # TASK HANDLERS
    # =============================================================================

    async def _process_review_requests(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Process pending review requests."""
        from app.services.ab_testing_service import ReviewAutomationService
        from app.models.gap_features_models import ReviewRequest
        from sqlalchemy import select, and_

        now = datetime.utcnow()

        # Get all venues with pending requests
        result = await db.execute(
            select(ReviewRequest.venue_id).where(
                and_(
                    ReviewRequest.status == "scheduled",
                    ReviewRequest.scheduled_at <= now
                )
            ).distinct()
        )
        venue_ids = [r[0] for r in result.all()]

        total_processed = 0
        total_sent = 0
        total_failed = 0

        for venue_id in venue_ids:
            service = ReviewAutomationService(db)
            result = await service.process_pending_requests(venue_id)
            total_processed += result.get("processed", 0)
            total_sent += result.get("sent", 0)
            total_failed += result.get("failed", 0)

        return {
            "venues_processed": len(venue_ids),
            "total_processed": total_processed,
            "total_sent": total_sent,
            "total_failed": total_failed
        }

    async def _aggregate_reviews(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Aggregate reviews from external platforms."""
        # This would fetch reviews from Google, Yelp, etc.
        return {"status": "completed", "reviews_aggregated": 0}

    async def _sync_7shifts(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Sync with 7shifts."""
        from app.services.third_party_integrations_service import SevenShiftsIntegration
        from app.models.gap_features_models import IntegrationCredential
        from sqlalchemy import select

        # Get all venues with 7shifts integration
        result = await db.execute(
            select(IntegrationCredential).where(
                and_(
                    IntegrationCredential.integration_type == "7shifts",
                    IntegrationCredential.is_active == True
                )
            )
        )
        credentials = result.scalars().all()

        synced = 0
        failed = 0

        for cred in credentials:
            try:
                integration = SevenShiftsIntegration(db)
                integration.api_key = cred.credentials.get("api_key")
                integration.company_id = cred.credentials.get("company_id")

                await integration.sync_employees(cred.venue_id)
                await integration.sync_shifts(
                    cred.venue_id,
                    datetime.utcnow(),
                    datetime.utcnow() + timedelta(days=14)
                )
                synced += 1
            except Exception as e:
                logger.error(f"7shifts sync failed for venue {cred.venue_id}: {e}")
                failed += 1

        return {"synced": synced, "failed": failed}

    async def _sync_homebase(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Sync with Homebase."""
        from app.services.third_party_integrations_service import HomebaseIntegration
        from app.models.gap_features_models import IntegrationCredential
        from sqlalchemy import select

        result = await db.execute(
            select(IntegrationCredential).where(
                and_(
                    IntegrationCredential.integration_type == "homebase",
                    IntegrationCredential.is_active == True
                )
            )
        )
        credentials = result.scalars().all()

        synced = 0
        for cred in credentials:
            try:
                integration = HomebaseIntegration(db)
                integration.api_key = cred.credentials.get("api_key")
                integration.location_id = cred.credentials.get("location_id")
                await integration.sync_timesheets(
                    cred.venue_id,
                    datetime.utcnow() - timedelta(days=1),
                    datetime.utcnow()
                )
                synced += 1
            except Exception as e:
                logger.error(f"Homebase sync failed: {e}")

        return {"synced": synced}

    async def _sync_marginedge(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Sync with MarginEdge."""
        from app.services.third_party_integrations_service import MarginEdgeIntegration
        from app.models.gap_features_models import IntegrationCredential
        from sqlalchemy import select

        result = await db.execute(
            select(IntegrationCredential).where(
                and_(
                    IntegrationCredential.integration_type == "marginedge",
                    IntegrationCredential.is_active == True
                )
            )
        )
        credentials = result.scalars().all()

        synced = 0
        for cred in credentials:
            try:
                integration = MarginEdgeIntegration(db)
                integration.api_key = cred.credentials.get("api_key")
                integration.restaurant_id = cred.credentials.get("restaurant_id")
                await integration.sync_invoices(
                    cred.venue_id,
                    datetime.utcnow() - timedelta(days=7),
                    datetime.utcnow()
                )
                synced += 1
            except Exception as e:
                logger.error(f"MarginEdge sync failed: {e}")

        return {"synced": synced}

    async def _sync_accounting(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Sync with accounting systems (QuickBooks, Xero)."""
        from app.services.third_party_integrations_service import AccountingSyncService
        from app.models.gap_features_models import IntegrationCredential
        from sqlalchemy import select

        result = await db.execute(
            select(IntegrationCredential).where(
                and_(
                    IntegrationCredential.integration_type.in_(["quickbooks", "xero"]),
                    IntegrationCredential.is_active == True
                )
            )
        )
        credentials = result.scalars().all()

        synced = 0
        for cred in credentials:
            try:
                service = AccountingSyncService(db)
                await service.sync_sales(
                    cred.venue_id,
                    cred.integration_type,
                    datetime.utcnow() - timedelta(days=1),
                    datetime.utcnow()
                )
                synced += 1
            except Exception as e:
                logger.error(f"Accounting sync failed: {e}")

        return {"synced": synced}

    async def _check_experiment_significance(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Check if running experiments have reached statistical significance."""
        from app.services.ab_testing_service import ABTestingService
        from app.models.gap_features_models import ABExperiment, ExperimentStatus
        from sqlalchemy import select

        result = await db.execute(
            select(ABExperiment).where(
                ABExperiment.status == ExperimentStatus.RUNNING
            )
        )
        experiments = result.scalars().all()

        significant = 0
        for exp in experiments:
            service = ABTestingService(db)
            results = await service.get_experiment_results(exp.id)

            if results.get("statistical_significance"):
                significant += 1
                # Emit WebSocket event
                from app.services.websocket_service import emit_experiment_significance
                await emit_experiment_significance(
                    venue_id=exp.venue_id,
                    experiment_id=str(exp.id),
                    experiment_name=exp.name,
                    is_significant=True,
                    confidence_level=0.95
                )

        return {"experiments_checked": len(experiments), "significant": significant}

    async def _auto_complete_experiments(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Auto-complete experiments that have reached their end date."""
        from app.services.ab_testing_service import ABTestingService
        from app.models.gap_features_models import ABExperiment, ExperimentStatus
        from sqlalchemy import select, and_

        now = datetime.utcnow()

        result = await db.execute(
            select(ABExperiment).where(
                and_(
                    ABExperiment.status == ExperimentStatus.RUNNING,
                    ABExperiment.end_date.isnot(None),
                    ABExperiment.end_date <= now
                )
            )
        )
        experiments = result.scalars().all()

        completed = 0
        for exp in experiments:
            service = ABTestingService(db)
            results = await service.get_experiment_results(exp.id)

            # Determine winner based on target metric
            variants = results.get("variants", [])
            if variants:
                winner = max(variants, key=lambda v: v.get("conversion_rate", 0))
                await service.complete_experiment(exp.id, winner.get("id"))
                completed += 1

        return {"experiments_completed": completed}

    async def _check_compliance(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Check labor compliance for active shifts."""
        from app.services.team_chat_service import LaborComplianceService
        from app.services.websocket_service import emit_compliance_violation

        # This would check all active shifts against compliance rules
        return {"violations_found": 0}

    async def _send_break_reminders(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Send break reminders to staff who need breaks."""
        from app.services.websocket_service import emit_break_reminder

        # This would check shift durations and send reminders
        return {"reminders_sent": 0}

    async def _check_overtime(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Check for overtime conditions."""
        from app.services.websocket_service import emit_overtime_warning

        # This would check weekly hours and send warnings
        return {"warnings_sent": 0}

    async def _deliver_webhook(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Deliver a webhook to a registered endpoint."""
        import aiohttp
        import hmac
        import hashlib
        from app.services.websocket_service import emit_webhook_delivery

        payload = task.payload
        endpoint_url = payload.get("endpoint_url")
        event_type = payload.get("event_type")
        data = payload.get("data")
        secret = payload.get("secret")
        webhook_id = payload.get("webhook_id")

        # Generate signature
        body = str(data).encode()
        signature = hmac.new(
            secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint_url,
                    json=data,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Webhook-Event": event_type
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    success = 200 <= response.status < 300

                    if task.venue_id:
                        await emit_webhook_delivery(
                            venue_id=task.venue_id,
                            webhook_id=webhook_id,
                            endpoint_url=endpoint_url,
                            event_type=event_type,
                            success=success,
                            response_status=response.status
                        )

                    return {
                        "success": success,
                        "status_code": response.status
                    }

        except Exception as e:
            if task.venue_id:
                await emit_webhook_delivery(
                    venue_id=task.venue_id,
                    webhook_id=webhook_id,
                    endpoint_url=endpoint_url,
                    event_type=event_type,
                    success=False,
                    error_message=str(e)
                )
            raise

    async def _retry_failed_webhooks(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Retry failed webhook deliveries."""
        from app.models.gap_features_models import WebhookDelivery
        from sqlalchemy import select, and_

        cutoff = datetime.utcnow() - timedelta(hours=24)

        result = await db.execute(
            select(WebhookDelivery).where(
                and_(
                    WebhookDelivery.success == False,
                    WebhookDelivery.retry_count < 5,
                    WebhookDelivery.created_at > cutoff
                )
            ).limit(50)
        )
        failed_deliveries = result.scalars().all()

        retried = 0
        for delivery in failed_deliveries:
            await self.schedule(
                "deliver_webhook",
                f"Retry webhook {delivery.id}",
                payload={
                    "webhook_id": str(delivery.webhook_id),
                    "endpoint_url": delivery.endpoint_url,
                    "event_type": delivery.event_type,
                    "data": delivery.payload,
                    "secret": delivery.secret
                },
                venue_id=delivery.venue_id,
                priority=TaskPriority.NORMAL
            )
            delivery.retry_count += 1
            retried += 1

        await db.commit()
        return {"retried": retried}

    async def _process_offline_transactions(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Process offline transactions that have been synced."""
        from app.services.mobile_offline_service import MobileOfflineService

        venue_id = task.payload.get("venue_id")
        device_id = task.payload.get("device_id")
        transactions = task.payload.get("transactions", [])

        if not venue_id or not transactions:
            return {"processed": 0}

        service = MobileOfflineService(db)
        result = await service.process_offline_transactions(
            venue_id=venue_id,
            device_id=device_id,
            transactions=transactions
        )

        return result

    async def _send_push_notifications(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Send push notifications to mobile devices."""
        from app.services.mobile_offline_service import PushNotificationService
        from app.models.gap_features_models import PushNotification
        from sqlalchemy import select, and_

        now = datetime.utcnow()

        result = await db.execute(
            select(PushNotification).where(
                and_(
                    PushNotification.status == "pending",
                    PushNotification.scheduled_at <= now
                )
            ).limit(100)
        )
        notifications = result.scalars().all()

        sent = 0
        for notif in notifications:
            service = PushNotificationService(db)
            try:
                await service.send_notification(
                    device_token=notif.device_token,
                    title=notif.title,
                    body=notif.body,
                    data=notif.data
                )
                notif.status = "sent"
                notif.sent_at = now
                sent += 1
            except Exception as e:
                notif.status = "failed"
                notif.error_message = str(e)

        await db.commit()
        return {"sent": sent}

    async def _check_device_health(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Check health of registered hardware devices."""
        from app.services.hardware_sdk_service import HardwareSDKService
        from app.models.gap_features_models import SDKHardwareDevice as HardwareDevice
        from app.services.websocket_service import emit_device_status
        from sqlalchemy import select

        result = await db.execute(
            select(HardwareDevice).where(HardwareDevice.is_active == True)
        )
        devices = result.scalars().all()

        offline = 0
        for device in devices:
            # Check last heartbeat
            if device.last_heartbeat:
                if datetime.utcnow() - device.last_heartbeat > timedelta(minutes=5):
                    if device.status != "offline":
                        device.status = "offline"
                        offline += 1
                        await emit_device_status(
                            venue_id=device.venue_id,
                            device_id=str(device.id),
                            device_type=device.device_type,
                            status="disconnected",
                            device_name=device.name
                        )

        await db.commit()
        return {"devices_checked": len(devices), "offline": offline}

    async def _process_sensor_data(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Process sensor data from hardware devices."""
        return {"processed": 0}

    async def _process_bnpl_captures(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Process BNPL payment captures."""
        from app.services.hardware_sdk_service import BNPLService
        from app.models.gap_features_models import BNPLTransaction
        from sqlalchemy import select, and_

        result = await db.execute(
            select(BNPLTransaction).where(
                and_(
                    BNPLTransaction.status == "authorized",
                    BNPLTransaction.auto_capture == True
                )
            )
        )
        transactions = result.scalars().all()

        captured = 0
        for txn in transactions:
            service = BNPLService(db)
            try:
                await service.capture_payment(txn.id)
                captured += 1
            except Exception as e:
                logger.error(f"BNPL capture failed: {e}")

        return {"captured": captured}

    async def _reconcile_bnpl_transactions(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Reconcile BNPL transactions with providers."""
        return {"reconciled": 0}

    async def _sync_sso_users(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Sync users from SSO providers (SCIM)."""
        return {"synced": 0}

    async def _cleanup_expired_tokens(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Cleanup expired API tokens."""
        from app.models.gap_features_models import APIKey
        from sqlalchemy import select, and_

        now = datetime.utcnow()

        result = await db.execute(
            select(APIKey).where(
                and_(
                    APIKey.expires_at.isnot(None),
                    APIKey.expires_at < now
                )
            )
        )
        expired_keys = result.scalars().all()

        for key in expired_keys:
            key.is_active = False

        await db.commit()
        return {"expired_keys_deactivated": len(expired_keys)}

    async def _update_api_analytics(
        self,
        db,
        task: BackgroundTask
    ) -> Dict[str, Any]:
        """Update API usage analytics."""
        return {"updated": True}


# Global worker manager instance
worker_manager = BackgroundWorkerManager()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def schedule_task(
    task_type: str,
    name: str,
    payload: Dict[str, Any] = None,
    venue_id: int = None,
    delay_seconds: int = 0,
    priority: TaskPriority = TaskPriority.NORMAL
) -> str:
    """Convenience function to schedule a background task."""
    return await worker_manager.schedule(
        task_type=task_type,
        name=name,
        payload=payload,
        venue_id=venue_id,
        delay_seconds=delay_seconds,
        priority=priority
    )


async def schedule_webhook_delivery(
    venue_id: int,
    webhook_id: str,
    endpoint_url: str,
    event_type: str,
    data: Dict[str, Any],
    secret: str
) -> str:
    """Schedule a webhook delivery."""
    return await schedule_task(
        task_type="deliver_webhook",
        name=f"Deliver webhook: {event_type}",
        payload={
            "webhook_id": webhook_id,
            "endpoint_url": endpoint_url,
            "event_type": event_type,
            "data": data,
            "secret": secret
        },
        venue_id=venue_id,
        priority=TaskPriority.HIGH
    )


async def schedule_integration_sync(
    venue_id: int,
    integration_type: str
) -> str:
    """Schedule an integration sync."""
    task_type_map = {
        "7shifts": "sync_7shifts",
        "homebase": "sync_homebase",
        "marginedge": "sync_marginedge",
        "quickbooks": "sync_accounting",
        "xero": "sync_accounting"
    }

    task_type = task_type_map.get(integration_type)
    if not task_type:
        raise ValueError(f"Unknown integration type: {integration_type}")

    return await schedule_task(
        task_type=task_type,
        name=f"Sync {integration_type}",
        payload={"venue_id": venue_id},
        venue_id=venue_id,
        priority=TaskPriority.NORMAL
    )


async def schedule_push_notification(
    venue_id: int,
    user_id: str,
    title: str,
    body: str,
    data: Dict[str, Any] = None,
    delay_seconds: int = 0
) -> str:
    """Schedule a push notification."""
    return await schedule_task(
        task_type="send_push_notifications",
        name=f"Push notification: {title}",
        payload={
            "user_id": user_id,
            "title": title,
            "body": body,
            "data": data
        },
        venue_id=venue_id,
        delay_seconds=delay_seconds,
        priority=TaskPriority.HIGH
    )
