from datetime import UTC, datetime

import pytest

from app.email import send_meeting_email


def test_send_meeting_email_stubs_in_emulator(monkeypatch):
    monkeypatch.setattr("app.email.is_emulator_environment", lambda: True)

    result = send_meeting_email(
        to_emails=["a@example.com"],
        title="Weekly",
        starts_at=datetime(2035, 1, 1, 12, 30, tzinfo=UTC),
        meet_link="https://meet.google.com/abc-defg-hij",
    )

    assert result["provider"] == "stub"
    assert result["sent"] is True
    assert result["to"] == ["a@example.com"]


def test_send_meeting_email_requires_api_key_in_production(monkeypatch):
    monkeypatch.setattr("app.email.is_emulator_environment", lambda: False)
    monkeypatch.delenv("MAILERSEND_API_KEY", raising=False)
    monkeypatch.setenv("MAIL_FROM_EMAIL", "from@example.com")

    with pytest.raises(RuntimeError, match="MAILERSEND_API_KEY is required"):
        send_meeting_email(
            to_emails=["a@example.com"],
            title="Weekly",
            starts_at=datetime(2035, 1, 1, 12, 30, tzinfo=UTC),
            meet_link="https://meet.google.com/abc-defg-hij",
        )


def test_send_meeting_email_requires_from_email_in_production(monkeypatch):
    monkeypatch.setattr("app.email.is_emulator_environment", lambda: False)
    monkeypatch.setenv("MAILERSEND_API_KEY", "test-key")
    monkeypatch.delenv("MAIL_FROM_EMAIL", raising=False)

    with pytest.raises(RuntimeError, match="MAIL_FROM_EMAIL is required"):
        send_meeting_email(
            to_emails=["a@example.com"],
            title="Weekly",
            starts_at=datetime(2035, 1, 1, 12, 30, tzinfo=UTC),
            meet_link="https://meet.google.com/abc-defg-hij",
        )


def test_send_meeting_email_posts_to_mailersend_success(monkeypatch):
    monkeypatch.setattr("app.email.is_emulator_environment", lambda: False)
    monkeypatch.setenv("MAILERSEND_API_KEY", "test-key")
    monkeypatch.setenv("MAIL_FROM_EMAIL", "from@example.com")
    monkeypatch.setenv("MAIL_FROM_NAME", "Coach")

    captured = {}

    class _Resp:
        status_code = 202
        text = ""

    def _fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _Resp()

    monkeypatch.setattr("app.email.requests.post", _fake_post)

    result = send_meeting_email(
        to_emails=["a@example.com", "b@example.com"],
        title="Weekly",
        starts_at=datetime(2035, 1, 1, 12, 30, tzinfo=UTC),
        meet_link="https://meet.google.com/abc-defg-hij",
    )

    assert result == {"provider": "mailersend", "sent": True}

    assert captured["url"] == "https://api.mailersend.com/v1/email"
    assert captured["headers"]["Authorization"].startswith("Bearer ")
    assert captured["json"]["from"]["email"] == "from@example.com"
    assert captured["json"]["from"]["name"] == "Coach"
    assert captured["json"]["to"] == [{"email": "a@example.com"}, {"email": "b@example.com"}]
    assert captured["json"]["subject"] == "Meeting scheduled: Weekly"
    assert "https://meet.google.com/abc-defg-hij" in captured["json"]["text"]
    assert captured["timeout"] == 10


def test_send_meeting_email_raises_on_non_2xx(monkeypatch):
    monkeypatch.setattr("app.email.is_emulator_environment", lambda: False)
    monkeypatch.setenv("MAILERSEND_API_KEY", "test-key")
    monkeypatch.setenv("MAIL_FROM_EMAIL", "from@example.com")

    class _Resp:
        status_code = 400
        text = "bad request"

    monkeypatch.setattr("app.email.requests.post", lambda *a, **k: _Resp())

    with pytest.raises(RuntimeError, match=r"MailerSend error 400"):
        send_meeting_email(
            to_emails=["a@example.com"],
            title="Weekly",
            starts_at=datetime(2035, 1, 1, 12, 30, tzinfo=UTC),
            meet_link="https://meet.google.com/abc-defg-hij",
        )
