"""Notification service for SMS and Email alerts."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import dataclass
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    success: bool
    channel: str  # "sms", "email", "push"
    recipient: str
    message: str
    error: Optional[str] = None
    sent_at: Optional[datetime] = None


class NotificationService:
    """Service for sending notifications via SMS, Email, and Push."""

    def __init__(
        self,
        sms_provider: str = "twilio",  # "twilio", "nexmo", "infobip", "local"
        sms_api_key: Optional[str] = None,
        sms_api_secret: Optional[str] = None,
        sms_from_number: Optional[str] = None,
        email_provider: str = "smtp",  # "smtp", "sendgrid", "mailgun"
        email_api_key: Optional[str] = None,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        email_from: Optional[str] = None,
    ):
        self.sms_provider = sms_provider
        self.sms_api_key = sms_api_key
        self.sms_api_secret = sms_api_secret
        self.sms_from_number = sms_from_number

        self.email_provider = email_provider
        self.email_api_key = email_api_key
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_from = email_from

        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def send_sms(
        self,
        to_numbers: List[str],
        message: str,
    ) -> List[NotificationResult]:
        """Send SMS to multiple recipients."""
        results = []

        for number in to_numbers:
            try:
                if self.sms_provider == "twilio":
                    result = await self._send_twilio_sms(number, message)
                elif self.sms_provider == "nexmo":
                    result = await self._send_nexmo_sms(number, message)
                elif self.sms_provider == "infobip":
                    result = await self._send_infobip_sms(number, message)
                else:
                    # Local/mock - just log
                    result = await self._send_mock_sms(number, message)

                results.append(result)

            except Exception as e:
                logger.error(f"SMS send error to {number}: {e}")
                results.append(NotificationResult(
                    success=False,
                    channel="sms",
                    recipient=number,
                    message=message,
                    error=str(e),
                ))

        return results

    async def _send_twilio_sms(self, to: str, message: str) -> NotificationResult:
        """Send SMS via Twilio."""
        if not self.sms_api_key or not self.sms_api_secret:
            return NotificationResult(
                success=False,
                channel="sms",
                recipient=to,
                message=message,
                error="Twilio credentials not configured",
            )

        client = await self._get_client()
        account_sid = self.sms_api_key
        auth_token = self.sms_api_secret

        try:
            response = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                auth=(account_sid, auth_token),
                data={
                    "To": to,
                    "From": self.sms_from_number,
                    "Body": message,
                },
            )

            if response.status_code in (200, 201):
                return NotificationResult(
                    success=True,
                    channel="sms",
                    recipient=to,
                    message=message,
                    sent_at=datetime.now(timezone.utc),
                )
            else:
                return NotificationResult(
                    success=False,
                    channel="sms",
                    recipient=to,
                    message=message,
                    error=f"Twilio error: {response.status_code} - {response.text}",
                )

        except Exception as e:
            return NotificationResult(
                success=False,
                channel="sms",
                recipient=to,
                message=message,
                error=str(e),
            )

    async def _send_nexmo_sms(self, to: str, message: str) -> NotificationResult:
        """Send SMS via Nexmo/Vonage."""
        if not self.sms_api_key or not self.sms_api_secret:
            return NotificationResult(
                success=False,
                channel="sms",
                recipient=to,
                message=message,
                error="Nexmo credentials not configured",
            )

        client = await self._get_client()

        try:
            response = await client.post(
                "https://rest.nexmo.com/sms/json",
                json={
                    "api_key": self.sms_api_key,
                    "api_secret": self.sms_api_secret,
                    "to": to,
                    "from": self.sms_from_number or "BJS Menu",
                    "text": message,
                },
            )

            data = response.json()
            if data.get("messages", [{}])[0].get("status") == "0":
                return NotificationResult(
                    success=True,
                    channel="sms",
                    recipient=to,
                    message=message,
                    sent_at=datetime.now(timezone.utc),
                )
            else:
                return NotificationResult(
                    success=False,
                    channel="sms",
                    recipient=to,
                    message=message,
                    error=f"Nexmo error: {data}",
                )

        except Exception as e:
            return NotificationResult(
                success=False,
                channel="sms",
                recipient=to,
                message=message,
                error=str(e),
            )

    async def _send_infobip_sms(self, to: str, message: str) -> NotificationResult:
        """Send SMS via Infobip (popular in Bulgaria)."""
        if not self.sms_api_key:
            return NotificationResult(
                success=False,
                channel="sms",
                recipient=to,
                message=message,
                error="Infobip API key not configured",
            )

        client = await self._get_client()

        try:
            response = await client.post(
                "https://api.infobip.com/sms/2/text/advanced",
                headers={
                    "Authorization": f"App {self.sms_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "messages": [{
                        "destinations": [{"to": to}],
                        "from": self.sms_from_number or "BJSMenu",
                        "text": message,
                    }]
                },
            )

            if response.status_code == 200:
                return NotificationResult(
                    success=True,
                    channel="sms",
                    recipient=to,
                    message=message,
                    sent_at=datetime.now(timezone.utc),
                )
            else:
                return NotificationResult(
                    success=False,
                    channel="sms",
                    recipient=to,
                    message=message,
                    error=f"Infobip error: {response.status_code}",
                )

        except Exception as e:
            return NotificationResult(
                success=False,
                channel="sms",
                recipient=to,
                message=message,
                error=str(e),
            )

    async def _send_mock_sms(self, to: str, message: str) -> NotificationResult:
        """Mock SMS for development - logs warning that no real SMS is sent."""
        logger.warning(
            f"[MOCK SMS] No SMS provider configured. Message NOT actually sent. "
            f"To: {to}, Message: {message}. "
            f"Configure a real SMS provider (twilio, nexmo, infobip) for production use."
        )
        return NotificationResult(
            success=True,
            channel="sms",
            recipient=to,
            message=message,
            sent_at=datetime.now(timezone.utc),
        )

    async def send_email(
        self,
        to_addresses: List[str],
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> List[NotificationResult]:
        """Send email to multiple recipients."""
        results = []

        for address in to_addresses:
            try:
                if self.email_provider == "sendgrid":
                    result = await self._send_sendgrid_email(address, subject, body, html_body)
                elif self.email_provider == "mailgun":
                    result = await self._send_mailgun_email(address, subject, body, html_body)
                else:
                    # SMTP or mock
                    result = await self._send_smtp_email(address, subject, body, html_body)

                results.append(result)

            except Exception as e:
                logger.error(f"Email send error to {address}: {e}")
                results.append(NotificationResult(
                    success=False,
                    channel="email",
                    recipient=address,
                    message=body,
                    error=str(e),
                ))

        return results

    async def _send_sendgrid_email(
        self, to: str, subject: str, body: str, html_body: Optional[str]
    ) -> NotificationResult:
        """Send email via SendGrid."""
        if not self.email_api_key:
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to,
                message=body,
                error="SendGrid API key not configured",
            )

        client = await self._get_client()

        try:
            content = [{"type": "text/plain", "value": body}]
            if html_body:
                content.append({"type": "text/html", "value": html_body})

            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {self.email_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to}]}],
                    "from": {"email": self.email_from or "alerts@bjsmenu.com"},
                    "subject": subject,
                    "content": content,
                },
            )

            if response.status_code in (200, 202):
                return NotificationResult(
                    success=True,
                    channel="email",
                    recipient=to,
                    message=body,
                    sent_at=datetime.now(timezone.utc),
                )
            else:
                return NotificationResult(
                    success=False,
                    channel="email",
                    recipient=to,
                    message=body,
                    error=f"SendGrid error: {response.status_code}",
                )

        except Exception as e:
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to,
                message=body,
                error=str(e),
            )

    async def _send_mailgun_email(
        self, to: str, subject: str, body: str, html_body: Optional[str]
    ) -> NotificationResult:
        """Send email via Mailgun."""
        if not self.email_api_key:
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to,
                message=body,
                error="Mailgun API key not configured",
            )

        client = await self._get_client()
        domain = self.email_from.split("@")[1] if self.email_from else "bjsmenu.com"

        try:
            data = {
                "from": self.email_from or f"alerts@{domain}",
                "to": to,
                "subject": subject,
                "text": body,
            }
            if html_body:
                data["html"] = html_body

            response = await client.post(
                f"https://api.mailgun.net/v3/{domain}/messages",
                auth=("api", self.email_api_key),
                data=data,
            )

            if response.status_code == 200:
                return NotificationResult(
                    success=True,
                    channel="email",
                    recipient=to,
                    message=body,
                    sent_at=datetime.now(timezone.utc),
                )
            else:
                return NotificationResult(
                    success=False,
                    channel="email",
                    recipient=to,
                    message=body,
                    error=f"Mailgun error: {response.status_code}",
                )

        except Exception as e:
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to,
                message=body,
                error=str(e),
            )

    async def _send_smtp_email(
        self, to: str, subject: str, body: str, html_body: Optional[str]
    ) -> NotificationResult:
        """Send email via SMTP (or mock if not configured)."""
        if not self.smtp_host:
            # Mock mode - no SMTP configured
            logger.warning(
                f"[MOCK EMAIL] No SMTP host configured. Email NOT actually sent. "
                f"To: {to}, Subject: {subject}. "
                f"Configure smtp_host or use sendgrid/mailgun for production use."
            )
            return NotificationResult(
                success=True,
                channel="email",
                recipient=to,
                message=body,
                sent_at=datetime.now(timezone.utc),
            )

        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_from or self.smtp_user
            msg["To"] = to

            msg.attach(MIMEText(body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))

            # Run SMTP in thread pool to not block
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_smtp_sync,
                to,
                msg.as_string(),
            )

            return NotificationResult(
                success=True,
                channel="email",
                recipient=to,
                message=body,
                sent_at=datetime.now(timezone.utc),
            )

        except Exception as e:
            return NotificationResult(
                success=False,
                channel="email",
                recipient=to,
                message=body,
                error=str(e),
            )

    def _send_smtp_sync(self, to: str, msg_string: str):
        """Synchronous SMTP send (called in thread pool)."""
        import smtplib

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            if self.smtp_user and self.smtp_password:
                server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.email_from or self.smtp_user, to, msg_string)

    async def send_manager_alert(
        self,
        alert_name: str,
        alert_type: str,
        message: str,
        phones: List[str],
        emails: List[str],
        send_sms: bool = True,
        send_email: bool = True,
        venue_name: str = "Restaurant",
    ) -> dict:
        """Send a manager alert via configured channels."""
        results = {
            "sms_results": [],
            "email_results": [],
            "total_sent": 0,
            "total_failed": 0,
        }

        # Prepare alert message
        timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        sms_message = f"[{venue_name}] {alert_name}: {message} ({timestamp})"
        email_subject = f"[{venue_name}] Alert: {alert_name}"
        email_body = f"""
Manager Alert

Type: {alert_type.upper()}
Alert: {alert_name}
Time: {timestamp}

Details:
{message}

---
This is an automated alert from BJS Menu POS System.
        """.strip()

        email_html = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <div style="background: #f97316; color: white; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
        <h2 style="margin: 0;">{alert_name}</h2>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">{venue_name} - {timestamp}</p>
    </div>
    <div style="background: #f3f4f6; padding: 15px; border-radius: 8px;">
        <p style="margin: 0; color: #374151;"><strong>Type:</strong> {alert_type.upper()}</p>
        <p style="margin: 10px 0 0 0; color: #374151;"><strong>Details:</strong></p>
        <p style="margin: 5px 0 0 0; color: #6b7280;">{message}</p>
    </div>
    <p style="color: #9ca3af; font-size: 12px; margin-top: 20px;">
        This is an automated alert from BJS Menu POS System.
    </p>
</body>
</html>
        """

        # Send SMS
        if send_sms and phones:
            sms_results = await self.send_sms(phones, sms_message)
            results["sms_results"] = [
                {"recipient": r.recipient, "success": r.success, "error": r.error}
                for r in sms_results
            ]
            results["total_sent"] += sum(1 for r in sms_results if r.success)
            results["total_failed"] += sum(1 for r in sms_results if not r.success)

        # Send Email
        if send_email and emails:
            email_results = await self.send_email(emails, email_subject, email_body, email_html)
            results["email_results"] = [
                {"recipient": r.recipient, "success": r.success, "error": r.error}
                for r in email_results
            ]
            results["total_sent"] += sum(1 for r in email_results if r.success)
            results["total_failed"] += sum(1 for r in email_results if not r.success)

        return results

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get or create the notification service singleton."""
    global _notification_service
    if _notification_service is None:
        # Load config from centralized settings
        _notification_service = NotificationService(
            sms_provider=settings.sms_provider,
            sms_api_key=settings.sms_api_key,
            sms_api_secret=settings.sms_api_secret,
            sms_from_number=settings.sms_from_number,
            email_provider=settings.email_provider,
            email_api_key=settings.email_api_key,
            smtp_host=settings.smtp_host,
            smtp_port=int(str(settings.smtp_port)),
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
            email_from=settings.email_from,
        )
    return _notification_service
