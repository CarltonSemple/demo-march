def build_seed_users() -> list[dict]:
    """Return the list of seed users to create via Firebase Auth.

    Edit this list to match your demo needs.

    Supported keys per user:
    - id (required): UID
    - email (required)
    - password (optional; default handled by the script)
    - displayName (optional)
    - phone (optional)
    """

    return [
        {
            "id": "coach-default",
            "email": "coach@example.com",
            "password": "password123",
            "displayName": "Coach Carter",
            "phone": "+15555550123",
        }
    ]
