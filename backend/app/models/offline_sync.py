"""
Offline Sync Models - Terminal Queue and Synchronization

Enables terminals to work offline and sync when connectivity is restored.
Critical for POS operations during network outages.

Key Features:
- Offline order queue with conflict resolution
- Menu version tracking
- Sync state management
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Text, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.db.base import Base


class SyncStatus(str, enum.Enum):
    """Sync operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


# OfflineQueueItem is defined in hardware.py - DO NOT define here


class TerminalMenuVersion(Base):
    """
    Track menu versions for offline terminal sync.

    Terminals cache menu and check version on sync.
    Distinct from MenuVersion (menu publishing) - this is for terminal offline caching.
    """
    __tablename__ = "terminal_menu_versions"
    __table_args__ = (
        UniqueConstraint('venue_id', 'version_number', name='uq_venue_terminal_menu_version'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)

    version_number = Column(Integer, nullable=False)
    version_hash = Column(String(64), nullable=False)  # SHA-256 of menu data

    # What changed
    changes_summary = Column(JSON, nullable=True)  # List of changes
    items_added = Column(Integer, default=0)
    items_modified = Column(Integer, default=0)
    items_removed = Column(Integer, default=0)
    categories_changed = Column(Integer, default=0)

    # Full snapshot for offline use
    menu_snapshot = Column(JSON, nullable=True)

    # Tracking
    created_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    venue = relationship("Venue", backref="terminal_menu_versions")


class TerminalSyncState(Base):
    """
    Track sync state per terminal.
    """
    __tablename__ = "terminal_sync_states"
    __table_args__ = (
        UniqueConstraint('venue_id', 'terminal_id', name='uq_venue_terminal'),
        {'extend_existing': True}
    )

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    terminal_id = Column(String(50), nullable=False, index=True)

    # Sync state
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    last_sequence_synced = Column(Integer, default=0)
    pending_items_count = Column(Integer, default=0)

    # Menu version
    current_menu_version = Column(Integer, nullable=True)
    menu_last_synced = Column(DateTime(timezone=True), nullable=True)

    # Connection state
    is_online = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    offline_since = Column(DateTime(timezone=True), nullable=True)

    # Stats
    total_synced_operations = Column(Integer, default=0)
    failed_sync_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    venue = relationship("Venue", backref="terminal_sync_states")


class SyncConflict(Base):
    """
    Record sync conflicts for manual resolution.
    """
    __tablename__ = "sync_conflicts"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    queue_item_id = Column(Integer, ForeignKey("offline_queue.id"), nullable=False)

    # Conflict details
    conflict_type = Column(String(50), nullable=False)  # version_mismatch, duplicate, etc.
    conflict_description = Column(Text, nullable=True)

    # Data comparison
    client_data = Column(JSON, nullable=False)
    server_data = Column(JSON, nullable=True)

    # Resolution
    is_resolved = Column(Boolean, default=False)
    resolution = Column(String(50), nullable=True)  # accept_client, accept_server, merge
    resolved_by = Column(Integer, ForeignKey("staff_users.id"), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    venue = relationship("Venue", backref="sync_conflicts")
    queue_item = relationship("OfflineQueueItem", backref="conflicts")
