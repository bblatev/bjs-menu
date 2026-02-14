"""
Email Service for BJ's Bar System
Handles sending email alerts and notifications
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending notifications"""
    
    def __init__(self, smtp_host: str = None, smtp_port: int = 587):
        self.smtp_host = smtp_host or "localhost"
        self.smtp_port = smtp_port
        self.configured = False
        
    def configure(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        use_tls: bool = True,
        from_email: str = "noreply@bjs-bar.com"
    ) -> None:
        """Configure SMTP settings"""
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_email = from_email
        self.configured = True
        logger.info(f"Email service configured for {smtp_host}")
    
    def send(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        attachments: Optional[List[dict]] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            attachments: Optional list of attachments
            
        Returns:
            True if sent successfully
        """
        if not self.configured:
            logger.warning(f"Email not configured, would send to {to}: {subject}")
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to
            
            # Add plain text part
            part1 = MIMEText(body, 'plain')
            msg.attach(part1)
            
            # Add HTML part if provided
            if html_body:
                part2 = MIMEText(html_body, 'html')
                msg.attach(part2)
            
            # Connect and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.username, self.password)
                server.sendmail(self.from_email, to, msg.as_string())
            
            logger.info(f"Email sent to {to}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to}: {e}")
            return False


# Global email service instance
_email_service = EmailService()


def configure_email(
    smtp_host: str,
    smtp_port: int,
    username: str,
    password: str,
    use_tls: bool = True,
    from_email: str = "noreply@bjs-bar.com"
) -> None:
    """Configure the global email service"""
    _email_service.configure(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        username=username,
        password=password,
        use_tls=use_tls,
        from_email=from_email
    )


def send_email(
    to: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    attachments: Optional[List[dict]] = None
) -> bool:
    """Send an email using the global service"""
    return _email_service.send(
        to=to,
        subject=subject,
        body=body,
        html_body=html_body,
        attachments=attachments
    )


def send_alert_email(
    to: str,
    subject: str,
    body: str,
    priority: str = "normal"
) -> bool:
    """
    Send an alert email
    
    Args:
        to: Recipient email
        subject: Alert subject
        body: Alert message
        priority: Alert priority (low, normal, high, critical)
    """
    # Add priority prefix to subject
    priority_prefix = {
        "critical": "🔴 CRITICAL: ",
        "high": "🟠 HIGH: ",
        "normal": "",
        "low": "🟢 "
    }
    
    full_subject = f"{priority_prefix.get(priority, '')}{subject}"
    
    # Create HTML body with styling
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            .alert {{ padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .critical {{ background-color: #fee; border-left: 4px solid #f00; }}
            .high {{ background-color: #fff3e0; border-left: 4px solid #ff9800; }}
            .normal {{ background-color: #e3f2fd; border-left: 4px solid #2196f3; }}
            .low {{ background-color: #e8f5e9; border-left: 4px solid #4caf50; }}
            .timestamp {{ color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="alert {priority}">
            <h2>{subject}</h2>
            <p>{body.replace(chr(10), '<br>')}</p>
            <p class="timestamp">Sent at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <p style="color: #666; font-size: 11px;">
            BJ's Bar Borovets Alert System<br>
            This is an automated message. Please do not reply.
        </p>
    </body>
    </html>
    """
    
    return send_email(
        to=to,
        subject=full_subject,
        body=body,
        html_body=html_body
    )


def send_daily_report(
    to: str,
    report_data: dict
) -> bool:
    """Send daily business report"""
    subject = f"📊 Daily Report - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    
    body = f"""
Daily Report for BJ's Bar Borovets

Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

Revenue: €{report_data.get('revenue', 0):,.2f}
Orders: {report_data.get('order_count', 0)}
Average Order: €{report_data.get('avg_order', 0):,.2f}

Top Items:
{chr(10).join(f"- {item}" for item in report_data.get('top_items', []))}

This is an automated daily report.
"""
    
    return send_email(to=to, subject=subject, body=body)


def send_low_stock_alert(
    to: str,
    items: List[dict]
) -> bool:
    """Send low stock alert"""
    subject = f"⚠️ Low Stock Alert - {len(items)} items"
    
    body = f"""
Low Stock Alert

The following items are running low:

{chr(10).join(f"- {item['name']}: {item['quantity']} {item['unit']} remaining (threshold: {item['threshold']})" for item in items)}

Please reorder these items soon.
"""
    
    return send_alert_email(to=to, subject=subject, body=body, priority="high")


def send_expiry_alert(
    to: str,
    items: List[dict]
) -> bool:
    """Send expiry date alert"""
    subject = f"🗓️ Expiry Alert - {len(items)} items expiring"
    
    body = f"""
Expiry Alert

The following items are expiring soon:

{chr(10).join(f"- {item['name']}: expires {item['expiry_date']}" for item in items)}

Please use or dispose of these items appropriately.
"""
    
    return send_alert_email(to=to, subject=subject, body=body, priority="high")
