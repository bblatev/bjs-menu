"""Email & SMS Communication Service - for marketing, PO sending, and notifications."""

import smtplib
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from typing import Optional, List, Dict, Any
from jinja2 import Template

from app.core.config import settings


class EmailService:
    """Send emails for various purposes."""

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = int(str(settings.smtp_port))
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email
        self.from_name = settings.from_name

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send an email."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email

            if cc:
                msg["Cc"] = ", ".join(cc)

            # Add text part
            if body_text:
                msg.attach(MIMEText(body_text, "plain"))

            # Add HTML part
            msg.attach(MIMEText(body_html, "html"))

            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEApplication(
                        attachment["content"],
                        Name=attachment["filename"]
                    )
                    part["Content-Disposition"] = f'attachment; filename="{attachment["filename"]}"'
                    msg.attach(part)

            # Build recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Send email
            if self.smtp_user and self.smtp_password:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_email, recipients, msg.as_string())

                return {"success": True, "message": "Email sent successfully"}
            else:
                # Log email if SMTP not configured
                return {
                    "success": False,
                    "message": "SMTP not configured",
                    "would_send_to": to_email,
                    "subject": subject
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_purchase_order_email(
        self,
        supplier_email: str,
        supplier_name: str,
        order_details: Dict[str, Any],
        pdf_content: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Send purchase order to supplier."""
        subject = f"Purchase Order #{order_details.get('order_number', 'N/A')} from {self.from_name}"

        # Generate HTML body
        body_html = self._generate_po_email_html(supplier_name, order_details)

        attachments = []
        if pdf_content:
            attachments.append({
                "filename": f"PO_{order_details.get('order_number', 'order')}.pdf",
                "content": pdf_content
            })

        return self.send_email(
            to_email=supplier_email,
            subject=subject,
            body_html=body_html,
            attachments=attachments if attachments else None
        )

    def _generate_po_email_html(self, supplier_name: str, order_details: Dict[str, Any]) -> str:
        """Generate purchase order email HTML."""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .header { background: #2563eb; color: white; padding: 20px; }
                .content { padding: 20px; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background: #f5f5f5; }
                .total { font-weight: bold; font-size: 1.2em; }
                .footer { background: #f5f5f5; padding: 20px; font-size: 0.9em; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Purchase Order</h1>
            </div>
            <div class="content">
                <p>Dear {{ supplier_name }},</p>
                <p>Please find below our purchase order. We kindly request delivery as per our agreed terms.</p>

                <h3>Order Details</h3>
                <p><strong>Order Number:</strong> {{ order_number }}</p>
                <p><strong>Order Date:</strong> {{ order_date }}</p>
                <p><strong>Requested Delivery:</strong> {{ delivery_date }}</p>

                <table>
                    <tr>
                        <th>Item</th>
                        <th>SKU</th>
                        <th>Quantity</th>
                        <th>Unit</th>
                        <th>Unit Price</th>
                        <th>Total</th>
                    </tr>
                    {% for item in items %}
                    <tr>
                        <td>{{ item.name }}</td>
                        <td>{{ item.sku }}</td>
                        <td>{{ item.quantity }}</td>
                        <td>{{ item.unit }}</td>
                        <td>${{ "%.2f"|format(item.unit_price) }}</td>
                        <td>${{ "%.2f"|format(item.total) }}</td>
                    </tr>
                    {% endfor %}
                    <tr class="total">
                        <td colspan="5" style="text-align: right;">Total:</td>
                        <td>${{ "%.2f"|format(total) }}</td>
                    </tr>
                </table>

                <p><strong>Delivery Address:</strong><br>{{ delivery_address }}</p>

                {% if notes %}
                <p><strong>Notes:</strong><br>{{ notes }}</p>
                {% endif %}

                <p>Please confirm receipt of this order and expected delivery date.</p>
                <p>Thank you for your continued partnership.</p>
            </div>
            <div class="footer">
                <p>This is an automated message from V99 POS System.</p>
            </div>
        </body>
        </html>
        """

        jinja_template = Template(template)
        return jinja_template.render(
            supplier_name=supplier_name,
            **order_details
        )

    def send_marketing_email(
        self,
        to_email: str,
        campaign_name: str,
        subject: str,
        body_html: str,
        unsubscribe_link: str
    ) -> Dict[str, Any]:
        """Send marketing campaign email."""
        # Add unsubscribe footer
        footer = f"""
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666;">
            <p>You received this email because you're a valued customer.</p>
            <p><a href="{unsubscribe_link}">Unsubscribe</a> from marketing emails.</p>
        </div>
        """
        body_html = body_html + footer

        return self.send_email(
            to_email=to_email,
            subject=subject,
            body_html=body_html
        )


class SMSService:
    """Send SMS via Twilio for waitlist, reservations, and marketing."""

    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_from_number
        self.api_url = "https://api.twilio.com/2010-04-01"

    async def send_sms(
        self,
        to_number: str,
        message: str
    ) -> Dict[str, Any]:
        """Send an SMS message."""
        if not self.account_sid or not self.auth_token:
            return {
                "success": False,
                "message": "Twilio not configured",
                "would_send_to": to_number,
                "content": message
            }

        try:
            url = f"{self.api_url}/Accounts/{self.account_sid}/Messages.json"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data={
                        "To": to_number,
                        "From": self.from_number,
                        "Body": message
                    }
                )

                if response.status_code in [200, 201]:
                    data = response.json()
                    return {
                        "success": True,
                        "message_sid": data.get("sid"),
                        "status": data.get("status")
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_waitlist_confirmation(
        self,
        to_number: str,
        guest_name: str,
        position: int,
        estimated_wait: int,
        restaurant_name: str = "V99 Restaurant"
    ) -> Dict[str, Any]:
        """Send waitlist confirmation SMS."""
        message = (
            f"Hi {guest_name}! You're #{position} on the waitlist at {restaurant_name}. "
            f"Estimated wait: {estimated_wait} mins. We'll text when your table is ready. "
            f"Reply REMOVE to cancel."
        )
        return await self.send_sms(to_number, message)

    async def send_table_ready_notification(
        self,
        to_number: str,
        guest_name: str,
        restaurant_name: str = "V99 Restaurant"
    ) -> Dict[str, Any]:
        """Send table ready notification."""
        message = (
            f"Great news, {guest_name}! Your table at {restaurant_name} is ready. "
            f"Please check in with the host within 10 minutes."
        )
        return await self.send_sms(to_number, message)

    async def send_reservation_confirmation(
        self,
        to_number: str,
        guest_name: str,
        date_time: datetime,
        party_size: int,
        confirmation_code: str,
        restaurant_name: str = "V99 Restaurant"
    ) -> Dict[str, Any]:
        """Send reservation confirmation SMS."""
        formatted_date = date_time.strftime("%B %d at %I:%M %p")
        message = (
            f"Hi {guest_name}! Your reservation at {restaurant_name} is confirmed for "
            f"{formatted_date}, party of {party_size}. "
            f"Confirmation: {confirmation_code}. "
            f"Reply C to cancel or M to modify."
        )
        return await self.send_sms(to_number, message)

    async def send_reservation_reminder(
        self,
        to_number: str,
        guest_name: str,
        date_time: datetime,
        hours_until: int,
        restaurant_name: str = "V99 Restaurant"
    ) -> Dict[str, Any]:
        """Send reservation reminder SMS."""
        formatted_time = date_time.strftime("%I:%M %p")
        message = (
            f"Reminder: {guest_name}, your reservation at {restaurant_name} is "
            f"{'today' if hours_until < 24 else 'tomorrow'} at {formatted_time}. "
            f"See you soon! Reply C to cancel."
        )
        return await self.send_sms(to_number, message)

    async def send_marketing_sms(
        self,
        to_number: str,
        message: str,
        opt_out_text: str = "Reply STOP to unsubscribe"
    ) -> Dict[str, Any]:
        """Send marketing SMS with opt-out."""
        full_message = f"{message}\n\n{opt_out_text}"
        return await self.send_sms(to_number, full_message)


class NotificationService:
    """Unified notification service for all channels."""

    def __init__(self):
        self.email = EmailService()
        self.sms = SMSService()

    async def send_notification(
        self,
        notification_type: str,
        recipient: Dict[str, str],
        data: Dict[str, Any],
        channels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Send notification via specified channels."""
        if channels is None:
            channels = ["email", "sms"]

        results = {}

        if "email" in channels and recipient.get("email"):
            # Generate email content based on type
            email_result = await self._send_email_notification(
                notification_type, recipient["email"], data
            )
            results["email"] = email_result

        if "sms" in channels and recipient.get("phone"):
            sms_result = await self._send_sms_notification(
                notification_type, recipient["phone"], data
            )
            results["sms"] = sms_result

        return results

    async def _send_email_notification(
        self,
        notification_type: str,
        email: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email notification based on type."""
        templates = {
            "reservation_confirmed": {
                "subject": "Reservation Confirmed - {restaurant_name}",
                "body": "Your reservation is confirmed for {date_time}."
            },
            "order_ready": {
                "subject": "Your Order is Ready!",
                "body": "Order #{order_number} is ready for pickup."
            },
            "low_stock_alert": {
                "subject": "Low Stock Alert - {product_name}",
                "body": "Stock for {product_name} is low ({current_qty} remaining)."
            }
        }

        template = templates.get(notification_type, {})
        subject = template.get("subject", "Notification").format(**data)
        body = template.get("body", "").format(**data)

        return self.email.send_email(
            to_email=email,
            subject=subject,
            body_html=f"<p>{body}</p>"
        )

    async def _send_sms_notification(
        self,
        notification_type: str,
        phone: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send SMS notification based on type."""
        messages = {
            "reservation_confirmed": "Reservation confirmed for {date_time}. See you soon!",
            "table_ready": "Your table is ready! Please check in with the host.",
            "order_ready": "Order #{order_number} is ready for pickup!",
            "waitlist_update": "Update: You're now #{position} on the waitlist."
        }

        message = messages.get(notification_type, "Notification from V99").format(**data)
        return await self.sms.send_sms(phone, message)
