"""
Stripe Payment Service
Handles subscription payments and billing
"""

import stripe
from typing import Dict, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class StripePaymentService:
    """
    Stripe payment integration for BJ's Bar subscriptions
    
    Features:
    - Customer management
    - Subscription management
    - Payment processing
    - Invoice handling
    - Webhook processing
    """
    
    def __init__(self, api_key: str):
        """
        Initialize Stripe service
        
        Args:
            api_key: Stripe secret key
        """
        self.api_key = api_key
        stripe.api_key = api_key
    
    # ==================== CUSTOMERS ====================
    
    def create_customer(
        self,
        email: str,
        name: str,
        company: str,
        phone: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Create Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                phone=phone,
                metadata={
                    "company": company,
                    **(metadata or {})
                }
            )
            
            logger.info(f"Created Stripe customer: {customer.id}")
            
            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "created": customer.created
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {str(e)}")
            raise Exception(f"Stripe error: {str(e)}")
    
    def get_customer(self, customer_id: str) -> Dict:
        """Get customer details"""
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return {
                "id": customer.id,
                "email": customer.email,
                "name": customer.name,
                "balance": customer.balance,
                "currency": customer.currency
            }
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting customer: {str(e)}")
            raise Exception(f"Stripe error: {str(e)}")
    
    # ==================== SUBSCRIPTIONS ====================
    
    def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        trial_days: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Create subscription"""
        try:
            sub_params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {}
            }
            
            if trial_days and trial_days > 0:
                sub_params["trial_period_days"] = trial_days
            
            subscription = stripe.Subscription.create(**sub_params)
            
            logger.info(f"Created subscription: {subscription.id}")
            
            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "trial_end": subscription.trial_end,
                "cancel_at_period_end": subscription.cancel_at_period_end
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {str(e)}")
            raise Exception(f"Stripe error: {str(e)}")
    
    def get_subscription(self, subscription_id: str) -> Dict:
        """Get subscription details"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            
            return {
                "id": subscription.id,
                "customer": subscription.customer,
                "status": subscription.status,
                "current_period_start": subscription.current_period_start,
                "current_period_end": subscription.current_period_end,
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "trial_end": subscription.trial_end
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error getting subscription: {str(e)}")
            raise Exception(f"Stripe error: {str(e)}")
    
    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False
    ) -> Dict:
        """Cancel subscription"""
        try:
            if immediately:
                subscription = stripe.Subscription.delete(subscription_id)
                logger.info(f"Cancelled subscription immediately: {subscription_id}")
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
                logger.info(f"Subscription will cancel at period end: {subscription_id}")
            
            return {
                "id": subscription.id,
                "status": subscription.status,
                "cancelled": True,
                "immediately": immediately
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error cancelling subscription: {str(e)}")
            raise Exception(f"Stripe error: {str(e)}")

    # ==================== REFUNDS ====================

    def refund_payment(
        self,
        charge_id: str,
        amount: Optional[int] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Refund a payment

        Args:
            charge_id: The Stripe charge ID to refund
            amount: Amount to refund in cents (if None, full refund)
            reason: Reason for refund ('duplicate', 'fraudulent', 'requested_by_customer')
            metadata: Additional metadata for the refund

        Returns:
            Dict with refund details
        """
        try:
            refund_params = {
                "charge": charge_id,
                "metadata": metadata or {}
            }

            if amount is not None:
                refund_params["amount"] = amount

            if reason:
                refund_params["reason"] = reason

            refund = stripe.Refund.create(**refund_params)

            logger.info(f"Created refund: {refund.id} for charge: {charge_id}")

            return {
                "id": refund.id,
                "charge": refund.charge,
                "amount": refund.amount,
                "currency": refund.currency,
                "status": refund.status,
                "reason": refund.reason,
                "created": refund.created
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating refund: {str(e)}")
            raise Exception(f"Stripe error: {str(e)}")

    # ==================== WEBHOOKS ====================
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
        webhook_secret: str
    ) -> Dict:
        """Verify webhook signature"""
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                webhook_secret
            )
            
            logger.info(f"Verified webhook event: {event['type']}")
            return event
            
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            raise Exception("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            raise Exception("Invalid signature")
    
    def handle_webhook_event(self, event: Dict) -> Dict:
        """Handle webhook events"""
        event_type = event["type"]
        data = event["data"]["object"]
        
        logger.info(f"Handling webhook event: {event_type}")
        
        handlers = {
            "customer.subscription.created": self._handle_subscription_created,
            "customer.subscription.updated": self._handle_subscription_updated,
            "customer.subscription.deleted": self._handle_subscription_deleted,
            "invoice.payment_succeeded": self._handle_payment_succeeded,
            "invoice.payment_failed": self._handle_payment_failed,
            "charge.refunded": self._handle_charge_refunded,
        }
        
        handler = handlers.get(event_type)
        if handler:
            return handler(data)
        
        logger.warning(f"Unhandled webhook event type: {event_type}")
        return {"handled": False}
    
    def _handle_subscription_created(self, data: Dict) -> Dict:
        """Handle subscription created - activate customer account"""
        logger.info(f"Subscription created: {data['id']}")
        
        # Store subscription record
        if not hasattr(self, '_subscriptions'):
            self._subscriptions = {}
        
        subscription_record = {
            "id": data["id"],
            "customer_id": data["customer"],
            "status": data["status"],
            "plan_id": data.get("plan", {}).get("id"),
            "current_period_start": data.get("current_period_start"),
            "current_period_end": data.get("current_period_end"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "activated": True
        }
        self._subscriptions[data["id"]] = subscription_record
        
        # In production: Update venue status to active
        # self.db.query(Venue).filter(Venue.stripe_customer_id == data["customer"]).update({"status": "active"})
        
        return {
            "action": "subscription_created",
            "subscription_id": data["id"],
            "customer_id": data["customer"],
            "status": data["status"],
            "processed": True
        }
    
    def _handle_subscription_updated(self, data: Dict) -> Dict:
        """Handle subscription updated - sync status changes"""
        logger.info(f"Subscription updated: {data['id']}")
        
        if hasattr(self, '_subscriptions') and data["id"] in self._subscriptions:
            self._subscriptions[data["id"]].update({
                "status": data["status"],
                "current_period_end": data.get("current_period_end"),
                "updated_at": datetime.now(timezone.utc).isoformat()
            })
        
        # Handle status changes
        if data["status"] == "past_due":
            logger.warning(f"Subscription {data['id']} is past due")
            # Send payment reminder notification
        
        return {
            "action": "subscription_updated",
            "subscription_id": data["id"],
            "status": data["status"],
            "processed": True
        }
    
    def _handle_subscription_deleted(self, data: Dict) -> Dict:
        """Handle subscription deleted - deactivate customer account"""
        logger.info(f"Subscription deleted: {data['id']}")
        
        if hasattr(self, '_subscriptions') and data["id"] in self._subscriptions:
            self._subscriptions[data["id"]]["status"] = "canceled"
            self._subscriptions[data["id"]]["canceled_at"] = datetime.now(timezone.utc).isoformat()
        
        # In production: Deactivate venue but preserve data
        # self.db.query(Venue).filter(Venue.stripe_subscription_id == data["id"]).update({"status": "inactive"})
        
        return {
            "action": "subscription_deleted",
            "subscription_id": data["id"],
            "processed": True
        }
    
    def _handle_payment_succeeded(self, data: Dict) -> Dict:
        """Handle successful payment - record and extend subscription"""
        logger.info(f"Payment succeeded: {data['id']}")
        
        # Store payment record
        if not hasattr(self, '_payments'):
            self._payments = []
        
        payment_record = {
            "invoice_id": data["id"],
            "customer_id": data["customer"],
            "amount": data["amount_paid"],
            "currency": data["currency"],
            "status": "succeeded",
            "paid_at": datetime.now(timezone.utc).isoformat()
        }
        self._payments.append(payment_record)
        
        # In production: Update venue subscription end date
        # self.db.query(Venue).filter(Venue.stripe_customer_id == data["customer"]).update({"subscription_end": new_end_date})
        
        return {
            "action": "payment_succeeded",
            "invoice_id": data["id"],
            "amount": data["amount_paid"],
            "currency": data["currency"],
            "processed": True
        }
    
    def _handle_payment_failed(self, data: Dict) -> Dict:
        """Handle failed payment - notify customer and schedule retry"""
        logger.error(f"Payment failed: {data['id']}")
        
        # Store failed payment record
        if not hasattr(self, '_failed_payments'):
            self._failed_payments = []
        
        failure_record = {
            "invoice_id": data["id"],
            "customer_id": data["customer"],
            "amount": data["amount_due"],
            "failure_reason": data.get("last_finalization_error", {}).get("message", "Unknown"),
            "attempt_count": data.get("attempt_count", 1),
            "next_attempt": data.get("next_payment_attempt"),
            "failed_at": datetime.now(timezone.utc).isoformat()
        }
        self._failed_payments.append(failure_record)
        
        # In production: Send email notification to customer
        # notification_service.send_payment_failed_email(data["customer"], data["amount_due"])
        
        return {
            "action": "payment_failed",
            "invoice_id": data["id"],
            "customer_id": data["customer"],
            "amount": data["amount_due"],
            "retry_scheduled": data.get("next_payment_attempt") is not None,
            "processed": True
        }

    def _handle_charge_refunded(self, data: Dict) -> Dict:
        """Handle charge refunded - record refund and update payment records"""
        logger.info(f"Charge refunded: {data['id']}")

        # Store refund record
        if not hasattr(self, '_refunds'):
            self._refunds = []

        refund_record = {
            "charge_id": data["id"],
            "customer_id": data.get("customer"),
            "amount_refunded": data.get("amount_refunded", 0),
            "currency": data.get("currency"),
            "refunded": data.get("refunded", False),
            "refund_count": len(data.get("refunds", {}).get("data", [])),
            "refunded_at": datetime.now(timezone.utc).isoformat()
        }
        self._refunds.append(refund_record)

        # In production: Update payment records and notify customer
        # self.db.query(Payment).filter(Payment.stripe_charge_id == data["id"]).update({"status": "refunded"})
        # notification_service.send_refund_confirmation_email(data["customer"], data["amount_refunded"])

        return {
            "action": "charge_refunded",
            "charge_id": data["id"],
            "customer_id": data.get("customer"),
            "amount_refunded": data.get("amount_refunded", 0),
            "currency": data.get("currency"),
            "processed": True
        }
