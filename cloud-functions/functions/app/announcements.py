from __future__ import annotations

from datetime import UTC, datetime

from firebase_functions import https_fn

from .firebase import ensure_firebase_initialized, get_db
from .http import cors_headers, cors_preflight_response, error_response, json_response


def validate_announcement_payload(payload: dict) -> tuple[dict | None, dict | None]:
    errors: dict[str, str] = {}

    group_id = payload.get("groupId") or payload.get("group_id")
    if not isinstance(group_id, str) or not group_id.strip():
        errors["groupId"] = "groupId is required"

    text = payload.get("text") or payload.get("message")
    if not isinstance(text, str) or not text.strip():
        errors["text"] = "text is required"
    elif len(text.strip()) > 1000:
        errors["text"] = "text must be <= 1000 characters"

    if errors:
        return None, errors

    return {"groupId": group_id.strip(), "text": text.strip()}, None


def handle_announcements(req: https_fn.Request) -> https_fn.Response:
    if req.method == "OPTIONS":
        return cors_preflight_response(origin="*")

    ensure_firebase_initialized()
    db = get_db()

    if req.method == "GET":
        args = getattr(req, "args", None)
        group_id = None
        if args is not None:
            group_id = args.get("groupId") or args.get("group_id")

        if not group_id or not str(group_id).strip():
            return error_response(
                status=400,
                code="missing_group_id",
                message="groupId is required",
                headers=cors_headers(),
            )

        query = (
            db.collection("groups")
            .document(str(group_id))
            .collection("announcements")
            .order_by("createdAt", direction="DESCENDING")
            .limit(50)
        )

        items: list[dict] = []
        for doc in query.stream():
            data = doc.to_dict() or {}
            data["id"] = doc.id
            created_at = data.get("createdAt")
            if hasattr(created_at, "isoformat"):
                data["createdAt"] = created_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            items.append(data)

        return json_response(
            {"groupId": str(group_id), "announcements": items},
            status=200,
            headers=cors_headers(),
        )

    if req.method == "POST":
        payload = req.get_json(silent=True, force=True) or {}
        cleaned, errors = validate_announcement_payload(payload)
        if errors:
            return error_response(
                status=400,
                code="validation_error",
                message="Invalid announcement payload",
                details=errors,
                headers=cors_headers(),
            )

        assert cleaned is not None
        group_id = cleaned["groupId"]

        now = datetime.now(tz=UTC)
        ref = db.collection("groups").document(group_id).collection("announcements").document()
        ref.set({"text": cleaned["text"], "createdAt": now})

        announcement = {
            "id": ref.id,
            "groupId": group_id,
            "text": cleaned["text"],
            "createdAt": now.isoformat().replace("+00:00", "Z"),
        }

        return json_response({"announcement": announcement}, status=201, headers=cors_headers())

    return error_response(
        status=405,
        code="method_not_allowed",
        message="Only GET and POST are supported",
        headers=cors_headers(),
    )
