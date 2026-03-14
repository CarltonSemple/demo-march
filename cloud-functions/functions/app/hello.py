from __future__ import annotations

from firebase_functions import https_fn

from .firebase import ensure_firebase_initialized
from .http import json_response


def hello_payload(name: str | None) -> dict:
    normalized = (name or "").strip()
    if not normalized:
        normalized = "world"
    return {"message": f"Hello, {normalized}!"}


def handle_hello(req: https_fn.Request) -> https_fn.Response:
    ensure_firebase_initialized()

    name = None
    args = getattr(req, "args", None)
    if args is not None:
        name = args.get("name")

    return json_response(hello_payload(name), status=200)
