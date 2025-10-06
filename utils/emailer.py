import os
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

RESEND_API_BASE = "https://api.resend.com"


def send_email(to: str, subject: str, html: str, *, from_email: Optional[str] = None) -> bool:
    """
    Send an email via Resend API.

    Env vars required:
      - RESEND_API_KEY: Your Resend API key
      - RESEND_FROM_EMAIL (optional): Default From email address
    """
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY not set; skipping email send to %s", to)
        return False

    sender = from_email or os.getenv("RESEND_FROM_EMAIL", "noreply@traliq.local")

    try:
        resp = requests.post(
            f"{RESEND_API_BASE}/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": sender,
                "to": to,
                "subject": subject,
                "html": html,
            },
            timeout=15,
        )
        if resp.status_code not in (200, 201):
            logger.error("Resend email failed (%s): %s", resp.status_code, resp.text)
            return False
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        logger.info("Resend email queued: %s", data)
        return True
    except Exception as e:
        logger.error("Resend email exception: %s", e)
        return False
