from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime, timedelta

from firebase_admin import firestore
from firebase_functions import https_fn

from .email import send_meeting_email
from .firebase import ensure_firebase_initialized, get_db, is_emulator_environment
from .http import cors_headers, cors_preflight_response, error_response, json_response
from .meetings_validation import validate_meeting_payload

try:
    from google.api_core.exceptions import AlreadyExists  # type: ignore
except Exception:  # pragma: no cover
    AlreadyExists = None


_IDEMPOTENCY_SAFE_RE = re.compile(r"^[A-Za-z0-9_-]{1,120}$")


def _meeting_doc_id_for_idempotency_key(key: str) -> str:
    k = (key or "").strip()
    if _IDEMPOTENCY_SAFE_RE.match(k):
        return f"idem_{k}"
    h = hashlib.sha256(k.encode("utf-8")).hexdigest()
    return f"idem_{h}"


def _meeting_payload_from_doc(*, doc_id: str, group_id: str, data: dict) -> dict:
    starts_at = data.get("startsAt")
    if hasattr(starts_at, "isoformat"):
        starts_at = starts_at.astimezone(UTC).isoformat().replace("+00:00", "Z")

    return {
        "id": doc_id,
        "groupId": group_id,
        "title": data.get("title") or "",
        "startsAt": starts_at or "",
        "meetLink": data.get("meetLink") or "",
        "attendees": data.get("attendees") or [],
    }


def _get_group_id_from_args(req: https_fn.Request) -> str | None:
    args = getattr(req, "args", None)
    if args is None:
        return None
    group_id = args.get("groupId") or args.get("group_id")
    if not group_id or not str(group_id).strip():
        return None
    return str(group_id)


def _handle_get(*, req: https_fn.Request, db, group_id: str) -> https_fn.Response:
    now = datetime.now(tz=UTC)
    query = (
        db.collection("groups")
        .document(group_id)
        .collection("meetings")
        .where("startsAt", ">=", now)
        .order_by("startsAt")
        .limit(50)
    )

    items: list[dict] = []
    for doc in query.stream():
        data = doc.to_dict() or {}
        data["id"] = doc.id
        starts_at = data.get("startsAt")
        if hasattr(starts_at, "isoformat"):
            data["startsAt"] = starts_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
        items.append(data)

    return json_response(
        {"groupId": group_id, "meetings": items},
        status=200,
        headers=cors_headers(),
    )


def _handle_post(*, req: https_fn.Request, db, group_id: str) -> https_fn.Response:
    payload = req.get_json(silent=True, force=True) or {}

    idempotency_key = payload.get("idempotencyKey") or payload.get("idempotency_key")
    idempotency_key = idempotency_key if isinstance(idempotency_key, str) and idempotency_key.strip() else None

    cleaned, errors = validate_meeting_payload(payload)
    if errors:
        return error_response(
            status=400,
            code="validation_error",
            message="Invalid meeting payload",
            details=errors,
            headers=cors_headers(),
        )

    assert cleaned is not None
    starts_at: datetime = cleaned["startsAt"]

    # Simple guard: don't allow meetings in the past
    if starts_at < datetime.now(tz=UTC) - timedelta(minutes=1):
        return error_response(
            status=400,
            code="validation_error",
            message="dateTime must be in the future",
            headers=cors_headers(),
        )

    meetings_ref = db.collection("groups").document(group_id).collection("meetings")
    data_to_write = {
        "title": cleaned["title"],
        "startsAt": starts_at,
        "meetLink": cleaned["meetLink"],
        "attendees": cleaned["attendees"],
        "createdAt": firestore.SERVER_TIMESTAMP,
    }

    doc_ref = None
    if idempotency_key:
        doc_ref = meetings_ref.document(_meeting_doc_id_for_idempotency_key(idempotency_key))
        try:
            doc_ref.create(data_to_write)
        except Exception as exc:
            is_already_exists = (
                (AlreadyExists is not None and isinstance(exc, AlreadyExists))
                or exc.__class__.__name__ == "AlreadyExists"
            )
            if not is_already_exists:
                raise

            snap = doc_ref.get()
            data = snap.to_dict() if getattr(snap, "exists", False) else {}
            meeting = _meeting_payload_from_doc(doc_id=doc_ref.id, group_id=group_id, data=data or {})
            meeting["email"] = {"provider": "dedupe", "sent": True}
            return json_response({"meeting": meeting}, status=201, headers=cors_headers())
    else:
        doc_ref = meetings_ref.document()
        doc_ref.set(data_to_write)

    try:
        email_result = send_meeting_email(
            to_emails=cleaned["attendees"],
            title=cleaned["title"],
            starts_at=starts_at,
            meet_link=cleaned["meetLink"],
        )
    except Exception as exc:
        # Keep API semantics: only succeed if email succeeded.
        if not is_emulator_environment():
            doc_ref.delete()
        return error_response(
            status=500,
            code="email_send_failed",
            message=str(exc),
            headers=cors_headers(),
        )

    meeting = {
        "id": doc_ref.id,
        "groupId": group_id,
        "title": cleaned["title"],
        "startsAt": starts_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "meetLink": cleaned["meetLink"],
        "attendees": cleaned["attendees"],
        "email": email_result,
    }

    return json_response({"meeting": meeting}, status=201, headers=cors_headers())


def handle_meetings(req: https_fn.Request) -> https_fn.Response:
    # Basic CORS preflight handling
    if req.method == "OPTIONS":
        return cors_preflight_response(origin="*")

    ensure_firebase_initialized()
    db = get_db()

    if req.method == "GET":
        group_id = _get_group_id_from_args(req)
        if not group_id:
            return error_response(
                status=400,
                code="missing_group_id",
                message="groupId is required",
                headers=cors_headers(),
            )
        return _handle_get(req=req, db=db, group_id=group_id)

    if req.method == "POST":
        payload = req.get_json(silent=True, force=True) or {}
        group_id = payload.get("groupId") or payload.get("group_id")
        if not group_id or not str(group_id).strip():
            return error_response(
                status=400,
                code="missing_group_id",
                message="groupId is required",
                headers=cors_headers(),
            )

        return _handle_post(req=req, db=db, group_id=str(group_id))

    return error_response(
        status=405,
        code="method_not_allowed",
        message="Only GET and POST are supported",
        headers=cors_headers(),
    )
