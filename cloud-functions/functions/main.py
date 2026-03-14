import json

from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app

# For cost control, you can set the maximum number of containers that can be
# running at the same time. This helps mitigate the impact of unexpected
# traffic spikes by instead downgrading performance. This limit is a per-function
# limit. You can override the limit for each function using the max_instances
# parameter in the decorator, e.g. @https_fn.on_request(max_instances=5).
set_global_options(max_instances=10)

_app = None


def _ensure_firebase_initialized() -> None:
	global _app
	if _app is not None:
		return
	try:
		_app = initialize_app()
	except ValueError:
		# Already initialized (can happen in tests / reload scenarios)
		_app = True


def _hello_payload(name: str | None) -> dict:
	normalized = (name or "").strip()
	if not normalized:
		normalized = "world"
	return {"message": f"Hello, {normalized}!"}


@https_fn.on_request()
def hello(req: https_fn.Request) -> https_fn.Response:
	_ensure_firebase_initialized()

	name = None
	args = getattr(req, "args", None)
	if args is not None:
		name = args.get("name")

	body = json.dumps(_hello_payload(name))
	return https_fn.Response(body, status=200, headers={"Content-Type": "application/json"})