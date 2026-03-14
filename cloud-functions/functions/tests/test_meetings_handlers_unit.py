import json
from datetime import UTC, datetime, timedelta

import pytest

from app import meetings as meetings_mod


def _resp_json(resp):
    return json.loads(resp.get_data(as_text=True))


class _Req:
    def __init__(self, *, method: str, args=None, json_body=None):
        self.method = method
        self.args = args
        self._json_body = json_body

    def get_json(self, silent=True, force=True):
        return self._json_body


class _FakeDoc:
    def __init__(self, doc_id: str, data: dict):
        self.id = doc_id
        self._data = data

    def to_dict(self):
        return dict(self._data)


class _FakeMeetingDocRef:
    def __init__(self, doc_id: str):
        self.id = doc_id
        self.set_calls = []
        self.deleted = False

    def set(self, data: dict, *args, **kwargs):
        self.set_calls.append(data)

    def delete(self):
        self.deleted = True


class _FakeMeetingsQuery:
    def __init__(self, docs):
        self._docs = docs

    def where(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def stream(self):
        return list(self._docs)


class _FakeMeetingsCollection:
    def __init__(self, *, docs_for_query, new_doc_ref: _FakeMeetingDocRef):
        self._docs_for_query = docs_for_query
        self._new_doc_ref = new_doc_ref

    def where(self, *args, **kwargs):
        return _FakeMeetingsQuery(self._docs_for_query)

    def document(self, *args, **kwargs):
        # Called without args to create a new meeting doc.
        return self._new_doc_ref


class _FakeGroupDoc:
    def __init__(self, meetings_collection: _FakeMeetingsCollection):
        self._meetings_collection = meetings_collection

    def collection(self, name: str):
        assert name == "meetings"
        return self._meetings_collection


class _FakeGroupsCollection:
    def __init__(self, group_doc: _FakeGroupDoc):
        self._group_doc = group_doc

    def document(self, group_id: str):
        # group_id already validated upstream
        return self._group_doc


class _FakeDB:
    def __init__(self, groups_collection: _FakeGroupsCollection):
        self._groups_collection = groups_collection

    def collection(self, name: str):
        assert name == "groups"
        return self._groups_collection


def test_get_group_id_from_args_missing_or_blank():
    assert meetings_mod._get_group_id_from_args(_Req(method="GET", args=None)) is None
    assert meetings_mod._get_group_id_from_args(_Req(method="GET", args={"groupId": ""})) is None
    assert meetings_mod._get_group_id_from_args(_Req(method="GET", args={"group_id": "   "})) is None


def test_get_group_id_from_args_accepts_groupId_and_group_id():
    assert meetings_mod._get_group_id_from_args(_Req(method="GET", args={"groupId": "abc"})) == "abc"
    assert meetings_mod._get_group_id_from_args(_Req(method="GET", args={"group_id": "xyz"})) == "xyz"


def test_handle_get_normalizes_startsAt_to_iso_z():
    starts_at = datetime(2030, 1, 1, 12, 30, tzinfo=UTC)
    docs = [
        _FakeDoc("m1", {"title": "A", "startsAt": starts_at, "meetLink": "x"}),
        _FakeDoc("m2", {"title": "B", "startsAt": starts_at + timedelta(hours=1), "meetLink": "y"}),
    ]

    resp = meetings_mod._handle_get(req=_Req(method="GET"), db=_FakeDB(_FakeGroupsCollection(_FakeGroupDoc(_FakeMeetingsCollection(docs_for_query=docs, new_doc_ref=_FakeMeetingDocRef("new"))))), group_id="g1")

    assert resp.status_code == 200
    body = _resp_json(resp)
    assert body["groupId"] == "g1"
    assert [m["id"] for m in body["meetings"]] == ["m1", "m2"]
    assert body["meetings"][0]["startsAt"].endswith("Z")


def test_handle_post_success_sets_doc_and_returns_201(monkeypatch):
    new_doc = _FakeMeetingDocRef("new-meeting")
    db = _FakeDB(_FakeGroupsCollection(_FakeGroupDoc(_FakeMeetingsCollection(docs_for_query=[], new_doc_ref=new_doc))))

    monkeypatch.setattr(meetings_mod, "send_meeting_email", lambda **kwargs: {"provider": "stub", "sent": True})

    payload = {
        "title": "Weekly",
        "dateTime": "2035-01-01T12:30:00Z",
        "meetLink": "https://meet.google.com/abc-defg-hij",
        "attendees": ["a@example.com"],
    }

    resp = meetings_mod._handle_post(req=_Req(method="POST", json_body=payload), db=db, group_id="g1")

    assert resp.status_code == 201
    body = _resp_json(resp)
    assert body["meeting"]["id"] == "new-meeting"
    assert body["meeting"]["groupId"] == "g1"
    assert body["meeting"]["email"]["provider"] == "stub"

    assert len(new_doc.set_calls) == 1
    assert new_doc.set_calls[0]["title"] == "Weekly"


@pytest.mark.parametrize("emulator", [True, False])
def test_handle_post_email_failure_rolls_back_only_outside_emulator(monkeypatch, emulator):
    new_doc = _FakeMeetingDocRef("new-meeting")
    db = _FakeDB(_FakeGroupsCollection(_FakeGroupDoc(_FakeMeetingsCollection(docs_for_query=[], new_doc_ref=new_doc))))

    def _boom(**kwargs):
        raise RuntimeError("mailer down")

    monkeypatch.setattr(meetings_mod, "send_meeting_email", _boom)
    monkeypatch.setattr(meetings_mod, "is_emulator_environment", lambda: emulator)

    payload = {
        "title": "Weekly",
        "dateTime": "2035-01-01T12:30:00Z",
        "meetLink": "https://meet.google.com/abc-defg-hij",
        "attendees": ["a@example.com"],
    }

    resp = meetings_mod._handle_post(req=_Req(method="POST", json_body=payload), db=db, group_id="g1")

    assert resp.status_code == 500
    body = _resp_json(resp)
    assert body["error"] == "email_send_failed"

    assert new_doc.deleted is (not emulator)
