from __future__ import annotations

import re
from datetime import UTC, datetime

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def parse_starts_at(value) -> datetime | None:
    if isinstance(value, (int, float)):
        # epoch millis
        return datetime.fromtimestamp(float(value) / 1000.0, tz=UTC)

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    # Allow trailing Z
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None

    if dt.tzinfo is None:
        # Assume UTC if timezone not provided
        dt = dt.replace(tzinfo=UTC)

    return dt.astimezone(UTC)


def validate_meeting_payload(payload: dict) -> tuple[dict | None, dict | None]:
    """Returns (cleaned, errors)."""

    errors: dict[str, str] = {}

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        errors["title"] = "title is required"

    starts_at_raw = payload.get("dateTime") or payload.get("startsAt")
    starts_at = parse_starts_at(starts_at_raw)
    if starts_at is None:
        errors["dateTime"] = "dateTime must be an ISO-8601 string or epoch millis"

    meet_link = payload.get("meetLink") or payload.get("googleMeetLink")
    if not isinstance(meet_link, str) or not meet_link.strip():
        errors["meetLink"] = "meetLink is required"
    elif not meet_link.strip().startswith("https://meet.google.com/"):
        errors["meetLink"] = "meetLink must be a https://meet.google.com/ link"

    attendees = payload.get("attendees") or payload.get("attendeeEmails")
    if not isinstance(attendees, list) or not attendees:
        errors["attendees"] = "attendees must be a non-empty list of emails"
    else:
        clean_attendees: list[str] = []
        for i, item in enumerate(attendees):
            if not isinstance(item, str) or not item.strip() or not _EMAIL_RE.match(item.strip()):
                errors[f"attendees[{i}]"] = "must be a valid email"
            else:
                clean_attendees.append(item.strip().lower())
        attendees = clean_attendees

    if errors:
        return None, errors

    return {
        "title": title.strip(),
        "startsAt": starts_at,
        "meetLink": meet_link.strip(),
        "attendees": attendees,
    }, None
