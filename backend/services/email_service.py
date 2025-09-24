"""
Lightweight SMTP email service for notifications.

Uses standard library smtplib to avoid new runtime deps.
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import config
from services.logging_config import get_logger


logger = get_logger(__name__)


class EmailService:
    def __init__(self) -> None:
        self.smtp_host = config.SMTP_HOST
        self.smtp_port = config.SMTP_PORT
        self.smtp_user = config.SMTP_USER
        self.smtp_pass = config.SMTP_PASSWORD
        self.from_address = config.EMAIL_FROM
        self.use_tls = config.SMTP_USE_TLS
        self.use_ssl = config.SMTP_USE_SSL

    def _build_message(self, to_address: str, subject: str, text_body: str, html_body: Optional[str] = None) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = self.from_address
        message["To"] = to_address
        message.attach(MIMEText(text_body, "plain"))
        if html_body:
            message.attach(MIMEText(html_body, "html"))
        return message

    def send_email(self, to_address: str, subject: str, text_body: str, html_body: Optional[str] = None) -> bool:
        if not to_address:
            logger.info("✉️ EmailService: Missing recipient address; skipping send")
            return False
        if not self.smtp_host:
            logger.warning("✉️ EmailService: SMTP host not configured; skipping send")
            return False

        try:
            message = self._build_message(to_address, subject, text_body, html_body)

            # SSL or STARTTLS
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    if self.smtp_user and self.smtp_pass:
                        server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.from_address, [to_address], message.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls(context=ssl.create_default_context())
                    if self.smtp_user and self.smtp_pass:
                        server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.from_address, [to_address], message.as_string())

            logger.info(f"✉️ EmailService: Sent email to {to_address} with subject '{subject}'")
            return True
        except Exception as exc:
            logger.error(f"✉️ EmailService: Failed to send email to {to_address}: {exc}")
            return False


email_service = EmailService()


