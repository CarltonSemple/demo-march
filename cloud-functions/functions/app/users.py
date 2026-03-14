from __future__ import annotations

import hmac
import os

from datetime import UTC, datetime

from firebase_functions import https_fn

from .firebase import ensure_firebase_initialized, get_db, is_emulator_environment
from .http import cors_headers, cors_preflight_response, error_response, json_response


_ALLOWED_ROLES = {"coach", "member"}


def _get_admin_api_key() -> str:
    return (os.environ.get("ADMIN_API_KEY") or "").strip()


def _is_authorized(req: https_fn.Request) -> tuple[bool, https_fn.Response | None]:
    required = _get_admin_api_key()

    if not required:
        if is_emulator_environment():
            return True, None
        return False, error_response(
            status=500,
            code="admin_key_not_configured",
            message="ADMIN_API_KEY must be set for admin endpoints in non-emulator environments",
            headers=cors_headers(),
        )

    provided = (
        req.headers.get("x-admin-key")
        or req.headers.get("X-Admin-Key")
        or req.headers.get("x-admin-api-key")
        or req.headers.get("X-Admin-Api-Key")
        or ""
    ).strip()

    if not provided or not hmac.compare_digest(provided, required):
        return False, error_response(
            status=401,
            code="unauthorized",
            message="Missing or invalid admin key",
            headers=cors_headers(),
        )

    return True, None


def validate_user_payload(payload: dict) -> tuple[dict | None, dict | None]:
    errors: dict[str, str] = {}

    user_id = payload.get("id") or payload.get("uid")
    if not isinstance(user_id, str) or not user_id.strip():
        errors["id"] = "id is required"

    email = payload.get("email")
    if not isinstance(email, str) or not email.strip() or "@" not in email:
        errors["email"] = "email is required"

    display_name = payload.get("displayName") or payload.get("display_name")
    if display_name is not None and (not isinstance(display_name, str) or not display_name.strip()):
        errors["displayName"] = "displayName must be a non-empty string"

    phone = payload.get("phone") or payload.get("phoneNumber") or payload.get("phone_number")
    if phone is not None and (not isinstance(phone, str) or not phone.strip()):
        errors["phone"] = "phone must be a non-empty string"

    role = payload.get("role")
    if not isinstance(role, str) or not role.strip():
        errors["role"] = "role is required"
    elif role.strip() not in _ALLOWED_ROLES:
        errors["role"] = "role must be 'coach' or 'member'"

    if errors:
        return None, errors

    cleaned: dict[str, str] = {
        "id": str(user_id).strip(),
        "email": str(email).strip().lower(),
        "role": str(role).strip(),
    }

    if isinstance(display_name, str) and display_name.strip():
        cleaned["displayName"] = display_name.strip()

    if isinstance(phone, str) and phone.strip():
        cleaned["phone"] = phone.strip()

    return cleaned, None


def _handle_post(*, req: https_fn.Request, db) -> https_fn.Response:
    ok, resp = _is_authorized(req)
    if not ok:
        assert resp is not None
        return resp

    payload = req.get_json(silent=True, force=True) or {}
    if not isinstance(payload, dict):
        return error_response(
            status=400,
            code="validation_error",
            message="Invalid payload (expected JSON object)",
            headers=cors_headers(),
        )

    cleaned, errors = validate_user_payload(payload)
    if errors:
        return error_response(
            status=400,
            code="validation_error",
            message="Invalid user payload",
            details=errors,
            headers=cors_headers(),
        )

    assert cleaned is not None

    now = datetime.now(tz=UTC)
    user_id = cleaned["id"]

    doc_ref = db.collection("users").document(user_id)
    doc_ref.set(
        {
            "email": cleaned["email"],
            "role": cleaned["role"],
            "displayName": cleaned.get("displayName") or "",
            "phone": cleaned.get("phone") or "",
            "updatedAt": now,
            "createdAt": now,
        },
        merge=True,
    )

    return json_response(
        {
            "user": {
                "id": user_id,
                "email": cleaned["email"],
                "role": cleaned["role"],
                "displayName": cleaned.get("displayName") or "",
                "phone": cleaned.get("phone") or "",
                "updatedAt": now.isoformat().replace("+00:00", "Z"),
            }
        },
        status=200,
        headers=cors_headers(),
    )


def _handle_get(*, req: https_fn.Request, db) -> https_fn.Response:
    ok, resp = _is_authorized(req)
    if not ok:
        assert resp is not None
        return resp

    users: list[dict[str, str]] = []
    for doc in db.collection("users").stream():
        data = doc.to_dict() or {}
        users.append(
            {
                "id": getattr(doc, "id", ""),
                "email": str(data.get("email") or ""),
                "role": str(data.get("role") or ""),
                "displayName": str(data.get("displayName") or ""),
                "phone": str(data.get("phone") or ""),
            }
        )

    users.sort(key=lambda u: (u.get("email") or u.get("id") or "").lower())
    return json_response({"users": users}, status=200, headers=cors_headers())


def handle_create_user(req: https_fn.Request) -> https_fn.Response:
    if req.method == "OPTIONS":
        return cors_preflight_response(origin="*", methods="POST,OPTIONS", headers="Content-Type, X-Admin-Key")

    if req.method != "POST":
        return error_response(
            status=405,
            code="method_not_allowed",
            message="Only POST is supported",
            headers=cors_headers(),
        )

    ensure_firebase_initialized()
    db = get_db()
    return _handle_post(req=req, db=db)


def handle_get_users(req: https_fn.Request) -> https_fn.Response:
    if req.method == "OPTIONS":
        return cors_preflight_response(origin="*", methods="GET,OPTIONS", headers="Content-Type, X-Admin-Key")

    if req.method != "GET":
        return error_response(
            status=405,
            code="method_not_allowed",
            message="Only GET is supported",
            headers=cors_headers(),
        )

    ensure_firebase_initialized()
    db = get_db()
    return _handle_get(req=req, db=db)
