from firebase_functions import https_fn
from firebase_functions.options import CorsOptions, set_global_options

from app.announcements import handle_announcements
from app.hello import handle_hello
from app.meetings import handle_meetings
from app.profile import handle_profile
from app.users import handle_create_user, handle_get_users

"""Firebase HTTPS Cloud Functions entrypoint.

This file intentionally stays thin:
- Exported Cloud Function handlers live here (so Firebase can discover them).
- Implementation details live in the `app/` package.

Endpoints
---------

`hello` (HTTP)
	- Method: GET
	- Query: `name` (optional)
	- Response: 200 JSON `{ "message": "Hello, <name|world>!" }`

`meetings` (HTTP)
	- Methods: GET, POST, OPTIONS
	- CORS: enabled (preflight supported)

	GET /meetings
		- Query: `groupId` (required)
		- Response: 200 JSON `{ "groupId": "...", "meetings": [...] }`

	POST /meetings
		- Body (JSON):
				- `groupId` (required)
				- `title` (required)
				- `dateTime` (required; ISO-8601 string or epoch millis)
				- `meetLink` (required; must start with `https://meet.google.com/`)
				- `attendees` (required; non-empty list of emails)
		- Response: 201 JSON `{ "meeting": { ... } }`
		- Email behavior:
				- In emulators: email is stubbed (always "sent": true)
				- In production: requires `MAILERSEND_API_KEY` + `MAIL_FROM_EMAIL`
					(optional: `MAIL_FROM_NAME`)

`profile` (HTTP)
	- Methods: GET, PUT, OPTIONS
	- CORS: enabled
	- Query: `userId` (optional, defaults to "default")
	- GET response: 200 JSON `{ "profile": { name, email, bio, avatarDataUrl } }`
	- PUT body (JSON): any subset of `{ name, email, bio, avatarDataUrl }`

`announcements` (HTTP)
	- Methods: GET, POST, OPTIONS
	- CORS: enabled
	- GET query: `groupId` (required)
	- POST body (JSON): `{ groupId, text }`

`createUser` (HTTP)
	- Methods: POST, OPTIONS
	- CORS: enabled
	- Purpose: Upsert a user document into Firestore (`users/{id}`)
	- Body (JSON): `{ id, email, role, displayName?, phone? }` (`role` is `coach` or `member`)
	- Security:
		- In emulators: allowed without auth
		- In non-emulator environments: requires `ADMIN_API_KEY` and `X-Admin-Key` header

`getUsers` (HTTP)
	- Methods: GET, OPTIONS
	- CORS: enabled
	- Purpose: List user documents from Firestore (`users/*`)
	- Response: 200 JSON `{ "users": [ { id, email, role, displayName, phone } ] }`
	- Security:
		- In emulators: allowed without auth
		- In non-emulator environments: requires `ADMIN_API_KEY` and `X-Admin-Key` header
"""

set_global_options(max_instances=10)
@https_fn.on_request()
def hello(req: https_fn.Request) -> https_fn.Response:
	"""Simple hello-world endpoint.

	See module docstring for request/response shape.
	"""
	return handle_hello(req)


@https_fn.on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET", "POST", "OPTIONS"]))
def meetings(req: https_fn.Request) -> https_fn.Response:
	"""Meeting Scheduling API.

	See module docstring for request/response shape and required fields.
	"""
	return handle_meetings(req)


@https_fn.on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET", "PUT", "OPTIONS"]))
def profile(req: https_fn.Request) -> https_fn.Response:
	"""Coach profile API.

	See module docstring for request/response shape.
	"""
	return handle_profile(req)


@https_fn.on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET", "POST", "OPTIONS"]))
def announcements(req: https_fn.Request) -> https_fn.Response:
	"""Announcements API.

	See module docstring for request/response shape.
	"""
	return handle_announcements(req)


@https_fn.on_request(cors=CorsOptions(cors_origins="*", cors_methods=["POST", "OPTIONS"]))
def createUser(req: https_fn.Request) -> https_fn.Response:
	"""Create/Update a user document.

	See module docstring for request/response shape.
	"""
	return handle_create_user(req)


@https_fn.on_request(cors=CorsOptions(cors_origins="*", cors_methods=["GET", "OPTIONS"]))
def getUsers(req: https_fn.Request) -> https_fn.Response:
	"""List user documents.

	See module docstring for request/response shape.
	"""
	return handle_get_users(req)