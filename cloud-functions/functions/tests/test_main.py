from main import _hello_payload


def test_hello_payload_default_world():
    assert _hello_payload(None) == {"message": "Hello, world!"}


def test_hello_payload_trims_name():
    assert _hello_payload("  Humm  ") == {"message": "Hello, Humm!"}
