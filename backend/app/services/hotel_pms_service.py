"""
Hotel PMS Integration Service
Integration with hotel property management systems for room charges and guest sync
Like Oracle MICROS, Lightspeed, and NCR Aloha
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session


class HotelPMSService:
    """
    Hotel Property Management System Integration
    - Connect to PMS systems (Opera, Mews, Cloudbeds, etc.)
    - Post room charges from restaurant orders
    - Sync guest information
    - Manage F&B credits from hotel packages
    """

    # Supported PMS providers
    SUPPORTED_PROVIDERS = [
        {
            "slug": "oracle_opera",
            "name": "Oracle Opera PMS",
            "description": "Industry-leading hotel PMS for major chains",
            "features": ["room_charge", "guest_sync", "reservation_sync", "package_credits"],
            "auth_type": "api_key",
            "regions": ["global"]
        },
        {
            "slug": "mews",
            "name": "Mews",
            "description": "Modern cloud-based hotel PMS",
            "features": ["room_charge", "guest_sync", "reservation_sync"],
            "auth_type": "oauth2",
            "regions": ["global"]
        },
        {
            "slug": "cloudbeds",
            "name": "Cloudbeds",
            "description": "All-in-one hospitality management",
            "features": ["room_charge", "guest_sync"],
            "auth_type": "api_key",
            "regions": ["global"]
        },
        {
            "slug": "protel",
            "name": "Protel",
            "description": "Enterprise hotel management",
            "features": ["room_charge", "guest_sync", "reservation_sync"],
            "auth_type": "api_key",
            "regions": ["EU"]
        },
        {
            "slug": "clock_pms",
            "name": "Clock PMS",
            "description": "Cloud hotel software",
            "features": ["room_charge", "guest_sync"],
            "auth_type": "api_key",
            "regions": ["global"]
        },
        {
            "slug": "stayntouch",
            "name": "StayNTouch",
            "description": "Mobile-first cloud PMS",
            "features": ["room_charge", "guest_sync", "mobile_checkin"],
            "auth_type": "api_key",
            "regions": ["global"]
        },
        {
            "slug": "apaleo",
            "name": "Apaleo",
            "description": "Open hospitality cloud",
            "features": ["room_charge", "guest_sync"],
            "auth_type": "oauth2",
            "regions": ["EU"]
        },
        {
            "slug": "guestline",
            "name": "Guestline",
            "description": "Hospitality technology",
            "features": ["room_charge", "guest_sync"],
            "auth_type": "api_key",
            "regions": ["UK", "EU"]
        },
        {
            "slug": "infor_hms",
            "name": "Infor HMS",
            "description": "Enterprise hospitality management",
            "features": ["room_charge", "guest_sync", "reservation_sync"],
            "auth_type": "api_key",
            "regions": ["global"]
        },
        {
            "slug": "roommaster",
            "name": "RoomMaster",
            "description": "Property management system",
            "features": ["room_charge", "guest_sync"],
            "auth_type": "api_key",
            "regions": ["global"]
        }
    ]

    def __init__(self, db: Session):
        self.db = db

    def get_supported_providers(self) -> List[Dict[str, Any]]:
        """Get list of supported PMS providers"""
        return self.SUPPORTED_PROVIDERS

    def connect_pms(
        self,
        venue_id: int,
        provider: str,
        api_endpoint: str,
        credentials: Dict[str, Any],
        hotel_id: str,
        hotel_name: str
    ) -> Dict[str, Any]:
        """Connect to a hotel PMS"""
        from app.models.enterprise_integrations_models import EnterpriseHotelPMSConnection as HotelPMSConnection, HotelPMSProvider

        # Validate provider
        valid_providers = [p["slug"] for p in self.SUPPORTED_PROVIDERS]
        if provider not in valid_providers:
            return {"success": False, "error": f"Unsupported provider: {provider}"}

        # Check for existing connection
        existing = self.db.query(HotelPMSConnection).filter(
            HotelPMSConnection.venue_id == venue_id
        ).first()

        if existing:
            # Update existing
            existing.provider = HotelPMSProvider(provider)
            existing.api_endpoint = api_endpoint
            existing.credentials = credentials
            existing.hotel_id = hotel_id
            existing.hotel_name = hotel_name
            existing.is_connected = True
            existing.connection_status = "connected"
            existing.last_health_check = datetime.utcnow()
            self.db.commit()

            return {
                "success": True,
                "connection_id": existing.id,
                "message": "PMS connection updated"
            }

        # Create new connection
        provider_info = next(p for p in self.SUPPORTED_PROVIDERS if p["slug"] == provider)

        connection = HotelPMSConnection(
            venue_id=venue_id,
            provider=HotelPMSProvider(provider),
            provider_name=provider_info["name"],
            api_endpoint=api_endpoint,
            credentials=credentials,
            hotel_id=hotel_id,
            hotel_name=hotel_name,
            is_connected=True,
            connection_status="connected",
            last_health_check=datetime.utcnow()
        )
        self.db.add(connection)
        self.db.commit()

        return {
            "success": True,
            "connection_id": connection.id,
            "message": f"Connected to {provider_info['name']}"
        }

    def disconnect_pms(self, venue_id: int) -> Dict[str, Any]:
        """Disconnect from hotel PMS"""
        from app.models.enterprise_integrations_models import EnterpriseHotelPMSConnection as HotelPMSConnection

        connection = self.db.query(HotelPMSConnection).filter(
            HotelPMSConnection.venue_id == venue_id
        ).first()

        if not connection:
            return {"success": False, "error": "No PMS connection found"}

        connection.is_connected = False
        connection.connection_status = "disconnected"
        connection.credentials = None
        self.db.commit()

        return {"success": True, "message": "PMS disconnected"}

    def get_connection(self, venue_id: int) -> Optional[Dict[str, Any]]:
        """Get current PMS connection details"""
        from app.models.enterprise_integrations_models import EnterpriseHotelPMSConnection as HotelPMSConnection

        connection = self.db.query(HotelPMSConnection).filter(
            HotelPMSConnection.venue_id == venue_id
        ).first()

        if not connection:
            return None

        return {
            "id": connection.id,
            "provider": connection.provider.value,
            "provider_name": connection.provider_name,
            "hotel_id": connection.hotel_id,
            "hotel_name": connection.hotel_name,
            "is_connected": connection.is_connected,
            "connection_status": connection.connection_status,
            "features": {
                "room_charge": connection.room_charge_enabled,
                "guest_sync": connection.guest_sync_enabled,
                "reservation_sync": connection.reservation_sync_enabled
            },
            "last_health_check": connection.last_health_check.isoformat() if connection.last_health_check else None,
            "last_error": connection.last_error,
            "last_error_at": connection.last_error_at.isoformat() if connection.last_error_at else None
        }

    def search_guests(
        self,
        venue_id: int,
        query: Optional[str] = None,
        room_number: Optional[str] = None,
        checked_in_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Search hotel guests"""
        from app.models.enterprise_integrations_models import EnterpriseHotelGuest as HotelGuest

        q = self.db.query(HotelGuest).filter(HotelGuest.venue_id == venue_id)

        if checked_in_only:
            q = q.filter(HotelGuest.is_checked_in == True)

        if room_number:
            q = q.filter(HotelGuest.room_number == room_number)

        if query:
            search = f"%{query}%"
            q = q.filter(
                (HotelGuest.full_name.ilike(search)) |
                (HotelGuest.room_number.ilike(search))
            )

        guests = q.limit(50).all()

        return [
            {
                "id": g.id,
                "pms_guest_id": g.pms_guest_id,
                "full_name": g.full_name,
                "room_number": g.room_number,
                "room_type": g.room_type,
                "check_in_date": g.check_in_date.isoformat() if g.check_in_date else None,
                "check_out_date": g.check_out_date.isoformat() if g.check_out_date else None,
                "is_vip": g.is_vip,
                "vip_level": g.vip_level,
                "room_charge_enabled": g.room_charge_enabled,
                "credit_limit": g.credit_limit,
                "current_balance": g.current_balance
            }
            for g in guests
        ]

    def sync_guests(self, venue_id: int) -> Dict[str, Any]:
        """Sync guests from PMS"""
        from app.models.enterprise_integrations_models import EnterpriseHotelPMSConnection as HotelPMSConnection, EnterpriseHotelGuest as HotelGuest

        connection = self.db.query(HotelPMSConnection).filter(
            HotelPMSConnection.venue_id == venue_id,
            HotelPMSConnection.is_connected == True
        ).first()

        if not connection:
            return {"success": False, "error": "No active PMS connection"}

        # In production, this would call the actual PMS API
        # Simulating guest sync
        sample_guests = self._get_sample_guests()

        synced_count = 0
        for guest_data in sample_guests:
            existing = self.db.query(HotelGuest).filter(
                HotelGuest.venue_id == venue_id,
                HotelGuest.pms_guest_id == guest_data["pms_guest_id"]
            ).first()

            if existing:
                # Update existing guest
                for key, value in guest_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                existing.last_synced_at = datetime.utcnow()
            else:
                # Create new guest
                guest = HotelGuest(
                    venue_id=venue_id,
                    pms_connection_id=connection.id,
                    **guest_data
                )
                guest.last_synced_at = datetime.utcnow()
                self.db.add(guest)

            synced_count += 1

        self.db.commit()

        return {
            "success": True,
            "synced_count": synced_count,
            "message": f"Synced {synced_count} guests"
        }

    def _get_sample_guests(self) -> List[Dict[str, Any]]:
        """Get sample guests for demo"""
        today = date.today()
        return [
            {
                "pms_guest_id": "G001",
                "pms_reservation_id": "R001",
                "first_name": "John",
                "last_name": "Smith",
                "full_name": "John Smith",
                "email": "john.smith@email.com",
                "room_number": "101",
                "room_type": "Deluxe King",
                "check_in_date": today - timedelta(days=2),
                "check_out_date": today + timedelta(days=3),
                "nights": 5,
                "is_checked_in": True,
                "is_vip": True,
                "vip_level": "Gold",
                "room_charge_enabled": True,
                "credit_limit": 500.00,
                "current_balance": 125.50
            },
            {
                "pms_guest_id": "G002",
                "pms_reservation_id": "R002",
                "first_name": "Jane",
                "last_name": "Doe",
                "full_name": "Jane Doe",
                "email": "jane.doe@email.com",
                "room_number": "205",
                "room_type": "Suite",
                "check_in_date": today - timedelta(days=1),
                "check_out_date": today + timedelta(days=2),
                "nights": 3,
                "is_checked_in": True,
                "is_vip": False,
                "room_charge_enabled": True,
                "credit_limit": 300.00,
                "current_balance": 0
            },
            {
                "pms_guest_id": "G003",
                "pms_reservation_id": "R003",
                "first_name": "Michael",
                "last_name": "Johnson",
                "full_name": "Michael Johnson",
                "email": "m.johnson@email.com",
                "room_number": "312",
                "room_type": "Standard Queen",
                "check_in_date": today,
                "check_out_date": today + timedelta(days=1),
                "nights": 1,
                "is_checked_in": True,
                "is_vip": False,
                "room_charge_enabled": True,
                "credit_limit": 200.00,
                "current_balance": 0
            }
        ]

    def post_room_charge(
        self,
        venue_id: int,
        order_id: int,
        guest_id: int,
        amount: float,
        description: str,
        posted_by: int
    ) -> Dict[str, Any]:
        """Post a charge to a guest's room folio"""
        from app.models.enterprise_integrations_models import (
            EnterpriseHotelPMSConnection as HotelPMSConnection,
            EnterpriseHotelGuest as HotelGuest,
            EnterpriseRoomCharge as RoomCharge,
            RoomChargeStatus
        )

        # Verify connection
        connection = self.db.query(HotelPMSConnection).filter(
            HotelPMSConnection.venue_id == venue_id,
            HotelPMSConnection.is_connected == True,
            HotelPMSConnection.room_charge_enabled == True
        ).first()

        if not connection:
            return {"success": False, "error": "Room charge not enabled"}

        # Get guest
        guest = self.db.query(HotelGuest).filter(
            HotelGuest.id == guest_id,
            HotelGuest.venue_id == venue_id
        ).first()

        if not guest:
            return {"success": False, "error": "Guest not found"}

        if not guest.room_charge_enabled:
            return {"success": False, "error": "Room charge not enabled for this guest"}

        if not guest.is_checked_in:
            return {"success": False, "error": "Guest is not checked in"}

        # Check credit limit
        if guest.credit_limit and (guest.current_balance + amount) > guest.credit_limit:
            return {
                "success": False,
                "error": "Charge exceeds credit limit",
                "current_balance": guest.current_balance,
                "credit_limit": guest.credit_limit,
                "requested_amount": amount
            }

        # Create room charge record
        charge = RoomCharge(
            venue_id=venue_id,
            pms_connection_id=connection.id,
            hotel_guest_id=guest_id,
            order_id=order_id,
            room_number=guest.room_number,
            guest_name=guest.full_name,
            charge_type="food",
            description=description,
            amount=amount,
            tax_amount=amount * 0.1,  # 10% tax
            total_amount=amount * 1.1,
            charge_date=datetime.utcnow(),
            status=RoomChargeStatus.PENDING,
            posted_by=posted_by
        )
        self.db.add(charge)
        self.db.flush()

        # In production, post to actual PMS API
        # Simulate successful posting
        charge.status = RoomChargeStatus.POSTED
        charge.posted_at = datetime.utcnow()
        charge.pms_posting_id = f"POST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Update guest balance
        guest.current_balance = (guest.current_balance or 0) + charge.total_amount

        self.db.commit()

        return {
            "success": True,
            "charge_id": charge.id,
            "pms_posting_id": charge.pms_posting_id,
            "room_number": guest.room_number,
            "guest_name": guest.full_name,
            "amount": charge.total_amount,
            "new_balance": guest.current_balance,
            "message": f"Room charge posted to room {guest.room_number}"
        }

    def void_room_charge(
        self,
        venue_id: int,
        charge_id: int,
        reason: str,
        voided_by: int
    ) -> Dict[str, Any]:
        """Void a room charge"""
        from app.models.enterprise_integrations_models import EnterpriseRoomCharge as RoomCharge, RoomChargeStatus, EnterpriseHotelGuest as HotelGuest

        charge = self.db.query(RoomCharge).filter(
            RoomCharge.id == charge_id,
            RoomCharge.venue_id == venue_id
        ).first()

        if not charge:
            return {"success": False, "error": "Charge not found"}

        if charge.status != RoomChargeStatus.POSTED:
            return {"success": False, "error": f"Cannot void charge with status: {charge.status.value}"}

        # Update charge status
        charge.status = RoomChargeStatus.VOID
        charge.rejection_reason = reason

        # Update guest balance
        guest = self.db.query(HotelGuest).filter(
            HotelGuest.id == charge.hotel_guest_id
        ).first()

        if guest:
            guest.current_balance = max(0, (guest.current_balance or 0) - charge.total_amount)

        self.db.commit()

        return {
            "success": True,
            "message": "Room charge voided",
            "charge_id": charge_id
        }

    def get_room_charges(
        self,
        venue_id: int,
        guest_id: Optional[int] = None,
        order_id: Optional[int] = None,
        status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get room charges"""
        from app.models.enterprise_integrations_models import EnterpriseRoomCharge as RoomCharge, RoomChargeStatus

        q = self.db.query(RoomCharge).filter(RoomCharge.venue_id == venue_id)

        if guest_id:
            q = q.filter(RoomCharge.hotel_guest_id == guest_id)

        if order_id:
            q = q.filter(RoomCharge.order_id == order_id)

        if status:
            q = q.filter(RoomCharge.status == RoomChargeStatus(status))

        if date_from:
            q = q.filter(RoomCharge.charge_date >= date_from)

        if date_to:
            q = q.filter(RoomCharge.charge_date <= date_to)

        charges = q.order_by(RoomCharge.charge_date.desc()).limit(limit).all()

        return [
            {
                "id": c.id,
                "order_id": c.order_id,
                "pms_posting_id": c.pms_posting_id,
                "room_number": c.room_number,
                "guest_name": c.guest_name,
                "charge_type": c.charge_type,
                "description": c.description,
                "amount": c.amount,
                "tax_amount": c.tax_amount,
                "total_amount": c.total_amount,
                "status": c.status.value,
                "charge_date": c.charge_date.isoformat(),
                "posted_at": c.posted_at.isoformat() if c.posted_at else None
            }
            for c in charges
        ]

    def create_fb_credit(
        self,
        venue_id: int,
        guest_id: int,
        amount: float,
        credit_type: str = "complimentary",
        valid_days: int = 7
    ) -> Dict[str, Any]:
        """Create F&B credit for a guest"""
        from app.models.enterprise_integrations_models import EnterpriseGuestFBCredit as GuestFBCredit, EnterpriseHotelGuest as HotelGuest

        guest = self.db.query(HotelGuest).filter(
            HotelGuest.id == guest_id,
            HotelGuest.venue_id == venue_id
        ).first()

        if not guest:
            return {"success": False, "error": "Guest not found"}

        credit = GuestFBCredit(
            venue_id=venue_id,
            hotel_guest_id=guest_id,
            credit_type=credit_type,
            original_amount=amount,
            remaining_amount=amount,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=valid_days)
        )
        self.db.add(credit)
        self.db.commit()

        return {
            "success": True,
            "credit_id": credit.id,
            "amount": amount,
            "valid_until": credit.valid_until.isoformat(),
            "message": f"F&B credit of ${amount} added for {guest.full_name}"
        }

    def get_guest_credits(self, venue_id: int, guest_id: int) -> List[Dict[str, Any]]:
        """Get F&B credits for a guest"""
        from app.models.enterprise_integrations_models import EnterpriseGuestFBCredit as GuestFBCredit

        credits = self.db.query(GuestFBCredit).filter(
            GuestFBCredit.venue_id == venue_id,
            GuestFBCredit.hotel_guest_id == guest_id,
            GuestFBCredit.is_active == True,
            GuestFBCredit.is_expired == False
        ).all()

        return [
            {
                "id": c.id,
                "credit_type": c.credit_type,
                "original_amount": c.original_amount,
                "remaining_amount": c.remaining_amount,
                "valid_from": c.valid_from.isoformat() if c.valid_from else None,
                "valid_until": c.valid_until.isoformat() if c.valid_until else None,
                "times_used": c.times_used,
                "total_used": c.total_used
            }
            for c in credits
        ]

    def apply_fb_credit(
        self,
        venue_id: int,
        guest_id: int,
        credit_id: int,
        amount: float
    ) -> Dict[str, Any]:
        """Apply F&B credit to an order"""
        from app.models.enterprise_integrations_models import EnterpriseGuestFBCredit as GuestFBCredit

        credit = self.db.query(GuestFBCredit).filter(
            GuestFBCredit.id == credit_id,
            GuestFBCredit.venue_id == venue_id,
            GuestFBCredit.hotel_guest_id == guest_id,
            GuestFBCredit.is_active == True
        ).first()

        if not credit:
            return {"success": False, "error": "Credit not found or not active"}

        if credit.remaining_amount < amount:
            return {
                "success": False,
                "error": "Insufficient credit balance",
                "remaining": credit.remaining_amount,
                "requested": amount
            }

        # Check validity
        today = date.today()
        if credit.valid_until and today > credit.valid_until:
            credit.is_expired = True
            self.db.commit()
            return {"success": False, "error": "Credit has expired"}

        # Apply credit
        credit.remaining_amount -= amount
        credit.total_used += amount
        credit.times_used += 1

        if credit.remaining_amount <= 0:
            credit.is_active = False

        self.db.commit()

        return {
            "success": True,
            "applied_amount": amount,
            "remaining_balance": credit.remaining_amount,
            "message": f"Applied ${amount} credit"
        }

    def get_pms_stats(self, venue_id: int) -> Dict[str, Any]:
        """Get PMS integration statistics"""
        from app.models.enterprise_integrations_models import (
            EnterpriseHotelPMSConnection as HotelPMSConnection,
            EnterpriseHotelGuest as HotelGuest,
            EnterpriseRoomCharge as RoomCharge,
            RoomChargeStatus
        )

        connection = self.db.query(HotelPMSConnection).filter(
            HotelPMSConnection.venue_id == venue_id
        ).first()

        if not connection:
            return {"connected": False}

        # Guest stats
        total_guests = self.db.query(HotelGuest).filter(
            HotelGuest.venue_id == venue_id
        ).count()

        checked_in = self.db.query(HotelGuest).filter(
            HotelGuest.venue_id == venue_id,
            HotelGuest.is_checked_in == True
        ).count()

        vip_guests = self.db.query(HotelGuest).filter(
            HotelGuest.venue_id == venue_id,
            HotelGuest.is_checked_in == True,
            HotelGuest.is_vip == True
        ).count()

        # Room charge stats
        total_charges = self.db.query(RoomCharge).filter(
            RoomCharge.venue_id == venue_id
        ).count()

        posted_charges = self.db.query(RoomCharge).filter(
            RoomCharge.venue_id == venue_id,
            RoomCharge.status == RoomChargeStatus.POSTED
        ).count()

        charges = self.db.query(RoomCharge).filter(
            RoomCharge.venue_id == venue_id,
            RoomCharge.status == RoomChargeStatus.POSTED
        ).all()

        total_charged_amount = sum(c.total_amount for c in charges)

        return {
            "connected": connection.is_connected,
            "provider": connection.provider_name,
            "hotel_name": connection.hotel_name,
            "guests": {
                "total": total_guests,
                "checked_in": checked_in,
                "vip": vip_guests
            },
            "room_charges": {
                "total": total_charges,
                "posted": posted_charges,
                "total_amount": round(total_charged_amount, 2)
            },
            "last_sync": connection.last_health_check.isoformat() if connection.last_health_check else None
        }

    def health_check(self, venue_id: int) -> Dict[str, Any]:
        """Check PMS connection health"""
        from app.models.enterprise_integrations_models import EnterpriseHotelPMSConnection as HotelPMSConnection

        connection = self.db.query(HotelPMSConnection).filter(
            HotelPMSConnection.venue_id == venue_id
        ).first()

        if not connection:
            return {"healthy": False, "error": "No connection configured"}

        # In production, this would ping the actual PMS API
        # Simulate health check
        connection.last_health_check = datetime.utcnow()
        connection.connection_status = "healthy"
        self.db.commit()

        return {
            "healthy": True,
            "provider": connection.provider_name,
            "hotel": connection.hotel_name,
            "last_check": connection.last_health_check.isoformat()
        }
