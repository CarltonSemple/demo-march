from __future__ import annotations

import os

from firebase_admin import credentials, firestore, initialize_app
from google.auth.credentials import Credentials

_app: object | None = None
_db: firestore.Client | None = None


class _EmulatorCredentials(Credentials):
    """A minimal credential for emulators.

    `google.auth.credentials.AnonymousCredentials` exists, but its `refresh()` raises.
    Some firebase-admin / google-cloud clients call `refresh()` even when talking
    to emulators, so we provide a no-op refreshable credential instead.
    """

    def __init__(self):
        super().__init__()
        self.token = "owner"

    def refresh(self, request):
        self.token = "owner"


def ensure_firebase_initialized() -> None:
    global _app
    if _app is not None:
        return

    try:
        if is_emulator_environment():
            project_id = (
                os.environ.get("FIREBASE_PROJECT")
                or os.environ.get("GCLOUD_PROJECT")
                or os.environ.get("GOOGLE_CLOUD_PROJECT")
                or "demo-project"
            )
            cred = credentials._ExternalCredentials(_EmulatorCredentials())
            _app = initialize_app(cred, {"projectId": project_id})
        else:
            _app = initialize_app()
    except ValueError:
        # Already initialized (can happen in tests / reload scenarios)
        _app = object()


def get_db() -> firestore.Client:
    global _db
    if _db is None:
        ensure_firebase_initialized()
        _db = firestore.client()
    return _db


def is_emulator_environment() -> bool:
    return bool(
        os.environ.get("FIREBASE_EMULATOR_HUB")
        or os.environ.get("FIRESTORE_EMULATOR_HOST")
        or os.environ.get("FUNCTIONS_EMULATOR") == "true"
        or os.environ.get("FIREBASE_CLI") == "true"
    )
