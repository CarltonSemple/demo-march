from datetime import UTC, datetime

import pytest

from app.meetings_validation import parse_starts_at, validate_meeting_payload


def test_parse_starts_at_accepts_iso_z():
    dt = parse_starts_at("2030-01-01T12:30:00Z")
    assert dt is not None
    assert dt.tzinfo is not None
    assert dt.astimezone(UTC).isoformat().startswith("2030-01-01T12:30:00")


def test_parse_starts_at_accepts_epoch_millis():
    dt = parse_starts_at(1893510600000)  # 2030-01-01T12:30:00Z
    assert dt is not None
    assert dt.tzinfo is not None


def test_validate_meeting_payload_happy_path():
    cleaned, errors = validate_meeting_payload(
        {
            "title": "Weekly Check-in",
            "dateTime": "2030-01-01T12:30:00Z",
            "meetLink": "https://meet.google.com/abc-defg-hij",
            "attendees": ["a@example.com", "B@EXAMPLE.com"],
        }
    )
    assert errors is None
    assert cleaned is not None
    assert cleaned["title"] == "Weekly Check-in"
    assert cleaned["meetLink"].startswith("https://meet.google.com/")
    assert cleaned["attendees"] == ["a@example.com", "b@example.com"]


@pytest.mark.parametrize(
    "payload,missing_key",
    [
        ({}, "title"),
        ({"title": "x"}, "dateTime"),
        ({"title": "x", "dateTime": "2030-01-01T12:30:00Z"}, "meetLink"),
        (
            {
                "title": "x",
                "dateTime": "2030-01-01T12:30:00Z",
                "meetLink": "https://meet.google.com/abc-defg-hij",
            },
            "attendees",
        ),
    ],
)
def test_validate_meeting_payload_missing_fields(payload, missing_key):
    cleaned, errors = validate_meeting_payload(payload)
    assert cleaned is None
    assert errors is not None
    assert missing_key in errors


def test_validate_meeting_payload_rejects_non_google_meet_link():
    cleaned, errors = validate_meeting_payload(
        {
            "title": "x",
            "dateTime": "2030-01-01T12:30:00Z",
            "meetLink": "https://zoom.us/j/123",
            "attendees": ["a@example.com"],
        }
    )
    assert cleaned is None
    assert errors is not None
    assert "meetLink" in errors
