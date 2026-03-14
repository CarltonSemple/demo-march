#!/usr/bin/env python3

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import firebase_admin
from firebase_admin import auth as admin_auth
import google.auth
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError

REPO_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS_PATH = REPO_ROOT / "cloud-functions" / "functions"
if str(FUNCTIONS_PATH) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS_PATH))

try:
    from app.seed import build_seed_users  # pyright: ignore[reportMissingImports]
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "Failed to import seed users from cloud-functions/functions/app/seed.py\n"
        "Make sure you're running this script from within the repo and that the Functions package exists.\n"
        f"Original error: {exc}"
    )

DEFAULT_PROJECT_ID = os.environ.get("GCLOUD_PROJECT", "coach-app-demo-3132026")
DEFAULT_EMULATOR_BASE_URL = "http://127.0.0.1:5001/coach-app-demo-3132026/us-central1"
DEFAULT_CLOUD_BASE_URL = "https://us-central1-coach-app-demo-3132026.cloudfunctions.net"


def resolve_base_url(base_url: str | None, cloud: bool) -> str:
    # This script uses the Admin SDK for Auth, and also calls a Cloud Function to
    # seed Firestore user documents.
    if base_url:
        return base_url
    if cloud:
        return DEFAULT_CLOUD_BASE_URL
    return os.environ.get("FUNCTIONS_BASE_URL", DEFAULT_EMULATOR_BASE_URL)


def _resolve_admin_api_key(cli_value: str | None) -> str:
    if cli_value and cli_value.strip():
        return cli_value.strip()
    return (os.environ.get("ADMIN_API_KEY") or "").strip()


def upsert_user_document_via_function(
    *,
    base_url: str,
    timeout: float,
    admin_api_key: str,
    user_id: str,
    email: str,
    role: str,
    display_name: str | None,
    phone_number: str | None,
) -> tuple[int, str]:
    url = base_url.rstrip("/") + "/createUser"

    payload = {
        "id": user_id,
        "email": email,
        "role": role,
        "displayName": display_name or "",
        "phone": phone_number or "",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    if admin_api_key:
        req.add_header("X-Admin-Key", admin_api_key)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return int(getattr(resp, "status", 200)), body
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        return int(getattr(exc, "code", 500)), body
    except Exception as exc:
        return 500, str(exc)


class _EmulatorCredentials(Credentials):
    """A minimal credential implementation for emulators.

    AnonymousCredentials.refresh() raises, but some client paths may call refresh
    even when talking to emulators.
    """

    def __init__(self):
        super().__init__()
        self.token = "owner"

    def refresh(self, request):
        self.token = "owner"


def validate_cloud_credentials(cloud: bool) -> None:
    if not cloud:
        return
    try:
        google.auth.default()
    except DefaultCredentialsError as exc:
        raise SystemExit(
            "Cloud mode requires Google Application Default Credentials (ADC).\n"
            "Run one of:\n"
            "  gcloud auth application-default login\n"
            "or pass --credentials-file (or set GOOGLE_APPLICATION_CREDENTIALS) to a service account JSON file.\n"
            f"Original error: {exc}"
        )


def initialize_auth_app(*, cloud: bool, project_id: str):
    if not cloud:
        os.environ.setdefault("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
        # Ensure downstream libs that read these will get a consistent project.
        os.environ.setdefault("GCLOUD_PROJECT", project_id)
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)

    if firebase_admin._apps:
        return firebase_admin.get_app()

    if cloud:
        return firebase_admin.initialize_app(options={"projectId": project_id})

    # In emulator mode, avoid ADC dependency.
    from firebase_admin import credentials

    cred = credentials._ExternalCredentials(_EmulatorCredentials())
    return firebase_admin.initialize_app(cred, options={"projectId": project_id})


def create_user(
    app,
    user_id: str,
    email: str,
    password: str,
    display_name: str | None,
    phone_number: str | None,
):
    try:
        admin_auth.create_user(
            app=app,
            uid=user_id,
            email=email,
            password=password,
            display_name=display_name,
            phone_number=phone_number,
            email_verified=True,
        )
        return 200, "created"
    except admin_auth.UidAlreadyExistsError:
        admin_auth.update_user(
            user_id,
            app=app,
            email=email,
            password=password,
            display_name=display_name,
            phone_number=phone_number,
            email_verified=True,
        )
        return 200, "updated"
    except admin_auth.EmailAlreadyExistsError:
        existing = admin_auth.get_user_by_email(email, app=app)
        admin_auth.update_user(
            existing.uid,
            app=app,
            password=password,
            display_name=display_name,
            phone_number=phone_number,
            email_verified=True,
        )
        if existing.uid != user_id:
            return 409, f"email exists with different uid ({existing.uid})"
        return 200, "updated"
    except Exception as exc:
        return 500, str(exc)


def clear_seed_users(app, users: list[dict]):
    deleted_count = 0
    for user in users:
        user_id = user.get("id")
        if not user_id:
            continue
        try:
            admin_auth.delete_user(user_id, app=app)
            deleted_count += 1
        except admin_auth.UserNotFoundError:
            continue
    return deleted_count


def main():
    parser = argparse.ArgumentParser(description="Create all seed users via Firebase Auth (Admin SDK)")
    parser.add_argument(
        "--base-url",
        default=None,
        help="Functions base URL override (accepted for CLI parity; not used by this script)",
    )
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="Use production Firebase Auth endpoint (requires ADC)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing seed user UIDs before creating/updating users",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Request timeout in seconds (used for Cloud Function calls)",
    )
    parser.add_argument(
        "--credentials-file",
        default=None,
        help="Path to Google service account JSON (sets GOOGLE_APPLICATION_CREDENTIALS)",
    )
    parser.add_argument(
        "--admin-api-key",
        default=None,
        help="Admin key for calling the createUser Cloud Function (defaults to ADMIN_API_KEY env var)",
    )
    parser.add_argument("--project-id", default=DEFAULT_PROJECT_ID, help="Firebase project id")
    args = parser.parse_args()

    base_url = resolve_base_url(args.base_url, args.cloud)
    admin_api_key = _resolve_admin_api_key(args.admin_api_key)

    if args.base_url is not None or "FUNCTIONS_BASE_URL" in os.environ:
        print(f"Using Cloud Function base URL: {base_url}")
    if args.timeout != 15.0:
        print(f"Cloud Function request timeout: {args.timeout}s")

    if args.credentials_file:
        credentials_path = Path(args.credentials_file).expanduser().resolve()
        if not credentials_path.exists():
            raise SystemExit(f"Credentials file not found: {credentials_path}")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credentials_path)
        print(f"Using credentials file: {credentials_path}")

    validate_cloud_credentials(args.cloud)
    app = initialize_auth_app(cloud=args.cloud, project_id=args.project_id)

    users = build_seed_users()
    created_count = 0
    db_upserted_count = 0
    failed_count = 0

    if args.clear:
        deleted_count = clear_seed_users(app, users)
        print(f"Cleared existing seed users by UID: {deleted_count}")

    for user in users:
        user_id = user.get("id")
        email = user.get("email")
        password = user.get("password") or "password123"
        role = (user.get("role") or "").strip()
        display_name = user.get("displayName")
        phone_number = user.get("phone") or user.get("whatsapp") or "+15555550123"

        if not user_id:
            print(f"Skipping user without id: {email or 'unknown-email'}")
            failed_count += 1
            continue

        if not email:
            print(f"Skipping user without email: {user_id}")
            failed_count += 1
            continue

        if role not in ("coach", "member"):
            print(f"Skipping user with invalid role: {email} ({user_id}) role={role or 'missing'}")
            failed_count += 1
            continue

        status_code, response_text = create_user(
            app=app,
            user_id=user_id,
            email=email,
            password=password,
            display_name=display_name,
            phone_number=phone_number,
        )

        if status_code == 200:
            print(f"Upserted user: {email} ({user_id}) [{response_text}]")
            created_count += 1

            db_status, db_body = upsert_user_document_via_function(
                base_url=base_url,
                timeout=args.timeout,
                admin_api_key=admin_api_key,
                user_id=user_id,
                email=email,
                role=role,
                display_name=display_name,
                phone_number=phone_number,
            )
            if 200 <= db_status < 300:
                print(f"Upserted user doc: {email} ({user_id})")
                db_upserted_count += 1
            else:
                print(f"Failed upserting user doc: {email} ({user_id})")
                print(db_status, db_body)
        else:
            print(f"Failed creating user: {email}")
            print(status_code, response_text)
            failed_count += 1

    print(
        f"Done. auth_upserted={created_count} db_upserted={db_upserted_count} "
        f"failed={failed_count} total={len(users)}"
    )


if __name__ == "__main__":
    main()
