"""
Hardware SDK Service
Implements terminal SDK, payment device management, and hardware integration
Competitor: Toast Terminal SDK, Square Terminal API, Clover SDK
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import Session


class HardwareDevice:
    """Hardware device types and configurations."""

    DEVICE_TYPES = {
        "payment_terminal": {
            "name": "Payment Terminal",
            "capabilities": ["card_present", "contactless", "chip", "swipe", "pin_entry"],
            "protocols": ["iso8583", "nexo", "custom"]
        },
        "receipt_printer": {
            "name": "Receipt Printer",
            "capabilities": ["thermal", "impact", "cut", "logo", "barcode", "qr_code"],
            "protocols": ["escpos", "star", "epson"]
        },
        "cash_drawer": {
            "name": "Cash Drawer",
            "capabilities": ["auto_open", "sensor", "bell"],
            "protocols": ["printer_driven", "serial", "usb"]
        },
        "barcode_scanner": {
            "name": "Barcode Scanner",
            "capabilities": ["1d", "2d", "qr", "continuous"],
            "protocols": ["hid", "serial", "bluetooth"]
        },
        "scale": {
            "name": "Scale",
            "capabilities": ["weight", "tare", "price_computing"],
            "protocols": ["serial", "usb"]
        },
        "kds_display": {
            "name": "Kitchen Display",
            "capabilities": ["touch", "bump_bar", "audio_alert"],
            "protocols": ["network", "hdmi"]
        },
        "customer_display": {
            "name": "Customer Display",
            "capabilities": ["line_display", "full_screen", "touch"],
            "protocols": ["serial", "usb", "network"]
        },
        "label_printer": {
            "name": "Label Printer",
            "capabilities": ["thermal", "barcode", "qr", "logo"],
            "protocols": ["zpl", "epl", "escpos"]
        },
        "kiosk": {
            "name": "Self-Service Kiosk",
            "capabilities": ["touch", "card_reader", "receipt_printer", "scanner"],
            "protocols": ["network", "usb"]
        },
        "handheld_terminal": {
            "name": "Handheld POS Terminal",
            "capabilities": ["touch", "scanner", "card_reader", "printer", "wifi", "4g"],
            "protocols": ["android", "proprietary"]
        }
    }


class HardwareSDKService:
    """
    Service for hardware device management and SDK integration.
    Provides unified API for all supported hardware devices.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== DEVICE REGISTRATION ====================

    async def register_device(
        self,
        venue_id: UUID,
        station_id: Optional[UUID],
        device_type: str,
        serial_number: str,
        manufacturer: str,
        model: str,
        firmware_version: Optional[str] = None,
        connection_type: str = "usb",
        connection_params: Optional[Dict[str, Any]] = None,
        capabilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Register a new hardware device."""
        from app.models.gap_features_models import SDKHardwareDevice as HardwareDeviceModel

        # Generate device token for authentication
        device_token = secrets.token_urlsafe(32)
        device_token_hash = hashlib.sha256(device_token.encode()).hexdigest()

        device = HardwareDeviceModel(
            id=uuid4(),
            venue_id=venue_id,
            station_id=station_id,
            device_type=device_type,
            serial_number=serial_number,
            manufacturer=manufacturer,
            model=model,
            firmware_version=firmware_version,
            connection_type=connection_type,
            connection_params=connection_params or {},
            capabilities=capabilities or [],
            device_token_hash=device_token_hash,
            status="registered",
            is_active=True,
            created_at=datetime.utcnow()
        )
        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)

        return {
            "device_id": str(device.id),
            "device_token": device_token,  # Only returned once
            "device_type": device_type,
            "status": "registered",
            "warning": "Save the device token securely. It will not be shown again."
        }

    async def authenticate_device(
        self,
        device_id: UUID,
        device_token: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a hardware device."""
        from app.models.gap_features_models import SDKHardwareDevice as HardwareDeviceModel

        token_hash = hashlib.sha256(device_token.encode()).hexdigest()

        result = await self.db.execute(
            select(HardwareDeviceModel).where(
                and_(
                    HardwareDeviceModel.id == device_id,
                    HardwareDeviceModel.device_token_hash == token_hash,
                    HardwareDeviceModel.is_active == True
                )
            )
        )
        device = result.scalar_one_or_none()

        if not device:
            return None

        # Update last seen
        device.last_seen_at = datetime.utcnow()
        device.status = "online"
        await self.db.commit()

        return {
            "device_id": str(device.id),
            "venue_id": str(device.venue_id),
            "station_id": str(device.station_id) if device.station_id else None,
            "device_type": device.device_type,
            "capabilities": device.capabilities,
            "connection_params": device.connection_params
        }

    async def update_device_status(
        self,
        device_id: UUID,
        status: str,
        status_details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update device status."""
        from app.models.gap_features_models import SDKHardwareDevice as HardwareDeviceModel

        result = await self.db.execute(
            select(HardwareDeviceModel).where(HardwareDeviceModel.id == device_id)
        )
        device = result.scalar_one_or_none()

        if not device:
            return False

        device.status = status
        device.status_details = status_details or {}
        device.last_seen_at = datetime.utcnow()
        await self.db.commit()
        return True

    async def get_venue_devices(
        self,
        venue_id: UUID,
        device_type: Optional[str] = None,
        station_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get all devices for a venue."""
        from app.models.gap_features_models import SDKHardwareDevice as HardwareDeviceModel

        query = select(HardwareDeviceModel).where(
            and_(
                HardwareDeviceModel.venue_id == venue_id,
                HardwareDeviceModel.is_active == True
            )
        )

        if device_type:
            query = query.where(HardwareDeviceModel.device_type == device_type)
        if station_id:
            query = query.where(HardwareDeviceModel.station_id == station_id)

        result = await self.db.execute(query)
        devices = result.scalars().all()

        return [
            {
                "id": str(d.id),
                "device_type": d.device_type,
                "serial_number": d.serial_number,
                "manufacturer": d.manufacturer,
                "model": d.model,
                "status": d.status,
                "connection_type": d.connection_type,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None
            }
            for d in devices
        ]

    async def deactivate_device(self, device_id: UUID) -> bool:
        """Deactivate a device."""
        from app.models.gap_features_models import SDKHardwareDevice as HardwareDeviceModel

        result = await self.db.execute(
            select(HardwareDeviceModel).where(HardwareDeviceModel.id == device_id)
        )
        device = result.scalar_one_or_none()

        if device:
            device.is_active = False
            device.status = "deactivated"
            await self.db.commit()
            return True
        return False

    # ==================== PAYMENT TERMINAL SDK ====================

    async def create_terminal_session(
        self,
        device_id: UUID,
        session_type: str = "payment"
    ) -> Dict[str, Any]:
        """Create a terminal session for payment processing."""
        from app.models.gap_features_models import SDKTerminalSession as TerminalSession

        session = TerminalSession(
            id=uuid4(),
            device_id=device_id,
            session_type=session_type,
            status="active",
            created_at=datetime.utcnow()
        )
        self.db.add(session)
        await self.db.commit()

        return {
            "session_id": str(session.id),
            "device_id": str(device_id),
            "status": "active"
        }

    async def send_terminal_command(
        self,
        device_id: UUID,
        command: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a command to a payment terminal."""
        from app.models.gap_features_models import SDKTerminalCommand as TerminalCommand

        # Validate command
        valid_commands = [
            "start_transaction", "cancel_transaction", "get_status",
            "print_receipt", "display_message", "request_signature",
            "process_card", "void_transaction", "refund",
            "batch_close", "get_batch_summary"
        ]

        if command not in valid_commands:
            raise ValueError(f"Invalid command: {command}")

        cmd = TerminalCommand(
            id=uuid4(),
            device_id=device_id,
            command=command,
            params=params,
            status="pending",
            created_at=datetime.utcnow()
        )
        self.db.add(cmd)
        await self.db.commit()

        return {
            "command_id": str(cmd.id),
            "command": command,
            "status": "pending"
        }

    async def get_command_result(
        self,
        command_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get the result of a terminal command."""
        from app.models.gap_features_models import SDKTerminalCommand as TerminalCommand

        result = await self.db.execute(
            select(TerminalCommand).where(TerminalCommand.id == command_id)
        )
        cmd = result.scalar_one_or_none()

        if not cmd:
            return None

        return {
            "command_id": str(cmd.id),
            "command": cmd.command,
            "status": cmd.status,
            "result": cmd.result,
            "error": cmd.error,
            "completed_at": cmd.completed_at.isoformat() if cmd.completed_at else None
        }

    async def update_command_result(
        self,
        command_id: UUID,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """Update command result (called by device)."""
        from app.models.gap_features_models import SDKTerminalCommand as TerminalCommand

        cmd_result = await self.db.execute(
            select(TerminalCommand).where(TerminalCommand.id == command_id)
        )
        cmd = cmd_result.scalar_one_or_none()

        if not cmd:
            return False

        cmd.status = status
        cmd.result = result
        cmd.error = error
        if status in ["completed", "failed"]:
            cmd.completed_at = datetime.utcnow()

        await self.db.commit()
        return True

    # ==================== PRINTER SDK ====================

    async def print_receipt(
        self,
        device_id: UUID,
        receipt_data: Dict[str, Any],
        copies: int = 1
    ) -> Dict[str, Any]:
        """Send print job to receipt printer."""
        return await self.send_terminal_command(
            device_id=device_id,
            command="print_receipt",
            params={
                "receipt_data": receipt_data,
                "copies": copies
            }
        )

    async def open_cash_drawer(
        self,
        device_id: UUID
    ) -> Dict[str, Any]:
        """Open cash drawer."""
        return await self.send_terminal_command(
            device_id=device_id,
            command="open_drawer",
            params={}
        )

    async def display_customer_message(
        self,
        device_id: UUID,
        lines: List[str]
    ) -> Dict[str, Any]:
        """Display message on customer display."""
        return await self.send_terminal_command(
            device_id=device_id,
            command="display_message",
            params={"lines": lines}
        )

    # ==================== DEVICE DIAGNOSTICS ====================

    async def run_device_diagnostics(
        self,
        device_id: UUID
    ) -> Dict[str, Any]:
        """Run diagnostics on a device."""
        from app.models.gap_features_models import SDKHardwareDevice as HardwareDeviceModel

        result = await self.db.execute(
            select(HardwareDeviceModel).where(HardwareDeviceModel.id == device_id)
        )
        device = result.scalar_one_or_none()

        if not device:
            raise ValueError("Device not found")

        # Check device connectivity
        is_online = device.last_seen_at and \
                   (datetime.utcnow() - device.last_seen_at).total_seconds() < 300

        diagnostics = {
            "device_id": str(device_id),
            "device_type": device.device_type,
            "connection_status": "online" if is_online else "offline",
            "last_seen": device.last_seen_at.isoformat() if device.last_seen_at else None,
            "firmware_version": device.firmware_version,
            "tests": []
        }

        # Add device-specific tests
        if device.device_type == "payment_terminal":
            diagnostics["tests"] = [
                {"name": "Network Connectivity", "status": "pass" if is_online else "fail"},
                {"name": "Card Reader", "status": "pending"},
                {"name": "PIN Pad", "status": "pending"},
                {"name": "Printer", "status": "pending"}
            ]
        elif device.device_type == "receipt_printer":
            diagnostics["tests"] = [
                {"name": "Connection", "status": "pass" if is_online else "fail"},
                {"name": "Paper Status", "status": "pending"},
                {"name": "Print Head", "status": "pending"}
            ]

        return diagnostics

    async def get_device_logs(
        self,
        device_id: UUID,
        limit: int = 100,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get device activity logs."""
        from app.models.gap_features_models import SDKDeviceLog as DeviceLog

        query = select(DeviceLog).where(DeviceLog.device_id == device_id)

        if since:
            query = query.where(DeviceLog.created_at >= since)

        query = query.order_by(desc(DeviceLog.created_at)).limit(limit)

        result = await self.db.execute(query)
        logs = result.scalars().all()

        return [
            {
                "id": str(log.id),
                "event_type": log.event_type,
                "message": log.message,
                "data": log.data,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]

    async def log_device_event(
        self,
        device_id: UUID,
        event_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a device event."""
        from app.models.gap_features_models import SDKDeviceLog as DeviceLog

        log = DeviceLog(
            id=uuid4(),
            device_id=device_id,
            event_type=event_type,
            message=message,
            data=data or {},
            created_at=datetime.utcnow()
        )
        self.db.add(log)
        await self.db.commit()


class BNPLService:
    """
    Buy Now Pay Later integration service.
    Supports Klarna, Affirm, Afterpay, and local BNPL providers.
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== BNPL PROVIDER CONFIGURATION ====================

    async def configure_provider(
        self,
        venue_id: UUID,
        provider: str,  # 'klarna', 'affirm', 'afterpay', 'clearpay', 'zip'
        credentials: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Configure a BNPL provider for a venue."""
        from app.models.gap_features_models import BNPLConfiguration

        # Check if already configured
        result = await self.db.execute(
            select(BNPLConfiguration).where(
                and_(
                    BNPLConfiguration.venue_id == venue_id,
                    BNPLConfiguration.provider == provider
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.credentials_encrypted = self._encrypt_credentials(credentials)
            existing.settings = settings or {}
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            return {"status": "updated", "provider": provider}

        config = BNPLConfiguration(
            id=uuid4(),
            venue_id=venue_id,
            provider=provider,
            credentials_encrypted=self._encrypt_credentials(credentials),
            settings=settings or {},
            is_active=True,
            created_at=datetime.utcnow()
        )
        self.db.add(config)
        await self.db.commit()

        return {"status": "configured", "provider": provider}

    def _encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """Encrypt BNPL credentials."""
        import json
        from app.core.security import encrypt_data
        return encrypt_data(json.dumps(credentials))

    def _decrypt_credentials(self, encrypted: str) -> Dict[str, Any]:
        """Decrypt BNPL credentials."""
        import json
        from app.core.security import decrypt_data
        return json.loads(decrypt_data(encrypted))

    async def get_enabled_providers(
        self,
        venue_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get enabled BNPL providers for a venue."""
        from app.models.gap_features_models import BNPLConfiguration

        result = await self.db.execute(
            select(BNPLConfiguration).where(
                and_(
                    BNPLConfiguration.venue_id == venue_id,
                    BNPLConfiguration.is_active == True
                )
            )
        )
        configs = result.scalars().all()

        providers_info = {
            "klarna": {
                "name": "Klarna",
                "logo": "https://cdn.klarna.com/1.0/shared/image/generic/logo/en_us/basic/logo_black.png",
                "min_amount": 35,
                "max_amount": 1000
            },
            "affirm": {
                "name": "Affirm",
                "logo": "https://cdn-assets.affirm.com/images/black_logo-white_bg.png",
                "min_amount": 50,
                "max_amount": 17500
            },
            "afterpay": {
                "name": "Afterpay",
                "logo": "https://static.afterpay.com/logo/afterpay-logo.png",
                "min_amount": 1,
                "max_amount": 2000
            },
            "clearpay": {
                "name": "Clearpay",
                "logo": "https://static.clearpay.co.uk/logo/clearpay-logo.png",
                "min_amount": 1,
                "max_amount": 1000
            },
            "zip": {
                "name": "Zip",
                "logo": "https://zip.co/assets/images/zip-logo.svg",
                "min_amount": 35,
                "max_amount": 1500
            }
        }

        return [
            {
                "provider": c.provider,
                "name": providers_info.get(c.provider, {}).get("name", c.provider),
                "logo": providers_info.get(c.provider, {}).get("logo"),
                "min_amount": providers_info.get(c.provider, {}).get("min_amount", 0),
                "max_amount": providers_info.get(c.provider, {}).get("max_amount", 10000),
                "settings": c.settings
            }
            for c in configs
        ]

    # ==================== BNPL TRANSACTIONS ====================

    async def create_bnpl_session(
        self,
        venue_id: UUID,
        provider: str,
        order_id: UUID,
        amount: float,
        currency: str = "USD",
        customer_info: Optional[Dict[str, Any]] = None,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a BNPL checkout session."""
        from app.models.gap_features_models import BNPLTransaction, BNPLConfiguration
        import httpx

        # Get provider config
        result = await self.db.execute(
            select(BNPLConfiguration).where(
                and_(
                    BNPLConfiguration.venue_id == venue_id,
                    BNPLConfiguration.provider == provider,
                    BNPLConfiguration.is_active == True
                )
            )
        )
        config = result.scalar_one_or_none()

        if not config:
            raise ValueError(f"BNPL provider {provider} not configured")

        credentials = self._decrypt_credentials(config.credentials_encrypted)

        # Create session based on provider
        if provider == "klarna":
            session_data = await self._create_klarna_session(
                credentials, amount, currency, customer_info, return_url, cancel_url
            )
        elif provider == "affirm":
            session_data = await self._create_affirm_session(
                credentials, amount, currency, customer_info, return_url, cancel_url
            )
        elif provider == "afterpay":
            session_data = await self._create_afterpay_session(
                credentials, amount, currency, customer_info, return_url, cancel_url
            )
        else:
            raise ValueError(f"Unsupported BNPL provider: {provider}")

        # Store transaction
        transaction = BNPLTransaction(
            id=uuid4(),
            venue_id=venue_id,
            order_id=order_id,
            provider=provider,
            external_session_id=session_data.get("session_id"),
            amount=amount,
            currency=currency,
            status="pending",
            redirect_url=session_data.get("redirect_url"),
            customer_info=customer_info,
            created_at=datetime.utcnow()
        )
        self.db.add(transaction)
        await self.db.commit()

        return {
            "transaction_id": str(transaction.id),
            "provider": provider,
            "redirect_url": session_data.get("redirect_url"),
            "session_id": session_data.get("session_id"),
            "status": "pending"
        }

    async def _create_klarna_session(
        self,
        credentials: Dict[str, Any],
        amount: float,
        currency: str,
        customer_info: Optional[Dict[str, Any]],
        return_url: Optional[str],
        cancel_url: Optional[str]
    ) -> Dict[str, Any]:
        """Create Klarna checkout session."""
        import httpx
        import base64

        api_key = credentials.get("api_key")
        api_secret = credentials.get("api_secret")
        auth = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()

        base_url = credentials.get("base_url", "https://api.klarna.com")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/payments/v1/sessions",
                headers={
                    "Authorization": f"Basic {auth}",
                    "Content-Type": "application/json"
                },
                json={
                    "purchase_country": customer_info.get("country", "US") if customer_info else "US",
                    "purchase_currency": currency,
                    "order_amount": int(amount * 100),
                    "order_lines": [{
                        "type": "physical",
                        "name": "Order",
                        "quantity": 1,
                        "unit_price": int(amount * 100),
                        "total_amount": int(amount * 100)
                    }],
                    "merchant_urls": {
                        "confirmation": return_url,
                        "cancel": cancel_url
                    }
                }
            )
            data = response.json()

            return {
                "session_id": data.get("session_id"),
                "redirect_url": data.get("redirect_url")
            }

    async def _create_affirm_session(
        self,
        credentials: Dict[str, Any],
        amount: float,
        currency: str,
        customer_info: Optional[Dict[str, Any]],
        return_url: Optional[str],
        cancel_url: Optional[str]
    ) -> Dict[str, Any]:
        """Create Affirm checkout session."""
        import httpx

        public_key = credentials.get("public_key")
        private_key = credentials.get("private_key")
        base_url = credentials.get("base_url", "https://api.affirm.com")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/v1/checkout",
                auth=(public_key, private_key),
                json={
                    "merchant": {
                        "user_confirmation_url": return_url,
                        "user_cancel_url": cancel_url
                    },
                    "total": int(amount * 100),
                    "currency": currency
                }
            )
            data = response.json()

            return {
                "session_id": data.get("checkout_id"),
                "redirect_url": data.get("redirect_url")
            }

    async def _create_afterpay_session(
        self,
        credentials: Dict[str, Any],
        amount: float,
        currency: str,
        customer_info: Optional[Dict[str, Any]],
        return_url: Optional[str],
        cancel_url: Optional[str]
    ) -> Dict[str, Any]:
        """Create Afterpay checkout session."""
        import httpx

        merchant_id = credentials.get("merchant_id")
        secret_key = credentials.get("secret_key")
        base_url = credentials.get("base_url", "https://api.afterpay.com")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v2/checkouts",
                auth=(merchant_id, secret_key),
                json={
                    "amount": {
                        "amount": str(amount),
                        "currency": currency
                    },
                    "merchant": {
                        "redirectConfirmUrl": return_url,
                        "redirectCancelUrl": cancel_url
                    }
                }
            )
            data = response.json()

            return {
                "session_id": data.get("token"),
                "redirect_url": data.get("redirectCheckoutUrl")
            }

    async def capture_bnpl_payment(
        self,
        transaction_id: UUID
    ) -> Dict[str, Any]:
        """Capture an authorized BNPL payment."""
        from app.models.gap_features_models import BNPLTransaction, BNPLConfiguration

        result = await self.db.execute(
            select(BNPLTransaction).where(BNPLTransaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            raise ValueError("Transaction not found")

        if transaction.status != "authorized":
            raise ValueError(f"Cannot capture transaction with status: {transaction.status}")

        # Get provider config
        config_result = await self.db.execute(
            select(BNPLConfiguration).where(
                and_(
                    BNPLConfiguration.venue_id == transaction.venue_id,
                    BNPLConfiguration.provider == transaction.provider
                )
            )
        )
        config = config_result.scalar_one_or_none()

        if not config:
            raise ValueError("Provider configuration not found")

        credentials = self._decrypt_credentials(config.credentials_encrypted)

        # Capture based on provider
        # (Implementation would call provider-specific capture API)

        transaction.status = "captured"
        transaction.captured_at = datetime.utcnow()
        await self.db.commit()

        return {
            "transaction_id": str(transaction_id),
            "status": "captured",
            "captured_at": transaction.captured_at.isoformat()
        }

    async def refund_bnpl_payment(
        self,
        transaction_id: UUID,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Refund a BNPL payment (full or partial)."""
        from app.models.gap_features_models import BNPLTransaction

        result = await self.db.execute(
            select(BNPLTransaction).where(BNPLTransaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            raise ValueError("Transaction not found")

        if transaction.status not in ["captured", "completed"]:
            raise ValueError(f"Cannot refund transaction with status: {transaction.status}")

        refund_amount = amount if amount else transaction.amount

        # Process refund (would call provider-specific refund API)

        if refund_amount >= transaction.amount:
            transaction.status = "refunded"
        else:
            transaction.status = "partially_refunded"

        transaction.refunded_amount = (transaction.refunded_amount or 0) + refund_amount
        transaction.refunded_at = datetime.utcnow()
        await self.db.commit()

        return {
            "transaction_id": str(transaction_id),
            "status": transaction.status,
            "refunded_amount": refund_amount,
            "refunded_at": transaction.refunded_at.isoformat()
        }

    async def handle_webhook(
        self,
        provider: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle BNPL provider webhook."""
        from app.models.gap_features_models import BNPLTransaction

        # Extract session/transaction ID based on provider
        if provider == "klarna":
            external_id = payload.get("order_id") or payload.get("session_id")
            event_type = payload.get("event_type")
        elif provider == "affirm":
            external_id = payload.get("checkout_id")
            event_type = payload.get("event")
        elif provider == "afterpay":
            external_id = payload.get("token")
            event_type = payload.get("status")
        else:
            return {"status": "unknown_provider"}

        # Find transaction
        result = await self.db.execute(
            select(BNPLTransaction).where(
                and_(
                    BNPLTransaction.external_session_id == external_id,
                    BNPLTransaction.provider == provider
                )
            )
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            return {"status": "transaction_not_found"}

        # Update status based on event
        status_mapping = {
            "authorized": "authorized",
            "captured": "captured",
            "completed": "completed",
            "cancelled": "cancelled",
            "declined": "declined",
            "expired": "expired",
            "refunded": "refunded"
        }

        new_status = status_mapping.get(event_type.lower() if event_type else "", transaction.status)
        transaction.status = new_status
        transaction.webhook_data = payload
        transaction.updated_at = datetime.utcnow()

        await self.db.commit()

        return {
            "transaction_id": str(transaction.id),
            "status": new_status,
            "event": event_type
        }

    async def get_transaction(
        self,
        transaction_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get BNPL transaction details."""
        from app.models.gap_features_models import BNPLTransaction

        result = await self.db.execute(
            select(BNPLTransaction).where(BNPLTransaction.id == transaction_id)
        )
        transaction = result.scalar_one_or_none()

        if not transaction:
            return None

        return {
            "id": str(transaction.id),
            "order_id": str(transaction.order_id),
            "provider": transaction.provider,
            "amount": float(transaction.amount),
            "currency": transaction.currency,
            "status": transaction.status,
            "redirect_url": transaction.redirect_url,
            "created_at": transaction.created_at.isoformat(),
            "captured_at": transaction.captured_at.isoformat() if transaction.captured_at else None,
            "refunded_amount": float(transaction.refunded_amount) if transaction.refunded_amount else None
        }

    async def get_venue_transactions(
        self,
        venue_id: UUID,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Get BNPL transactions for a venue."""
        from app.models.gap_features_models import BNPLTransaction

        query = select(BNPLTransaction).where(BNPLTransaction.venue_id == venue_id)

        if provider:
            query = query.where(BNPLTransaction.provider == provider)
        if status:
            query = query.where(BNPLTransaction.status == status)
        if start_date:
            query = query.where(BNPLTransaction.created_at >= start_date)
        if end_date:
            query = query.where(BNPLTransaction.created_at <= end_date)

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        # Get paginated results
        query = query.order_by(desc(BNPLTransaction.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        transactions = result.scalars().all()

        return [
            {
                "id": str(t.id),
                "order_id": str(t.order_id),
                "provider": t.provider,
                "amount": float(t.amount),
                "currency": t.currency,
                "status": t.status,
                "created_at": t.created_at.isoformat()
            }
            for t in transactions
        ], total
