from app.hello import hello_payload


def test_hello_payload_default_world():
    assert hello_payload(None) == {"message": "Hello, world!"}


def test_hello_payload_trims_name():
    assert hello_payload("  Humm  ") == {"message": "Hello, Humm!"}
