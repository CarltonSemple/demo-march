import pytest

from app.profile import validate_profile_payload


def test_validate_profile_payload_allows_empty_update():
    cleaned, errors = validate_profile_payload({})
    assert errors is None
    assert cleaned == {}


def test_validate_profile_payload_valid_fields():
    cleaned, errors = validate_profile_payload(
        {
            "name": "  Casey ",
            "email": "CASEY@EXAMPLE.COM",
            "bio": "  Hello  ",
            "avatarDataUrl": "data:image/png;base64,aaaa",
        }
    )
    assert errors is None
    assert cleaned["name"] == "Casey"
    assert cleaned["email"] == "casey@example.com"
    assert cleaned["bio"] == "Hello"
    assert cleaned["avatarDataUrl"].startswith("data:image/")


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"name": ""}, "name"),
        ({"email": "not-an-email"}, "email"),
        ({"bio": 123}, "bio"),
        ({"avatarDataUrl": "http://example.com/x.png"}, "avatarDataUrl"),
    ],
)
def test_validate_profile_payload_invalid_fields(payload, field):
    cleaned, errors = validate_profile_payload(payload)
    assert cleaned is None
    assert errors is not None
    assert field in errors
