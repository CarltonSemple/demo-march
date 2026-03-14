import os

import pytest
import requests


def _base_url() -> str:
    # Allow override for CI/local setups.
    # Example: BASE_URL=http://127.0.0.1:5001/my-project/us-central1
    explicit = os.environ.get("BASE_URL")
    if explicit:
        return explicit.rstrip("/")

    project_id = (
        os.environ.get("FIREBASE_PROJECT")
        or os.environ.get("GCLOUD_PROJECT")
        or "coach-app-demo-3132026"
    )
    region = os.environ.get("FUNCTION_REGION") or "us-central1"
    return f"http://127.0.0.1:5001/{project_id}/{region}"


@pytest.mark.integration
def test_hello_world_endpoint_returns_json():
    url = f"{_base_url()}/hello"

    try:
        resp = requests.get(url, timeout=3)
    except requests.exceptions.RequestException as exc:
        pytest.skip(f"Functions emulator not reachable at {url}: {exc}")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}, body: {resp.text}"
    assert resp.headers.get("content-type", "").startswith("application/json")
    assert resp.json() == {"message": "Hello, world!"}


@pytest.mark.integration
def test_hello_world_endpoint_accepts_name_query_param():
    url = f"{_base_url()}/hello"

    try:
        resp = requests.get(url, params={"name": "Casey"}, timeout=3)
    except requests.exceptions.RequestException as exc:
        pytest.skip(f"Functions emulator not reachable at {url}: {exc}")

    assert resp.status_code == 200
    assert resp.json() == {"message": "Hello, Casey!"}
