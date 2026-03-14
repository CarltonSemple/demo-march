from firebase_functions import https_fn
from firebase_functions.options import CorsOptions, set_global_options

from app.hello import handle_hello
from app.meetings import handle_meetings

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