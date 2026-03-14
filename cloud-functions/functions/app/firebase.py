from __future__ import annotations

import os

from firebase_admin import firestore, initialize_app

_app: object | None = None
_db: firestore.Client | None = None


def ensure_firebase_initialized() -> None:
    global _app
    if _app is not None:
        return

    try:
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
