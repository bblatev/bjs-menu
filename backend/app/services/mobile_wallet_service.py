"""Mobile Wallet Service.

Handles Apple Pay and Google Pay payments via Stripe.
"""

import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class WalletType(str, Enum):
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    LINK = "link"  # Stripe Link


class WalletPaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class WalletConfiguration:
    """Configuration for mobile wallet payments."""
    venue_id: int
    apple_pay_enabled: bool = True
    google_pay_enabled: bool = True
    link_enabled: bool = True
    merchant_name: str = ""
    merchant_country: str = "US"
    merchant_currency: str = "USD"
    apple_pay_merchant_id: Optional[str] = None
    supported_networks: List[str] = field(default_factory=lambda: ["visa", "mastercard", "amex", "discover"])


@dataclass
class WalletPayment:
    """A mobile wallet payment record."""
    payment_id: str
    order_id: str
    wallet_type: WalletType
    amount: int  # Amount in cents
    currency: str
    status: WalletPaymentStatus
    stripe_payment_intent_id: Optional[str] = None
    stripe_payment_method_id: Optional[str] = None
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    customer_email: Optional[str] = None
    receipt_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class MobileWalletService:
    """Service for Apple Pay and Google Pay payments.

    This service integrates with Stripe to handle mobile wallet payments.
    It provides:
    - Payment session creation for Apple Pay/Google Pay
    - Payment verification and completion
    - Wallet configuration management
    """

    def __init__(self, stripe_service=None):
        self.stripe_service = stripe_service

        # In-memory storage (use database in production)
        self._configurations: Dict[int, WalletConfiguration] = {}
        self._payments: Dict[str, WalletPayment] = {}

        # Default configuration
        self._default_config = WalletConfiguration(
            venue_id=0,
            merchant_name="BJS Restaurant",
            merchant_country="US",
            merchant_currency="USD",
        )

    # =========================================================================
    # Configuration
    # =========================================================================

    def get_configuration(self, venue_id: int) -> WalletConfiguration:
        """Get wallet configuration for a venue."""
        return self._configurations.get(venue_id, self._default_config)

    def update_configuration(
        self,
        venue_id: int,
        **updates,
    ) -> WalletConfiguration:
        """Update wallet configuration for a venue."""
        config = self._configurations.get(venue_id)

        if not config:
            config = WalletConfiguration(venue_id=venue_id)
            self._configurations[venue_id] = config

        for key, value in updates.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        return config

    def get_client_config(self, venue_id: int) -> Dict[str, Any]:
        """Get client-side configuration for payment request button.

        Returns configuration needed for Stripe.js PaymentRequest.
        """
        config = self.get_configuration(venue_id)

        return {
            "country": config.merchant_country,
            "currency": config.merchant_currency.lower(),
            "requestPayerName": True,
            "requestPayerEmail": True,
            "applePay": {
                "enabled": config.apple_pay_enabled,
                "merchantId": config.apple_pay_merchant_id,
            },
            "googlePay": {
                "enabled": config.google_pay_enabled,
                "merchantName": config.merchant_name,
            },
            "link": {
                "enabled": config.link_enabled,
            },
            "supportedNetworks": config.supported_networks,
        }

    # =========================================================================
    # Payment Session
    # =========================================================================

    def create_payment_session(
        self,
        order_id: str,
        amount: int,
        currency: str = "usd",
        venue_id: int = 0,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Create a payment session for mobile wallet payment.

        This creates a Stripe PaymentIntent configured for wallet payments.
        The client then uses this with Stripe.js PaymentRequest to display
        the Apple Pay or Google Pay sheet.
        """
        config = self.get_configuration(venue_id)

        # Build payment intent metadata
        intent_metadata = {
            "order_id": order_id,
            "venue_id": str(venue_id),
            "payment_source": "mobile_wallet",
        }
        if metadata:
            intent_metadata.update(metadata)

        # Create payment intent via Stripe service if available
        payment_intent_data = {
            "amount": amount,
            "currency": currency,
            "automatic_payment_methods": {
                "enabled": True,
            },
            "metadata": intent_metadata,
        }

        if description:
            payment_intent_data["description"] = description

        # In production, call Stripe API
        # For now, simulate payment intent creation
        client_secret = f"pi_{uuid.uuid4().hex}_secret_{uuid.uuid4().hex[:8]}"
        payment_intent_id = f"pi_{uuid.uuid4().hex}"

        # Create local payment record
        payment = WalletPayment(
            payment_id=f"wp-{uuid.uuid4().hex[:8]}",
            order_id=order_id,
            wallet_type=WalletType.APPLE_PAY,  # Will be updated on completion
            amount=amount,
            currency=currency,
            status=WalletPaymentStatus.PENDING,
            stripe_payment_intent_id=payment_intent_id,
        )
        self._payments[payment.payment_id] = payment

        logger.info(f"Created wallet payment session {payment.payment_id} for order {order_id}")

        return {
            "payment_id": payment.payment_id,
            "client_secret": client_secret,
            "payment_intent_id": payment_intent_id,
            "amount": amount,
            "currency": currency,
            "wallet_config": self.get_client_config(venue_id),
        }

    def confirm_payment(
        self,
        payment_id: str,
        wallet_type: str,
        payment_method_id: Optional[str] = None,
        card_brand: Optional[str] = None,
        card_last4: Optional[str] = None,
        customer_email: Optional[str] = None,
    ) -> Optional[WalletPayment]:
        """Confirm a wallet payment was completed.

        Called after the client-side payment sheet completes.
        """
        payment = self._payments.get(payment_id)
        if not payment:
            return None

        try:
            payment.wallet_type = WalletType(wallet_type)
        except ValueError:
            payment.wallet_type = WalletType.APPLE_PAY

        payment.stripe_payment_method_id = payment_method_id
        payment.card_brand = card_brand
        payment.card_last4 = card_last4
        payment.customer_email = customer_email
        payment.status = WalletPaymentStatus.PROCESSING

        # In production, verify with Stripe that payment succeeded
        # For now, simulate success
        payment.status = WalletPaymentStatus.SUCCEEDED
        payment.completed_at = datetime.utcnow()
        payment.receipt_url = f"https://pay.stripe.com/receipts/{payment.stripe_payment_intent_id}"

        logger.info(f"Confirmed wallet payment {payment_id} via {wallet_type}")

        return payment

    def cancel_payment(self, payment_id: str, reason: str = "") -> Optional[WalletPayment]:
        """Cancel a pending wallet payment."""
        payment = self._payments.get(payment_id)
        if not payment:
            return None

        if payment.status not in (WalletPaymentStatus.PENDING, WalletPaymentStatus.PROCESSING):
            return None

        payment.status = WalletPaymentStatus.CANCELED
        payment.error_message = reason or "Payment canceled"

        logger.info(f"Canceled wallet payment {payment_id}")

        return payment

    def fail_payment(self, payment_id: str, error_message: str) -> Optional[WalletPayment]:
        """Mark a payment as failed."""
        payment = self._payments.get(payment_id)
        if not payment:
            return None

        payment.status = WalletPaymentStatus.FAILED
        payment.error_message = error_message

        logger.info(f"Failed wallet payment {payment_id}: {error_message}")

        return payment

    # =========================================================================
    # Payment Retrieval
    # =========================================================================

    def get_payment(self, payment_id: str) -> Optional[WalletPayment]:
        """Get a wallet payment by ID."""
        return self._payments.get(payment_id)

    def get_payment_by_intent(self, payment_intent_id: str) -> Optional[WalletPayment]:
        """Get a wallet payment by Stripe PaymentIntent ID."""
        for payment in self._payments.values():
            if payment.stripe_payment_intent_id == payment_intent_id:
                return payment
        return None

    def get_payments_by_order(self, order_id: str) -> List[WalletPayment]:
        """Get all wallet payments for an order."""
        return [p for p in self._payments.values() if p.order_id == order_id]

    def list_payments(
        self,
        wallet_type: Optional[WalletType] = None,
        status: Optional[WalletPaymentStatus] = None,
        limit: int = 50,
    ) -> List[WalletPayment]:
        """List wallet payments with optional filters."""
        payments = list(self._payments.values())

        if wallet_type:
            payments = [p for p in payments if p.wallet_type == wallet_type]

        if status:
            payments = [p for p in payments if p.status == status]

        payments = sorted(payments, key=lambda p: p.created_at, reverse=True)

        return payments[:limit]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get wallet payment statistics."""
        payments = list(self._payments.values())
        total = len(payments)

        succeeded = [p for p in payments if p.status == WalletPaymentStatus.SUCCEEDED]
        failed = [p for p in payments if p.status == WalletPaymentStatus.FAILED]

        apple_pay_count = sum(1 for p in succeeded if p.wallet_type == WalletType.APPLE_PAY)
        google_pay_count = sum(1 for p in succeeded if p.wallet_type == WalletType.GOOGLE_PAY)
        link_count = sum(1 for p in succeeded if p.wallet_type == WalletType.LINK)

        total_amount = sum(p.amount for p in succeeded)

        return {
            "total_payments": total,
            "succeeded": len(succeeded),
            "failed": len(failed),
            "success_rate": round(len(succeeded) / total * 100, 2) if total > 0 else 0,
            "by_wallet_type": {
                "apple_pay": apple_pay_count,
                "google_pay": google_pay_count,
                "link": link_count,
            },
            "total_amount_cents": total_amount,
            "total_amount": round(total_amount / 100, 2),
        }


# Singleton instance
_mobile_wallet_service: Optional[MobileWalletService] = None


def get_mobile_wallet_service() -> MobileWalletService:
    """Get the mobile wallet service singleton."""
    global _mobile_wallet_service
    if _mobile_wallet_service is None:
        _mobile_wallet_service = MobileWalletService()
    return _mobile_wallet_service
