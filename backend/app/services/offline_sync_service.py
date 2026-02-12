"""
Offline Sync Service

Handles terminal offline queue management and synchronization.

When OFFLINE_SYNC_ENABLED feature flag is active:
- Terminals can queue operations while offline
- Operations are synced when connectivity is restored
- Conflicts are detected and flagged for resolution
"""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.feature_flags import is_enabled
from app.models.offline_sync import (
    OfflineQueueItem,
    SyncStatus,
    TerminalTerminalMenuVersion,
    TerminalSyncState,
    SyncConflict,
)


class OfflineSyncService:
    """
    Service for managing offline sync operations.

    All methods check OFFLINE_SYNC_ENABLED feature flag.
    """

    MAX_SYNC_ATTEMPTS = 5
    SYNC_BATCH_SIZE = 50

    def __init__(self, db: Session):
        self.db = db

    def is_active(self) -> bool:
        """Check if offline sync feature is enabled."""
        return is_enabled("OFFLINE_SYNC_ENABLED")

    def queue_operation(
        self,
        venue_id: int,
        terminal_id: str,
        operation_type: str,
        operation_data: Dict[str, Any],
        operation_id: Optional[str] = None,
        depends_on: Optional[str] = None,
    ) -> Optional[OfflineQueueItem]:
        """
        Queue an operation from an offline terminal.

        Args:
            venue_id: Venue ID
            terminal_id: Terminal identifier
            operation_type: Type of operation (create_order, payment, etc.)
            operation_data: Full operation payload
            operation_id: Client-generated UUID (generated if not provided)
            depends_on: Previous operation ID this depends on

        Returns:
            OfflineQueueItem if created, None if feature disabled
        """
        if not self.is_active():
            return None

        # Generate operation ID if not provided
        if not operation_id:
            operation_id = str(uuid.uuid4())

        # Get next sequence number for terminal
        sequence = self._get_next_sequence(venue_id, terminal_id)

        item = OfflineQueueItem(
            venue_id=venue_id,
            terminal_id=terminal_id,
            operation_type=operation_type,
            operation_id=operation_id,
            operation_data=operation_data,
            sequence_number=sequence,
            depends_on=depends_on,
            sync_status=SyncStatus.PENDING,
        )

        self.db.add(item)

        # Update terminal sync state
        self._update_terminal_state(venue_id, terminal_id, pending_delta=1)

        self.db.commit()
        self.db.refresh(item)

        return item

    def sync_pending_operations(
        self,
        venue_id: int,
        terminal_id: str,
        processor_callback: callable,
    ) -> Dict[str, Any]:
        """
        Sync pending operations for a terminal.

        Args:
            venue_id: Venue ID
            terminal_id: Terminal identifier
            processor_callback: Function to process each operation

        Returns:
            Sync result summary
        """
        if not self.is_active():
            return {"status": "disabled"}

        pending = self.db.query(OfflineQueueItem).filter(
            OfflineQueueItem.venue_id == venue_id,
            OfflineQueueItem.terminal_id == terminal_id,
            OfflineQueueItem.sync_status == SyncStatus.PENDING,
            OfflineQueueItem.sync_attempts < self.MAX_SYNC_ATTEMPTS,
        ).order_by(OfflineQueueItem.sequence_number).limit(self.SYNC_BATCH_SIZE).all()

        synced = 0
        failed = 0
        conflicts = 0

        for item in pending:
            try:
                # Check dependencies
                if item.depends_on:
                    dep = self.db.query(OfflineQueueItem).filter(
                        OfflineQueueItem.operation_id == item.depends_on
                    ).first()
                    if dep and dep.sync_status != SyncStatus.COMPLETED:
                        continue  # Skip, dependency not synced yet

                # Mark as in progress
                item.sync_status = SyncStatus.IN_PROGRESS
                item.sync_attempts += 1
                item.last_sync_attempt = datetime.utcnow()
                self.db.commit()

                # Process operation
                result = processor_callback(item.operation_type, item.operation_data)

                if result.get("success"):
                    item.sync_status = SyncStatus.COMPLETED
                    item.server_id = result.get("id")
                    item.server_response = result
                    item.synced_at = datetime.utcnow()
                    synced += 1
                elif result.get("conflict"):
                    item.sync_status = SyncStatus.CONFLICT
                    self._create_conflict(item, result)
                    conflicts += 1
                else:
                    item.sync_status = SyncStatus.FAILED
                    item.sync_error = result.get("error", "Unknown error")
                    failed += 1

            except Exception as e:
                item.sync_status = SyncStatus.FAILED
                item.sync_error = str(e)
                failed += 1

            self.db.commit()

        # Update terminal state
        self._update_terminal_state(
            venue_id, terminal_id,
            pending_delta=-synced,
            synced_delta=synced,
        )

        return {
            "status": "ok",
            "synced": synced,
            "failed": failed,
            "conflicts": conflicts,
            "remaining": self._count_pending(venue_id, terminal_id),
        }

    def get_menu_version(self, venue_id: int) -> Optional[TerminalMenuVersion]:
        """Get current active menu version for venue."""
        if not is_enabled("MENU_VERSIONING_ENABLED"):
            return None

        return self.db.query(TerminalMenuVersion).filter(
            TerminalMenuVersion.venue_id == venue_id,
            TerminalMenuVersion.is_active == True,
        ).order_by(TerminalMenuVersion.version_number.desc()).first()

    def create_menu_version(
        self,
        venue_id: int,
        menu_data: Dict[str, Any],
        changes_summary: Optional[List[str]] = None,
        created_by: Optional[int] = None,
    ) -> Optional[TerminalMenuVersion]:
        """Create a new menu version."""
        if not is_enabled("MENU_VERSIONING_ENABLED"):
            return None

        # Calculate hash
        menu_hash = hashlib.sha256(
            json.dumps(menu_data, sort_keys=True).encode()
        ).hexdigest()

        # Get next version number
        latest = self.db.query(TerminalMenuVersion).filter(
            TerminalMenuVersion.venue_id == venue_id
        ).order_by(TerminalMenuVersion.version_number.desc()).first()

        next_version = (latest.version_number + 1) if latest else 1

        version = TerminalMenuVersion(
            venue_id=venue_id,
            version_number=next_version,
            version_hash=menu_hash,
            changes_summary=changes_summary,
            menu_snapshot=menu_data,
            created_by=created_by,
        )

        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)

        return version

    def check_menu_update(
        self,
        venue_id: int,
        terminal_version: int,
    ) -> Dict[str, Any]:
        """
        Check if terminal needs menu update.

        Returns update info if terminal version is outdated.
        """
        current = self.get_menu_version(venue_id)

        if not current:
            return {"needs_update": False}

        if terminal_version >= current.version_number:
            return {"needs_update": False}

        return {
            "needs_update": True,
            "current_version": current.version_number,
            "terminal_version": terminal_version,
            "menu_snapshot": current.menu_snapshot,
            "changes_summary": current.changes_summary,
        }

    def record_heartbeat(
        self,
        venue_id: int,
        terminal_id: str,
        is_online: bool = True,
    ) -> None:
        """Record terminal heartbeat."""
        if not self.is_active():
            return

        state = self.db.query(TerminalSyncState).filter(
            TerminalSyncState.venue_id == venue_id,
            TerminalSyncState.terminal_id == terminal_id,
        ).first()

        if not state:
            state = TerminalSyncState(
                venue_id=venue_id,
                terminal_id=terminal_id,
            )
            self.db.add(state)

        state.last_heartbeat = datetime.utcnow()

        if is_online and not state.is_online:
            # Coming back online
            state.is_online = True
            state.offline_since = None
        elif not is_online and state.is_online:
            # Going offline
            state.is_online = False
            state.offline_since = datetime.utcnow()

        self.db.commit()

    def get_terminal_status(
        self,
        venue_id: int,
        terminal_id: str,
    ) -> Dict[str, Any]:
        """Get terminal sync status."""
        if not self.is_active():
            return {"status": "disabled"}

        state = self.db.query(TerminalSyncState).filter(
            TerminalSyncState.venue_id == venue_id,
            TerminalSyncState.terminal_id == terminal_id,
        ).first()

        if not state:
            return {
                "terminal_id": terminal_id,
                "is_online": True,
                "pending_operations": 0,
                "last_sync": None,
            }

        return {
            "terminal_id": terminal_id,
            "is_online": state.is_online,
            "pending_operations": state.pending_items_count,
            "last_sync": state.last_sync_at.isoformat() if state.last_sync_at else None,
            "menu_version": state.current_menu_version,
            "offline_since": state.offline_since.isoformat() if state.offline_since else None,
        }

    def _get_next_sequence(self, venue_id: int, terminal_id: str) -> int:
        """Get next sequence number for terminal."""
        max_seq = self.db.query(func.max(OfflineQueueItem.sequence_number)).filter(
            OfflineQueueItem.venue_id == venue_id,
            OfflineQueueItem.terminal_id == terminal_id,
        ).scalar()
        return (max_seq or 0) + 1

    def _count_pending(self, venue_id: int, terminal_id: str) -> int:
        """Count pending operations for terminal."""
        return self.db.query(OfflineQueueItem).filter(
            OfflineQueueItem.venue_id == venue_id,
            OfflineQueueItem.terminal_id == terminal_id,
            OfflineQueueItem.sync_status == SyncStatus.PENDING,
        ).count()

    def _update_terminal_state(
        self,
        venue_id: int,
        terminal_id: str,
        pending_delta: int = 0,
        synced_delta: int = 0,
    ) -> None:
        """Update terminal sync state."""
        state = self.db.query(TerminalSyncState).filter(
            TerminalSyncState.venue_id == venue_id,
            TerminalSyncState.terminal_id == terminal_id,
        ).first()

        if not state:
            state = TerminalSyncState(
                venue_id=venue_id,
                terminal_id=terminal_id,
            )
            self.db.add(state)

        state.pending_items_count = max(0, state.pending_items_count + pending_delta)
        state.total_synced_operations += synced_delta

        if synced_delta > 0:
            state.last_sync_at = datetime.utcnow()

    def _create_conflict(
        self,
        item: OfflineQueueItem,
        result: Dict[str, Any],
    ) -> SyncConflict:
        """Create a sync conflict record."""
        conflict = SyncConflict(
            venue_id=item.venue_id,
            queue_item_id=item.id,
            conflict_type=result.get("conflict_type", "unknown"),
            conflict_description=result.get("conflict_description"),
            client_data=item.operation_data,
            server_data=result.get("server_data"),
        )
        self.db.add(conflict)
        return conflict
