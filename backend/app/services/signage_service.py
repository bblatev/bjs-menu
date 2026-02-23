"""Digital signage management service."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session


class SignageService:
    """Manages digital display content and scheduling."""

    @staticmethod
    def get_displays(db: Session, venue_id: int):
        """Get all digital displays for a venue."""
        from app.models.v99_models import DigitalDisplay

        displays = db.query(DigitalDisplay).filter(
            DigitalDisplay.venue_id == venue_id
        ).all()

        return [
            {
                "id": d.id,
                "name": d.name,
                "location": d.location,
                "display_type": d.display_type,
                "resolution": d.resolution,
                "orientation": d.orientation,
                "is_online": d.is_online,
                "last_heartbeat": str(d.last_heartbeat) if d.last_heartbeat else None,
                "current_content_id": d.current_content_id,
            }
            for d in displays
        ]

    @staticmethod
    def create_display(db: Session, venue_id: int, data: dict):
        """Register a new digital display."""
        from app.models.v99_models import DigitalDisplay

        display = DigitalDisplay(
            venue_id=venue_id,
            name=data["name"],
            location=data.get("location"),
            display_type=data.get("display_type", "menu_board"),
            resolution=data.get("resolution", "1920x1080"),
            orientation=data.get("orientation", "landscape"),
        )
        db.add(display)
        db.commit()
        db.refresh(display)
        return {"id": display.id, "name": display.name, "status": "created"}

    @staticmethod
    def get_content_templates(db: Session, venue_id: int):
        """Get available content templates."""
        from app.models.v99_models import SignageContent

        templates = db.query(SignageContent).filter(
            SignageContent.venue_id == venue_id,
            SignageContent.is_active == True,
        ).all()

        return [
            {
                "id": t.id,
                "name": t.name,
                "content_type": t.content_type,
                "template": t.template,
                "duration_seconds": t.duration_seconds,
                "schedule_start": str(t.schedule_start) if t.schedule_start else None,
                "schedule_end": str(t.schedule_end) if t.schedule_end else None,
            }
            for t in templates
        ]

    @staticmethod
    def create_content(db: Session, venue_id: int, data: dict):
        """Create a new content item."""
        from app.models.v99_models import SignageContent

        content = SignageContent(
            venue_id=venue_id,
            name=data["name"],
            content_type=data["content_type"],
            template=data.get("template"),
            data=data.get("data", {}),
            duration_seconds=data.get("duration_seconds", 30),
            schedule_start=data.get("schedule_start"),
            schedule_end=data.get("schedule_end"),
        )
        db.add(content)
        db.commit()
        db.refresh(content)
        return {"id": content.id, "name": content.name, "status": "created"}

    @staticmethod
    def assign_content(db: Session, display_id: int, content_id: int):
        """Assign content to a display."""
        from app.models.v99_models import DigitalDisplay

        display = db.query(DigitalDisplay).filter(DigitalDisplay.id == display_id).first()
        if not display:
            return None

        display.current_content_id = content_id
        db.commit()
        return {"display_id": display_id, "content_id": content_id, "status": "assigned"}

    @staticmethod
    def heartbeat(db: Session, display_id: int):
        """Record display heartbeat (online check)."""
        from app.models.v99_models import DigitalDisplay

        display = db.query(DigitalDisplay).filter(DigitalDisplay.id == display_id).first()
        if not display:
            return None

        display.is_online = True
        display.last_heartbeat = datetime.now(timezone.utc)
        db.commit()
        return {"display_id": display_id, "is_online": True}
