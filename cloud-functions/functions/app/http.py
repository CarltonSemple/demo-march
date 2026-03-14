from __future__ import annotations

import json
from typing import Any

from firebase_functions import https_fn


def _merge_headers(*parts: dict[str, str] | None) -> dict[str, str]:
    merged: dict[str, str] = {}
    for part in parts:
        if part:
            merged.update(part)
    return merged


def cors_headers(origin: str = "*") -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        "Vary": "Origin",
    }


def cors_preflight_response(
    *,
    origin: str = "*",
    methods: str = "GET,POST,OPTIONS",
    headers: str = "Content-Type, Authorization",
    max_age_seconds: int = 3600,
) -> https_fn.Response:
    return https_fn.Response(
        "",
        status=204,
        headers={
            **cors_headers(origin),
            "Access-Control-Allow-Methods": methods,
            "Access-Control-Allow-Headers": headers,
            "Access-Control-Max-Age": str(max_age_seconds),
        },
    )


def json_response(payload: dict[str, Any], *, status: int = 200, headers: dict[str, str] | None = None) -> https_fn.Response:
    return https_fn.Response(
        json.dumps(payload, default=str),
        status=status,
        headers=_merge_headers({"Content-Type": "application/json"}, headers),
    )


def error_response(
    *,
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> https_fn.Response:
    payload: dict[str, Any] = {"error": code, "message": message}
    if details:
        payload["details"] = details
    return json_response(payload, status=status, headers=headers)
