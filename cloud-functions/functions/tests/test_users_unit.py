import json

import pytest

from app import users as users_mod


def _resp_json(resp):
    return json.loads(resp.get_data(as_text=True))


class _Req:
    def __init__(self, *, method: str, headers=None, json_body=None):
        self.method = method
        self.headers = headers or {}
        self._json_body = json_body

    def get_json(self, silent=True, force=True):
        return self._json_body


class _FakeDocRef:
    def __init__(self, doc_id: str):
        self.id = doc_id
        self.set_calls = []

    def set(self, data: dict, merge=False):
        self.set_calls.append({"data": data, "merge": merge})


class _FakeUsersCollection:
    def __init__(self, doc_ref: _FakeDocRef):
        self._doc_ref = doc_ref
        self.requested_ids = []

    def document(self, user_id: str):
        self.requested_ids.append(user_id)
        return self._doc_ref


class _FakeDB:
    def __init__(self, users_collection: _FakeUsersCollection):
        self._users_collection = users_collection

    def collection(self, name: str):
        assert name == "users"
        return self._users_collection


def test_validate_user_payload_requires_id_and_email():
    cleaned, errors = users_mod.validate_user_payload({})
    assert cleaned is None
    assert errors is not None
    assert "id" in errors
    assert "email" in errors
    assert "role" in errors


def test_handle_post_requires_admin_key_outside_emulator(monkeypatch):
    monkeypatch.setattr(users_mod, "is_emulator_environment", lambda: False)
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    db = _FakeDB(_FakeUsersCollection(_FakeDocRef("u")))
    resp = users_mod._handle_post(
        req=_Req(method="POST", json_body={"id": "u1", "email": "a@b.com", "role": "coach"}),
        db=db,
    )

    assert resp.status_code == 500
    body = _resp_json(resp)
    assert body["error"] == "admin_key_not_configured"


def test_handle_post_rejects_bad_or_missing_key_when_configured(monkeypatch):
    monkeypatch.setattr(users_mod, "is_emulator_environment", lambda: False)
    monkeypatch.setenv("ADMIN_API_KEY", "secret")

    db = _FakeDB(_FakeUsersCollection(_FakeDocRef("u")))

    resp_missing = users_mod._handle_post(
        req=_Req(method="POST", headers={}, json_body={"id": "u1", "email": "a@b.com", "role": "coach"}),
        db=db,
    )
    assert resp_missing.status_code == 401

    resp_bad = users_mod._handle_post(
        req=_Req(method="POST", headers={"X-Admin-Key": "nope"}, json_body={"id": "u1", "email": "a@b.com", "role": "coach"}),
        db=db,
    )
    assert resp_bad.status_code == 401


def test_handle_post_upserts_user_doc_in_emulator(monkeypatch):
    monkeypatch.setattr(users_mod, "is_emulator_environment", lambda: True)
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    doc_ref = _FakeDocRef("u1")
    db = _FakeDB(_FakeUsersCollection(doc_ref))

    resp = users_mod._handle_post(
        req=_Req(
            method="POST",
            json_body={
                "id": "u1",
                "email": "COACH@EXAMPLE.COM",
                "role": "coach",
                "displayName": " Coach ",
                "phone": "+1555",
            },
        ),
        db=db,
    )

    assert resp.status_code == 200
    body = _resp_json(resp)
    assert body["user"]["id"] == "u1"
    assert body["user"]["email"] == "coach@example.com"
    assert body["user"]["role"] == "coach"

    assert len(doc_ref.set_calls) == 1
    assert doc_ref.set_calls[0]["merge"] is True
    assert doc_ref.set_calls[0]["data"]["email"] == "coach@example.com"
    assert doc_ref.set_calls[0]["data"]["role"] == "coach"


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE"])
def test_handle_create_user_rejects_non_post(method):
    resp = users_mod.handle_create_user(_Req(method=method))
    assert resp.status_code == 405
