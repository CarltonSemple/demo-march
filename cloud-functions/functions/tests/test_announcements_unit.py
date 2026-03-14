import pytest

from app.announcements import validate_announcement_payload


def test_validate_announcement_payload_happy_path():
    cleaned, errors = validate_announcement_payload({"groupId": " g1 ", "text": " hello "})
    assert errors is None
    assert cleaned == {"groupId": "g1", "text": "hello"}


@pytest.mark.parametrize(
    "payload,field",
    [
        ({}, "groupId"),
        ({"groupId": "g1"}, "text"),
        ({"text": "hi"}, "groupId"),
        ({"groupId": " ", "text": "hi"}, "groupId"),
        ({"groupId": "g1", "text": " "}, "text"),
    ],
)
def test_validate_announcement_payload_missing(payload, field):
    cleaned, errors = validate_announcement_payload(payload)
    assert cleaned is None
    assert errors is not None
    assert field in errors


def test_validate_announcement_payload_limits_text_length():
    cleaned, errors = validate_announcement_payload({"groupId": "g1", "text": "x" * 1001})
    assert cleaned is None
    assert errors is not None
    assert "text" in errors
