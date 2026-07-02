import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def send_email_alert(config: dict, subject: str, body: str) -> bool:
    email_cfg = config.get("email", {})

    sender = email_cfg.get("sender")
    password = email_cfg.get("password")
    recipient = email_cfg.get("recipient", sender)

    if not sender or not password:
        logger.warning("Email not configured (set EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT env vars)")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = recipient
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(email_cfg.get("smtp_host", "smtp.gmail.com"),
                          email_cfg.get("smtp_port", 587)) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        logger.info("Alert email sent to %s", recipient)
        return True
    except Exception as e:
        logger.error("Failed to send alert email: %s", e)
        return False
