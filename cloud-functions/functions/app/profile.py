from __future__ import annotations

import re
from datetime import UTC, datetime

from firebase_admin import firestore
from firebase_functions import https_fn

from .firebase import ensure_firebase_initialized, get_db
from .http import cors_headers, cors_preflight_response, error_response, json_response

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_profile_payload(payload: dict) -> tuple[dict | None, dict | None]:
    """Returns (cleaned, errors).

    All fields are optional on update, but if provided must be valid.
    """

    errors: dict[str, str] = {}
    cleaned: dict[str, str] = {}

    if "name" in payload:
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            errors["name"] = "name must be a non-empty string"
        else:
            cleaned["name"] = name.strip()

    if "email" in payload:
        email = payload.get("email")
        if not isinstance(email, str) or not email.strip() or not _EMAIL_RE.match(email.strip()):
            errors["email"] = "email must be a valid email"
        else:
            cleaned["email"] = email.strip().lower()

    if "bio" in payload:
        bio = payload.get("bio")
        if bio is None:
            cleaned["bio"] = ""
        elif not isinstance(bio, str):
            errors["bio"] = "bio must be a string"
        else:
            cleaned["bio"] = bio.strip()

    if "avatarDataUrl" in payload:
        avatar = payload.get("avatarDataUrl")
        if avatar is None or avatar == "":
            cleaned["avatarDataUrl"] = ""
        elif not isinstance(avatar, str) or not avatar.startswith("data:image/"):
            errors["avatarDataUrl"] = "avatarDataUrl must be a data:image/* data URL"
        else:
            cleaned["avatarDataUrl"] = avatar

    if errors:
        return None, errors

    return cleaned, None


def handle_profile(req: https_fn.Request) -> https_fn.Response:
    if req.method == "OPTIONS":
        return cors_preflight_response(origin="*")

    ensure_firebase_initialized()
    db = get_db()

    user_id = "default"
    args = getattr(req, "args", None)
    if args is not None:
        maybe = args.get("userId") or args.get("user_id") or args.get("coachId") or args.get("coach_id")
        if isinstance(maybe, str) and maybe.strip():
            user_id = maybe.strip()

    # Store profiles keyed by userId so members and coaches both work.
    profiles_ref = db.collection("profiles").document(user_id)
    legacy_ref = db.collection("coaches").document(user_id)

    if req.method == "GET":
        snap = profiles_ref.get()
        if getattr(snap, "exists", False):
            data = snap.to_dict() or {}
        else:
            legacy = legacy_ref.get()
            data = legacy.to_dict() if getattr(legacy, "exists", False) else {}

        profile = {
            "userId": user_id,
            "name": data.get("name") or "",
            "email": data.get("email") or "",
            "bio": data.get("bio") or "",
            "avatarDataUrl": data.get("avatarDataUrl") or "",
        }

        return json_response({"profile": profile}, status=200, headers=cors_headers())

    if req.method in ("PUT", "POST"):
        payload = req.get_json(silent=True, force=True) or {}
        cleaned, errors = validate_profile_payload(payload)
        if errors:
            return error_response(
                status=400,
                code="validation_error",
                message="Invalid profile payload",
                details=errors,
                headers=cors_headers(),
            )

        assert cleaned is not None
        cleaned["updatedAt"] = datetime.now(tz=UTC)

        profiles_ref.set(cleaned, merge=True)
        return json_response({"profile": {"userId": user_id, **cleaned}}, status=200, headers=cors_headers())

    return error_response(
        status=405,
        code="method_not_allowed",
        message="Only GET and PUT are supported",
        headers=cors_headers(),
    )
