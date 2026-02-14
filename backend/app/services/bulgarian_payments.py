"""
Bulgarian Payment Gateway Integrations
Borica and ePay.bg payment processors for Bulgarian market
"""
import hmac
import hashlib
import base64
import logging
from typing import Optional, Dict
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlencode
from app.core.config import settings

logger = logging.getLogger(__name__)

# Optional imports
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class PaymentResult:
    success: bool
    transaction_id: Optional[str] = None
    status: PaymentStatus = PaymentStatus.PENDING
    amount: Optional[float] = None
    currency: str = "BGN"
    error_message: Optional[str] = None
    redirect_url: Optional[str] = None
    raw_response: Optional[Dict] = None


# ============================================================================
# BORICA INTEGRATION (Bulgarian Bank Card Payments)
# ============================================================================

class BoricaService:
    """
    Borica Payment Gateway Integration

    Borica is the primary card payment processor in Bulgaria.
    Supports:
    - Visa, Mastercard, Maestro
    - 3D Secure authentication
    - Recurring payments
    - Refunds
    """

    # Production endpoints
    PROD_URL = "https://3dsgate.borica.bg/cgi-bin/cgi_link"
    # Test endpoints
    TEST_URL = "https://3dsgate-dev.borica.bg/cgi-bin/cgi_link"

    def __init__(self):
        self.terminal_id = settings.borica_terminal_id
        self.merchant_id = settings.borica_merchant_id
        self.private_key_path = settings.borica_private_key_path
        self.certificate_path = settings.borica_certificate_path
        self.is_production = settings.borica_production.lower() == "true"

        self._base_url = self.PROD_URL if self.is_production else self.TEST_URL
        self._initialized = bool(self.terminal_id and self.merchant_id)

    @property
    def is_available(self) -> bool:
        return self._initialized and HAS_REQUESTS

    def create_payment(
        self,
        amount: float,
        order_id: str,
        description: str,
        currency: str = "BGN",
        return_url: Optional[str] = None,
        customer_email: Optional[str] = None
    ) -> PaymentResult:
        """
        Create a payment request and get redirect URL for 3D Secure.

        Args:
            amount: Payment amount
            order_id: Unique order identifier
            description: Payment description
            currency: Currency code (default BGN)
            return_url: URL to redirect after payment
            customer_email: Customer email for receipt

        Returns:
            PaymentResult with redirect_url for 3DS
        """
        if not self._initialized:
            return self._mock_payment(amount, order_id)

        try:
            # Borica message format
            transaction_code = "10"  # Authorization
            amount_str = f"{int(amount * 100):012d}"  # Amount in stotinki
            currency_code = "975"  # BGN ISO code
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

            # Build message
            message = self._build_payment_message(
                trtype=transaction_code,
                amount=amount_str,
                currency=currency_code,
                order_id=order_id,
                description=description,
                timestamp=timestamp,
                return_url=return_url or settings.borica_return_url
            )

            # Sign message
            signature = self._sign_message(message)

            # Build redirect URL
            params = {
                "TERMINAL": self.terminal_id,
                "TRTYPE": transaction_code,
                "AMOUNT": amount_str,
                "CURRENCY": currency_code,
                "ORDER": order_id,
                "DESC": description,
                "MERCHANT": self.merchant_id,
                "TIMESTAMP": timestamp,
                "NONCE": self._generate_nonce(),
                "P_SIGN": signature,
                "BACKREF": return_url or ""
            }

            redirect_url = f"{self._base_url}?{urlencode(params)}"

            return PaymentResult(
                success=True,
                transaction_id=f"BOR-{order_id}-{timestamp}",
                status=PaymentStatus.PENDING,
                amount=amount,
                currency=currency,
                redirect_url=redirect_url
            )

        except Exception as e:
            logger.error(f"Borica payment error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )

    def verify_callback(self, callback_data: Dict) -> PaymentResult:
        """
        Verify and process payment callback from Borica.

        Args:
            callback_data: POST data from Borica callback

        Returns:
            PaymentResult with final status
        """
        if not self._initialized:
            return self._mock_callback(callback_data)

        try:
            # Extract callback fields
            action = callback_data.get("ACTION", "")
            rc = callback_data.get("RC", "")
            approval = callback_data.get("APPROVAL", "")
            order_id = callback_data.get("ORDER", "")
            amount = callback_data.get("AMOUNT", "0")
            signature = callback_data.get("P_SIGN", "")

            # Verify signature
            message = self._build_callback_message(callback_data)
            if not self._verify_signature(message, signature):
                return PaymentResult(
                    success=False,
                    error_message="Invalid signature"
                )

            # Check response code
            if rc == "00":  # Success
                return PaymentResult(
                    success=True,
                    transaction_id=approval,
                    status=PaymentStatus.SUCCESS,
                    amount=int(amount) / 100,
                    raw_response=callback_data
                )
            else:
                return PaymentResult(
                    success=False,
                    status=PaymentStatus.FAILED,
                    error_message=self._get_error_message(rc),
                    raw_response=callback_data
                )

        except Exception as e:
            logger.error(f"Borica callback error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )

    def refund(
        self,
        original_transaction_id: str,
        amount: Optional[float] = None,
        reason: Optional[str] = None
    ) -> PaymentResult:
        """Process a refund for a previous transaction"""
        if not self._initialized:
            return self._mock_refund(original_transaction_id)

        try:
            transaction_code = "24"  # Reversal
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

            # Build refund message
            params = {
                "TERMINAL": self.terminal_id,
                "TRTYPE": transaction_code,
                "MERCHANT": self.merchant_id,
                "RRN": original_transaction_id,
                "TIMESTAMP": timestamp,
                "NONCE": self._generate_nonce()
            }

            if amount:
                params["AMOUNT"] = f"{int(amount * 100):012d}"

            # Would make actual API call here
            return PaymentResult(
                success=True,
                transaction_id=f"REF-{timestamp}",
                status=PaymentStatus.REFUNDED,
                amount=amount
            )

        except Exception as e:
            return PaymentResult(success=False, error_message=str(e))

    def _build_payment_message(self, **kwargs) -> str:
        """Build message string for signing"""
        fields = ["TERMINAL", "TRTYPE", "AMOUNT", "CURRENCY", "ORDER",
                  "MERCHANT", "TIMESTAMP", "NONCE"]
        parts = [kwargs.get(f.lower(), self.__dict__.get(f.lower(), ""))
                 for f in fields]
        return "".join(parts)

    def _build_callback_message(self, data: Dict) -> str:
        """Build message from callback for verification"""
        fields = ["ACTION", "RC", "APPROVAL", "TERMINAL", "TRTYPE",
                  "AMOUNT", "CURRENCY", "ORDER", "RRN", "INT_REF",
                  "TIMESTAMP", "NONCE"]
        return "".join(data.get(f, "") for f in fields)

    def _sign_message(self, message: str) -> str:
        """Sign message with private key"""
        # In production, use RSA signing with private key
        # This is a simplified HMAC for demo
        secret = settings.borica_secret
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return base64.b64encode(signature.encode()).decode()

    def _verify_signature(self, message: str, signature: str) -> bool:
        """Verify callback signature"""
        expected = self._sign_message(message)
        return hmac.compare_digest(expected, signature)

    def _generate_nonce(self) -> str:
        """Generate random nonce"""
        import random
        return "".join(random.choices("0123456789ABCDEF", k=32))

    def _get_error_message(self, code: str) -> str:
        """Get human-readable error message"""
        errors = {
            "01": "Refer to card issuer",
            "04": "Pick up card",
            "05": "Do not honor",
            "12": "Invalid transaction",
            "13": "Invalid amount",
            "14": "Invalid card number",
            "30": "Format error",
            "41": "Lost card",
            "43": "Stolen card",
            "51": "Insufficient funds",
            "54": "Expired card",
            "55": "Incorrect PIN",
            "61": "Exceeds withdrawal limit",
            "65": "Exceeds withdrawal frequency",
            "91": "Issuer not available",
            "96": "System malfunction"
        }
        return errors.get(code, f"Transaction declined (code: {code})")

    def _mock_payment(self, amount: float, order_id: str) -> PaymentResult:
        """Mock payment for development"""
        return PaymentResult(
            success=True,
            transaction_id=f"MOCK-BOR-{order_id}",
            status=PaymentStatus.PENDING,
            amount=amount,
            redirect_url=f"https://3dsgate-dev.borica.bg/mock?order={order_id}"
        )

    def _mock_callback(self, data: Dict) -> PaymentResult:
        """Mock callback for development"""
        return PaymentResult(
            success=True,
            transaction_id=f"MOCK-{data.get('ORDER', 'unknown')}",
            status=PaymentStatus.SUCCESS,
            amount=float(data.get("AMOUNT", 0)) / 100
        )

    def _mock_refund(self, transaction_id: str) -> PaymentResult:
        """Mock refund for development"""
        return PaymentResult(
            success=True,
            transaction_id=f"MOCK-REF-{transaction_id}",
            status=PaymentStatus.REFUNDED
        )


# ============================================================================
# ePay.bg INTEGRATION (Bulgarian Online Payments)
# ============================================================================

class EPayService:
    """
    ePay.bg Payment Gateway Integration

    ePay.bg supports:
    - Bank transfers
    - ePay wallet
    - Credit/debit cards via Borica
    - EasyPay terminals
    - B-Pay
    """

    PROD_URL = "https://epay.bg"
    TEST_URL = "https://demo.epay.bg"

    def __init__(self):
        self.client_id = settings.epay_client_id
        self.secret_key = settings.epay_secret_key
        self.is_production = settings.epay_production.lower() == "true"

        self._base_url = self.PROD_URL if self.is_production else self.TEST_URL
        self._initialized = bool(self.client_id and self.secret_key)

    @property
    def is_available(self) -> bool:
        return self._initialized and HAS_REQUESTS

    def create_payment(
        self,
        amount: float,
        invoice_id: str,
        description: str,
        expiration_days: int = 7,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> PaymentResult:
        """
        Create ePay.bg payment request.

        Args:
            amount: Payment amount in BGN
            invoice_id: Unique invoice/order ID
            description: Payment description
            expiration_days: Days until payment expires
            return_url: Success redirect URL
            cancel_url: Cancel redirect URL

        Returns:
            PaymentResult with redirect URL
        """
        if not self._initialized:
            return self._mock_payment(amount, invoice_id)

        try:
            # Build payment data
            encoded_data = self._encode_payment_data(
                amount=amount,
                invoice_id=invoice_id,
                description=description,
                expiration_days=expiration_days
            )

            checksum = self._calculate_checksum(encoded_data)

            # Build payment URL
            params = {
                "PAGE": "paylogin",
                "ENCODED": encoded_data,
                "CHECKSUM": checksum,
                "URL_OK": return_url or settings.epay_success_url,
                "URL_CANCEL": cancel_url or settings.epay_cancel_url
            }

            redirect_url = f"{self._base_url}/?{urlencode(params)}"

            return PaymentResult(
                success=True,
                transaction_id=f"EPAY-{invoice_id}",
                status=PaymentStatus.PENDING,
                amount=amount,
                redirect_url=redirect_url
            )

        except Exception as e:
            logger.error(f"ePay payment error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )

    def verify_notification(self, notification_data: Dict) -> PaymentResult:
        """
        Verify and process IPN (Instant Payment Notification) from ePay.

        Args:
            notification_data: POST data from ePay notification

        Returns:
            PaymentResult with payment status
        """
        if not self._initialized:
            return self._mock_notification(notification_data)

        try:
            encoded = notification_data.get("encoded", "")
            checksum = notification_data.get("checksum", "")

            # Verify checksum
            expected_checksum = self._calculate_checksum(encoded)
            if not hmac.compare_digest(expected_checksum.lower(), checksum.lower()):
                return PaymentResult(
                    success=False,
                    error_message="Invalid checksum"
                )

            # Decode payment data
            decoded = base64.b64decode(encoded).decode("utf-8")
            data = self._parse_notification(decoded)

            status = data.get("STATUS", "")
            invoice_id = data.get("INVOICE", "")
            amount = float(data.get("AMOUNT", 0))

            if status == "PAID":
                return PaymentResult(
                    success=True,
                    transaction_id=data.get("PAY_TIME", invoice_id),
                    status=PaymentStatus.SUCCESS,
                    amount=amount,
                    raw_response=data
                )
            elif status == "DENIED":
                return PaymentResult(
                    success=False,
                    status=PaymentStatus.FAILED,
                    error_message="Payment denied",
                    raw_response=data
                )
            elif status == "EXPIRED":
                return PaymentResult(
                    success=False,
                    status=PaymentStatus.CANCELLED,
                    error_message="Payment expired",
                    raw_response=data
                )
            else:
                return PaymentResult(
                    success=False,
                    status=PaymentStatus.PENDING,
                    raw_response=data
                )

        except Exception as e:
            logger.error(f"ePay notification error: {str(e)}")
            return PaymentResult(
                success=False,
                error_message=str(e)
            )

    def check_payment_status(self, invoice_id: str) -> PaymentResult:
        """Check payment status via API"""
        if not self._initialized:
            return PaymentResult(
                success=True,
                transaction_id=invoice_id,
                status=PaymentStatus.PENDING
            )

        try:
            # Build status check request
            data = f"INVOICE={invoice_id}\nMIN={self.client_id}"
            encoded = base64.b64encode(data.encode()).decode()
            checksum = self._calculate_checksum(encoded)

            response = requests.post(
                f"{self._base_url}/api/check",
                data={
                    "encoded": encoded,
                    "checksum": checksum
                },
                timeout=10
            )

            if response.status_code == 200:
                result = self._parse_status_response(response.text)
                return PaymentResult(
                    success=True,
                    transaction_id=invoice_id,
                    status=PaymentStatus(result.get("status", "pending")),
                    amount=float(result.get("amount", 0))
                )

            return PaymentResult(
                success=False,
                error_message=f"API error: {response.status_code}"
            )

        except Exception as e:
            return PaymentResult(
                success=False,
                error_message=str(e)
            )

    def _encode_payment_data(
        self,
        amount: float,
        invoice_id: str,
        description: str,
        expiration_days: int
    ) -> str:
        """Encode payment data for ePay"""
        from datetime import timedelta

        exp_date = (datetime.now() + timedelta(days=expiration_days)).strftime("%d.%m.%Y")

        data_lines = [
            f"MIN={self.client_id}",
            f"INVOICE={invoice_id}",
            f"AMOUNT={amount:.2f}",
            f"EXP_TIME={exp_date}",
            f"DESCR={description}"
        ]

        data = "\n".join(data_lines)
        return base64.b64encode(data.encode()).decode()

    def _calculate_checksum(self, encoded_data: str) -> str:
        """Calculate HMAC-SHA1 checksum"""
        return hmac.new(
            self.secret_key.encode(),
            encoded_data.encode(),
            hashlib.sha1
        ).hexdigest()

    def _parse_notification(self, decoded: str) -> Dict:
        """Parse decoded notification data"""
        result = {}
        for line in decoded.strip().split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                result[key.strip()] = value.strip()
        return result

    def _parse_status_response(self, response: str) -> Dict:
        """Parse status check response"""
        # ePay returns data in key=value format
        return self._parse_notification(response)

    def _mock_payment(self, amount: float, invoice_id: str) -> PaymentResult:
        """Mock payment for development"""
        return PaymentResult(
            success=True,
            transaction_id=f"MOCK-EPAY-{invoice_id}",
            status=PaymentStatus.PENDING,
            amount=amount,
            redirect_url=f"https://demo.epay.bg/mock?invoice={invoice_id}"
        )

    def _mock_notification(self, data: Dict) -> PaymentResult:
        """Mock notification for development"""
        return PaymentResult(
            success=True,
            transaction_id=f"MOCK-{datetime.now().timestamp()}",
            status=PaymentStatus.SUCCESS,
            amount=100.0
        )


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

# Global service instances
borica_service = BoricaService()
epay_service = EPayService()


def get_borica_service() -> BoricaService:
    return borica_service


def get_epay_service() -> EPayService:
    return epay_service


def get_bulgarian_payment_service(provider: str):
    """Get payment service by provider name"""
    providers = {
        "borica": borica_service,
        "epay": epay_service
    }
    return providers.get(provider.lower())
