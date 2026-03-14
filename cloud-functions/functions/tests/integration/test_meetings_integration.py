import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests


def _base_url() -> str:
    explicit = os.environ.get("BASE_URL")
    if explicit:
        return explicit.rstrip("/")

    project_id = (
        os.environ.get("FIREBASE_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or "coach-app-demo-3132026"
    )
    region = os.environ.get("FUNCTION_REGION") or "us-central1"
    return f"http://127.0.0.1:5001/{project_id}/{region}"


@pytest.mark.integration
def test_meetings_create_then_list():
    group_id = f"test-group-{uuid.uuid4()}"
    starts_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")

    payload = {
        "groupId": group_id,
        "title": "Integration Meeting",
        "dateTime": starts_at,
        "meetLink": "https://meet.google.com/abc-defg-hij",
        "attendees": ["a@example.com"],
    }

    create_url = f"{_base_url()}/meetings"

    try:
        resp = requests.post(create_url, json=payload, timeout=5)
    except requests.exceptions.RequestException as exc:
        pytest.skip(f"Functions emulator not reachable at {create_url}: {exc}")

    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}, body: {resp.text}"
    body = resp.json()
    meeting = body.get("meeting")
    assert meeting and meeting.get("id")
    assert meeting.get("groupId") == group_id
    assert meeting.get("title") == payload["title"]

    list_url = f"{_base_url()}/meetings?groupId={group_id}"
    resp2 = requests.get(list_url, timeout=5)
    assert resp2.status_code == 200
    data2 = resp2.json()
    meetings = data2.get("meetings") or []
    ids = [m.get("id") for m in meetings]
    assert meeting["id"] in ids
