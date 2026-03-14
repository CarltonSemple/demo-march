from __future__ import annotations

import os
from datetime import UTC, datetime

import requests

from .firebase import is_emulator_environment


def send_meeting_email(*, to_emails: list[str], title: str, starts_at: datetime, meet_link: str) -> dict:
    """Sends a meeting confirmation email.

    - In emulator: stub success
    - In production: requires MAILERSEND_API_KEY and MAIL_FROM_EMAIL
    """

    if is_emulator_environment():
        return {
            "provider": "stub",
            "sent": True,
            "to": to_emails,
        }

    api_key = (os.environ.get("MAILERSEND_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("MAILERSEND_API_KEY is required in production")

    from_email = (os.environ.get("MAIL_FROM_EMAIL") or "").strip()
    from_name = (os.environ.get("MAIL_FROM_NAME") or "Humm Coach App").strip()
    if not from_email:
        raise RuntimeError("MAIL_FROM_EMAIL is required in production")

    subject = f"Meeting scheduled: {title}"
    starts_text = starts_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
    text = (
        f"Your meeting is scheduled.\n\n"
        f"Title: {title}\n"
        f"When: {starts_text}\n"
        f"Link: {meet_link}\n"
    )

    body = {
        "from": {"email": from_email, "name": from_name},
        "to": [{"email": email} for email in to_emails],
        "subject": subject,
        "text": text,
    }

    resp = requests.post(
        "https://api.mailersend.com/v1/email",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=body,
        timeout=10,
    )

    if resp.status_code >= 300:
        raise RuntimeError(f"MailerSend error {resp.status_code}: {resp.text}")

    return {"provider": "mailersend", "sent": True}
