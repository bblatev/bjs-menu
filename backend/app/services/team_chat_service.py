"""
Team Chat & Communication Service
Implements team messaging, announcements, and shift-based chat
Competitor: Toast Team Communication, 7shifts Messaging, Homebase Chat
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.orm import Session

from app.models.gap_features_models import (
    ChatChannel, ChatMessage, MessageAcknowledgment, TeamAnnouncement
)


class TeamChatService:
    """
    Service for team messaging and communication.
    Supports channels, direct messages, and announcements.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== CHANNEL MANAGEMENT ====================

    async def create_channel(
        self,
        venue_id: UUID,
        name: str,
        channel_type: str = "public",  # 'public', 'private', 'shift', 'direct'
        description: Optional[str] = None,
        created_by: Optional[UUID] = None,
        members: Optional[List[UUID]] = None
    ) -> ChatChannel:
        """Create a new chat channel."""
        channel = ChatChannel(
            id=uuid4(),
            venue_id=venue_id,
            name=name,
            channel_type=channel_type,
            description=description,
            created_by=created_by,
            members=members or [],
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(channel)
        self.db.commit()
        self.db.refresh(channel)
        return channel

    async def create_shift_channel(
        self,
        venue_id: UUID,
        shift_date: datetime,
        shift_name: str
    ) -> ChatChannel:
        """Create a channel for a specific shift."""
        channel_name = f"shift-{shift_date.strftime('%Y%m%d')}-{shift_name.lower().replace(' ', '-')}"

        # Check if channel already exists
        result = self.db.execute(
            select(ChatChannel).where(
                and_(
                    ChatChannel.venue_id == venue_id,
                    ChatChannel.name == channel_name
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        return await self.create_channel(
            venue_id=venue_id,
            name=channel_name,
            channel_type="shift",
            description=f"Chat for {shift_name} shift on {shift_date.strftime('%Y-%m-%d')}"
        )

    async def create_direct_message_channel(
        self,
        venue_id: UUID,
        user1_id: UUID,
        user2_id: UUID
    ) -> ChatChannel:
        """Create or get a direct message channel between two users."""
        # Sort IDs to create consistent channel name
        sorted_ids = sorted([str(user1_id), str(user2_id)])
        channel_name = f"dm-{sorted_ids[0][:8]}-{sorted_ids[1][:8]}"

        # Check if channel already exists
        result = self.db.execute(
            select(ChatChannel).where(
                and_(
                    ChatChannel.venue_id == venue_id,
                    ChatChannel.name == channel_name
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        return await self.create_channel(
            venue_id=venue_id,
            name=channel_name,
            channel_type="direct",
            members=[user1_id, user2_id]
        )

    async def get_channel(self, channel_id: UUID) -> Optional[ChatChannel]:
        """Get a channel by ID."""
        result = self.db.execute(
            select(ChatChannel).where(ChatChannel.id == channel_id)
        )
        return result.scalar_one_or_none()

    async def get_user_channels(
        self,
        venue_id: UUID,
        user_id: UUID
    ) -> List[ChatChannel]:
        """Get all channels a user has access to."""
        # Get public channels and channels user is a member of
        result = self.db.execute(
            select(ChatChannel).where(
                and_(
                    ChatChannel.venue_id == venue_id,
                    ChatChannel.is_active == True,
                    or_(
                        ChatChannel.channel_type == "public",
                        ChatChannel.members.contains([user_id])
                    )
                )
            ).order_by(ChatChannel.name)
        )
        return list(result.scalars().all())

    async def add_member_to_channel(
        self,
        channel_id: UUID,
        user_id: UUID
    ) -> bool:
        """Add a member to a channel."""
        channel = await self.get_channel(channel_id)
        if not channel:
            return False

        if user_id not in channel.members:
            channel.members = channel.members + [user_id]
            self.db.commit()
        return True

    async def remove_member_from_channel(
        self,
        channel_id: UUID,
        user_id: UUID
    ) -> bool:
        """Remove a member from a channel."""
        channel = await self.get_channel(channel_id)
        if not channel:
            return False

        if user_id in channel.members:
            channel.members = [m for m in channel.members if m != user_id]
            self.db.commit()
        return True

    # ==================== MESSAGING ====================

    async def send_message(
        self,
        channel_id: UUID,
        sender_id: UUID,
        content: str,
        message_type: str = "text",
        attachments: Optional[List[Dict[str, Any]]] = None,
        reply_to_id: Optional[UUID] = None,
        mentions: Optional[List[UUID]] = None
    ) -> ChatMessage:
        """Send a message to a channel."""
        try:
            message = ChatMessage(
                id=uuid4(),
                channel_id=channel_id,
                sender_id=sender_id,
                content=content,
                message_type=message_type,
                attachments=attachments or [],
                reply_to_id=reply_to_id,
                mentions=mentions or [],
                is_edited=False,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(message)

            # Update channel's last message timestamp
            channel = await self.get_channel(channel_id)
            if channel:
                channel.last_message_at = datetime.now(timezone.utc)

            self.db.commit()
            self.db.refresh(message)
            return message
        except Exception:
            self.db.rollback()
            raise

    async def edit_message(
        self,
        message_id: UUID,
        sender_id: UUID,
        new_content: str
    ) -> Optional[ChatMessage]:
        """Edit a message (only by sender)."""
        result = self.db.execute(
            select(ChatMessage).where(
                and_(
                    ChatMessage.id == message_id,
                    ChatMessage.sender_id == sender_id
                )
            )
        )
        message = result.scalar_one_or_none()

        if not message:
            return None

        message.content = new_content
        message.is_edited = True
        message.edited_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(message)
        return message

    async def delete_message(
        self,
        message_id: UUID,
        user_id: UUID,
        is_admin: bool = False
    ) -> bool:
        """Delete a message."""
        query = select(ChatMessage).where(ChatMessage.id == message_id)

        if not is_admin:
            query = query.where(ChatMessage.sender_id == user_id)

        result = self.db.execute(query)
        message = result.scalar_one_or_none()

        if message:
            message.is_deleted = True
            message.deleted_at = datetime.now(timezone.utc)
            self.db.commit()
            return True
        return False

    async def get_channel_messages(
        self,
        channel_id: UUID,
        limit: int = 50,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None
    ) -> List[ChatMessage]:
        """Get messages from a channel with pagination."""
        query = select(ChatMessage).where(
            and_(
                ChatMessage.channel_id == channel_id,
                ChatMessage.is_deleted == False
            )
        )

        if before:
            query = query.where(ChatMessage.created_at < before)
        if after:
            query = query.where(ChatMessage.created_at > after)

        query = query.order_by(desc(ChatMessage.created_at)).limit(limit)

        result = self.db.execute(query)
        messages = list(result.scalars().all())

        # Return in chronological order
        return list(reversed(messages))

    async def search_messages(
        self,
        venue_id: UUID,
        query: str,
        user_id: Optional[UUID] = None,
        channel_id: Optional[UUID] = None,
        limit: int = 20
    ) -> List[ChatMessage]:
        """Search messages across channels."""
        search_query = select(ChatMessage).join(
            ChatChannel, ChatMessage.channel_id == ChatChannel.id
        ).where(
            and_(
                ChatChannel.venue_id == venue_id,
                ChatMessage.is_deleted == False,
                ChatMessage.content.ilike(f"%{query}%")
            )
        )

        if channel_id:
            search_query = search_query.where(ChatMessage.channel_id == channel_id)

        search_query = search_query.order_by(desc(ChatMessage.created_at)).limit(limit)

        result = self.db.execute(search_query)
        return list(result.scalars().all())

    # ==================== READ RECEIPTS ====================

    async def mark_message_read(
        self,
        message_id: UUID,
        user_id: UUID
    ) -> MessageAcknowledgment:
        """Mark a message as read."""
        # Check if already acknowledged
        result = self.db.execute(
            select(MessageAcknowledgment).where(
                and_(
                    MessageAcknowledgment.message_id == message_id,
                    MessageAcknowledgment.user_id == user_id
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing

        ack = MessageAcknowledgment(
            id=uuid4(),
            message_id=message_id,
            user_id=user_id,
            read_at=datetime.now(timezone.utc)
        )
        self.db.add(ack)
        self.db.commit()
        self.db.refresh(ack)
        return ack

    async def mark_channel_read(
        self,
        channel_id: UUID,
        user_id: UUID
    ) -> int:
        """Mark all messages in a channel as read."""
        try:
            # Get unread message IDs
            result = self.db.execute(
                select(ChatMessage.id).where(
                    ChatMessage.channel_id == channel_id
                ).except_(
                    select(MessageAcknowledgment.message_id).where(
                        MessageAcknowledgment.user_id == user_id
                    )
                )
            )
            unread_ids = [r[0] for r in result.all()]

            now = datetime.now(timezone.utc)
            for message_id in unread_ids:
                ack = MessageAcknowledgment(
                    id=uuid4(),
                    message_id=message_id,
                    user_id=user_id,
                    read_at=now
                )
                self.db.add(ack)

            self.db.commit()
            return len(unread_ids)
        except Exception:
            self.db.rollback()
            raise

    async def get_unread_count(
        self,
        channel_id: UUID,
        user_id: UUID
    ) -> int:
        """Get unread message count for a channel."""
        result = self.db.execute(
            select(func.count(ChatMessage.id)).where(
                and_(
                    ChatMessage.channel_id == channel_id,
                    ChatMessage.is_deleted == False
                )
            ).except_(
                select(func.count(MessageAcknowledgment.message_id)).where(
                    MessageAcknowledgment.user_id == user_id
                )
            )
        )
        return result.scalar() or 0

    # ==================== ANNOUNCEMENTS ====================

    async def create_announcement(
        self,
        venue_id: UUID,
        title: str,
        content: str,
        created_by: UUID,
        priority: str = "normal",  # 'low', 'normal', 'high', 'urgent'
        target_roles: Optional[List[str]] = None,
        target_staff_ids: Optional[List[UUID]] = None,
        expires_at: Optional[datetime] = None,
        require_acknowledgment: bool = False
    ) -> TeamAnnouncement:
        """Create a team announcement."""
        try:
            announcement = TeamAnnouncement(
                id=uuid4(),
                venue_id=venue_id,
                title=title,
                content=content,
                created_by=created_by,
                priority=priority,
                target_roles=target_roles or [],
                target_staff_ids=target_staff_ids or [],
                expires_at=expires_at,
                require_acknowledgment=require_acknowledgment,
                acknowledgments=[],
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(announcement)
            self.db.commit()
            self.db.refresh(announcement)
            return announcement
        except Exception:
            self.db.rollback()
            raise

    async def acknowledge_announcement(
        self,
        announcement_id: UUID,
        user_id: UUID
    ) -> bool:
        """Acknowledge an announcement."""
        result = self.db.execute(
            select(TeamAnnouncement).where(TeamAnnouncement.id == announcement_id)
        )
        announcement = result.scalar_one_or_none()

        if not announcement:
            return False

        if user_id not in announcement.acknowledgments:
            announcement.acknowledgments = announcement.acknowledgments + [
                {"user_id": str(user_id), "acknowledged_at": datetime.now(timezone.utc).isoformat()}
            ]
            self.db.commit()
        return True

    async def get_active_announcements(
        self,
        venue_id: UUID,
        user_id: Optional[UUID] = None,
        role: Optional[str] = None
    ) -> List[TeamAnnouncement]:
        """Get active announcements for a venue/user."""
        now = datetime.now(timezone.utc)

        query = select(TeamAnnouncement).where(
            and_(
                TeamAnnouncement.venue_id == venue_id,
                TeamAnnouncement.is_active == True,
                or_(
                    TeamAnnouncement.expires_at.is_(None),
                    TeamAnnouncement.expires_at > now
                )
            )
        )

        # Filter by target if user_id provided
        if user_id and role:
            query = query.where(
                or_(
                    TeamAnnouncement.target_roles == [],  # No role filter means all
                    TeamAnnouncement.target_roles.contains([role]),
                    TeamAnnouncement.target_staff_ids.contains([user_id])
                )
            )

        query = query.order_by(
            desc(TeamAnnouncement.priority == 'urgent'),
            desc(TeamAnnouncement.priority == 'high'),
            desc(TeamAnnouncement.created_at)
        )

        result = self.db.execute(query)
        return list(result.scalars().all())

    async def delete_announcement(
        self,
        announcement_id: UUID
    ) -> bool:
        """Soft delete an announcement."""
        result = self.db.execute(
            select(TeamAnnouncement).where(TeamAnnouncement.id == announcement_id)
        )
        announcement = result.scalar_one_or_none()

        if announcement:
            announcement.is_active = False
            self.db.commit()
            return True
        return False


class LaborComplianceService:
    """
    Service for labor law compliance monitoring.
    Tracks breaks, overtime, minor labor laws, etc.
    """

    def __init__(self, db: Session):
        self.db = db

    async def create_compliance_rule(
        self,
        venue_id: UUID,
        rule_type: str,  # 'break', 'overtime', 'minor', 'scheduling', 'split_shift'
        name: str,
        description: str,
        conditions: Dict[str, Any],
        action: str,  # 'warn', 'block', 'notify'
        is_active: bool = True
    ) -> Dict[str, Any]:
        """Create a labor compliance rule."""
        from app.models.gap_features_models import LaborComplianceRule

        rule = LaborComplianceRule(
            id=uuid4(),
            venue_id=venue_id,
            rule_type=rule_type,
            name=name,
            description=description,
            conditions=conditions,
            action=action,
            is_active=is_active,
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(rule)
        self.db.commit()

        return {
            "id": str(rule.id),
            "rule_type": rule_type,
            "name": name,
            "conditions": conditions,
            "action": action
        }

    async def check_shift_compliance(
        self,
        venue_id: UUID,
        staff_id: UUID,
        shift_start: datetime,
        shift_end: datetime
    ) -> List[Dict[str, Any]]:
        """Check if a shift complies with labor rules."""
        from app.models.gap_features_models import LaborComplianceRule

        # Get all active rules for venue
        result = self.db.execute(
            select(LaborComplianceRule).where(
                and_(
                    LaborComplianceRule.venue_id == venue_id,
                    LaborComplianceRule.is_active == True
                )
            )
        )
        rules = result.scalars().all()

        violations = []
        shift_hours = (shift_end - shift_start).total_seconds() / 3600

        for rule in rules:
            violation = await self._check_rule(
                rule,
                staff_id,
                shift_start,
                shift_end,
                shift_hours
            )
            if violation:
                violations.append(violation)

        return violations

    async def _check_rule(
        self,
        rule,
        staff_id: UUID,
        shift_start: datetime,
        shift_end: datetime,
        shift_hours: float
    ) -> Optional[Dict[str, Any]]:
        """Check a single compliance rule."""
        conditions = rule.conditions

        if rule.rule_type == "overtime":
            # Check daily overtime
            max_hours = conditions.get("max_daily_hours", 8)
            if shift_hours > max_hours:
                return {
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "violation_type": "daily_overtime",
                    "message": f"Shift exceeds {max_hours} hours ({shift_hours:.1f}h scheduled)",
                    "action": rule.action,
                    "severity": "high" if shift_hours > max_hours + 2 else "medium"
                }

            # Check weekly overtime
            max_weekly = conditions.get("max_weekly_hours", 40)
            week_start = shift_start - timedelta(days=shift_start.weekday())
            weekly_hours = await self._get_weekly_hours(staff_id, week_start)
            if weekly_hours + shift_hours > max_weekly:
                return {
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "violation_type": "weekly_overtime",
                    "message": f"Week will exceed {max_weekly}h ({weekly_hours + shift_hours:.1f}h total)",
                    "action": rule.action,
                    "severity": "medium"
                }

        elif rule.rule_type == "break":
            # Check required breaks
            min_hours_for_break = conditions.get("min_hours_for_break", 6)
            break_duration = conditions.get("break_duration_minutes", 30)

            if shift_hours >= min_hours_for_break:
                return {
                    "rule_id": str(rule.id),
                    "rule_name": rule.name,
                    "violation_type": "break_required",
                    "message": f"Shift of {shift_hours:.1f}h requires {break_duration}min break",
                    "action": "notify",
                    "severity": "low"
                }

        elif rule.rule_type == "minor":
            # Check minor labor restrictions
            staff = await self._get_staff(staff_id)
            if staff and staff.get("is_minor"):
                max_hours = conditions.get("max_hours_for_minors", 4)
                curfew_hour = conditions.get("curfew_hour", 22)

                if shift_hours > max_hours:
                    return {
                        "rule_id": str(rule.id),
                        "rule_name": rule.name,
                        "violation_type": "minor_hours",
                        "message": f"Minor cannot work more than {max_hours}h",
                        "action": rule.action,
                        "severity": "high"
                    }

                if shift_end.hour >= curfew_hour:
                    return {
                        "rule_id": str(rule.id),
                        "rule_name": rule.name,
                        "violation_type": "minor_curfew",
                        "message": f"Minor cannot work after {curfew_hour}:00",
                        "action": rule.action,
                        "severity": "high"
                    }

        elif rule.rule_type == "split_shift":
            # Check split shift premium requirements
            min_gap = conditions.get("min_gap_hours", 2)
            premium_required = conditions.get("premium_required", True)
            # This would check if there's another shift same day with a gap

        return None

    async def _get_weekly_hours(
        self,
        staff_id: UUID,
        week_start: datetime
    ) -> float:
        """Get total hours worked in a week."""
        from app.models.shifts import Shift

        week_end = week_start + timedelta(days=7)

        result = self.db.execute(
            select(Shift).where(
                and_(
                    Shift.staff_id == staff_id,
                    Shift.start_time >= week_start,
                    Shift.start_time < week_end
                )
            )
        )
        shifts = result.scalars().all()

        total_hours = sum(
            (s.end_time - s.start_time).total_seconds() / 3600
            for s in shifts
            if s.end_time
        )
        return total_hours

    async def _get_staff(self, staff_id: UUID) -> Optional[Dict[str, Any]]:
        """Get staff info for compliance checking."""
        from app.models import StaffUser as Staff

        result = self.db.execute(
            select(Staff).where(Staff.id == staff_id)
        )
        staff = result.scalar_one_or_none()

        if not staff:
            return None

        return {
            "id": str(staff.id),
            "name": staff.name,
            "is_minor": getattr(staff, 'is_minor', False),
            "role": staff.role
        }

    async def record_violation(
        self,
        venue_id: UUID,
        rule_id: UUID,
        staff_id: UUID,
        violation_type: str,
        details: Dict[str, Any],
        shift_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Record a labor compliance violation."""
        from app.models.gap_features_models import LaborComplianceViolation

        violation = LaborComplianceViolation(
            id=uuid4(),
            venue_id=venue_id,
            rule_id=rule_id,
            staff_id=staff_id,
            shift_id=shift_id,
            violation_type=violation_type,
            details=details,
            status="open",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(violation)
        self.db.commit()

        return {
            "id": str(violation.id),
            "violation_type": violation_type,
            "details": details,
            "status": "open"
        }

    async def get_violations(
        self,
        venue_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get labor compliance violations."""
        from app.models.gap_features_models import LaborComplianceViolation

        query = select(LaborComplianceViolation).where(
            LaborComplianceViolation.venue_id == venue_id
        )

        if start_date:
            query = query.where(LaborComplianceViolation.created_at >= start_date)
        if end_date:
            query = query.where(LaborComplianceViolation.created_at <= end_date)
        if status:
            query = query.where(LaborComplianceViolation.status == status)

        query = query.order_by(desc(LaborComplianceViolation.created_at))

        result = self.db.execute(query)
        violations = result.scalars().all()

        return [
            {
                "id": str(v.id),
                "rule_id": str(v.rule_id),
                "staff_id": str(v.staff_id),
                "violation_type": v.violation_type,
                "details": v.details,
                "status": v.status,
                "created_at": v.created_at.isoformat()
            }
            for v in violations
        ]
