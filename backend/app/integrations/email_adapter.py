import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import get_settings

logger = logging.getLogger(__name__)

class EmailAdapter:
    """Email integration adapter using SMTP."""

    def __init__(self):
        self.settings = get_settings()

    @property
    def is_live(self) -> bool:
        return bool(self.settings.SMTP_HOST and self.settings.SMTP_USER)

    def send_email(self, action) -> dict:
        """Send email notification."""
        recipients_json = action.recipients_json if hasattr(action, 'recipients_json') else "[]"
        recipients = json.loads(recipients_json) if isinstance(recipients_json, str) else recipients_json
        metadata_json = action.metadata_json if hasattr(action, 'metadata_json') else "{}"
        metadata = json.loads(metadata_json) if isinstance(metadata_json, str) else metadata_json

        template = metadata.get("template", "default")
        zoom_join_url = metadata.get("zoom_join_url")

        if not self.is_live:
            logger.info(f"[MOCK] Email sent to {recipients} using template '{template}'")
            return {"success": True, "mock": True, "recipients": recipients, "template": template}

        try:
            msg = MIMEMultipart()
            msg["From"] = self.settings.SMTP_USER
            msg["To"] = ", ".join(recipients)
            msg["Subject"] = f"[WarRoom] {action.title}"

            zoom_html = ""
            if zoom_join_url:
                zoom_html = f"""
                <p><strong>Zoom Join URL:</strong>
                  <a href="{zoom_join_url}">{zoom_join_url}</a>
                </p>
                """

            body = f"""
            <h2>Incident Alert: {action.title}</h2>
            <p>{action.description}</p>
            {zoom_html}
            <hr>
            <p><em>This is an automated message from WarRoom Agent.</em></p>
            """
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                server.starttls()
                server.login(self.settings.SMTP_USER, self.settings.SMTP_PASS)
                server.sendmail(self.settings.SMTP_USER, recipients, msg.as_string())

            return {"success": True, "recipients": recipients}
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return {"success": False, "error": str(e)}