# demo-march

A small end-to-end demo:
- Firebase Cloud Functions (Python) + Firestore
- Express proxy API
- React (Vite) web UI

## Prerequisites

- Node.js 20+ and npm
- Python 3.13 (Functions runtime is `python313`)
- Firebase CLI (`npm i -g firebase-tools`)
- Java (required for the Firestore emulator)

## Run locally (end-to-end)

You’ll typically run 3 terminals.

### 1) Start Firebase emulators

From `cloud-functions/`:

```bash
firebase emulators:start --only functions,firestore,ui
```

Useful URLs/ports:
- Functions emulator: `http://127.0.0.1:5001/coach-app-demo-3132026/us-central1`
- Firestore emulator: `127.0.0.1:8081`
- Emulator UI: `http://127.0.0.1:4001/`

If `firebase emulators:start` fails, ensure Java is installed and try `firebase setup:emulators:firestore`.

### 2) Start Express server

From `coach-mini-app/server`:

```bash
npm install
npm run dev
```

Optional override if you’re using a different project/region:

```bash
export PY_FUNCTION_BASE_URL="http://127.0.0.1:5001/coach-app-demo-3132026/us-central1"
```

If `PY_FUNCTION_BASE_URL` is unset, the server defaults to
`http://127.0.0.1:5001/<project>/<region>` using `FIREBASE_PROJECT`/`GCLOUD_PROJECT` and `FUNCTION_REGION`.

Express listens on `http://127.0.0.1:3005`.

### 3) Start React web

From `coach-mini-app/web`:

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:3000`.

Vite proxies `/api/*` to Express (`http://127.0.0.1:3005`).

## API overview

These are called by the React UI via Express `/api/*` proxies.

- Profile
	- `GET /api/profile?userId=...` (optional `userId`, defaults to `default`; `coachId` is accepted as an alias)
	- `PUT /api/profile` body can include any subset of `{ name, email, bio, avatarDataUrl }`

- Announcements
	- `GET /api/announcements?groupId=...` (`groupId` required)
	- `POST /api/announcements` body `{ groupId, text }`

- Meetings
	- `GET /api/meetings?groupId=...` (`groupId` required)
	- `POST /api/meetings` body:
		- `groupId`, `title`, `dateTime` (ISO-8601 or epoch millis), `meetLink`, `attendees` (non-empty list)
		- `meetLink` must start with `https://meet.google.com/`

Notes:
- The demo web UI uses a simple default `groupId` of `demo-group`.
- In emulator mode, meeting email sending is stubbed (no real email).

## Email (production)

Meeting creation sends email via MailerSend when not running in emulators.

Environment variables:
- `MAILERSEND_API_KEY` (required)
- `MAIL_FROM_EMAIL` (required)
- `MAIL_FROM_NAME` (optional)
- `SEND_FROM_EMULATOR` (required)

## Tests

### Python tests

First-time setup (create a venv under `cloud-functions/functions/`):

```bash
cd cloud-functions/functions
python3.13 -m venv venv
```

Run tests (from repo root):

```bash
cd cloud-functions/functions
./venv/bin/python -m pip install -q -r requirements-dev.txt
./venv/bin/python -m pytest -q
```

Integration-only (assumes emulators are already running):

```bash
cd cloud-functions/functions
./venv/bin/python -m pip install -q -r requirements-dev.txt
./venv/bin/python -m pytest -q -m integration -rs
```

### Node (Express) integration tests

From `coach-mini-app/server` (assumes emulators are running):

```bash
npm test
```

### Run everything

```bash
# Python tests
cd cloud-functions/functions
./venv/bin/python -m pip install -q -r requirements-dev.txt
./venv/bin/python -m pytest -q

# Node (Express) integration tests
cd coach-mini-app/server
export PY_FUNCTION_BASE_URL="http://127.0.0.1:5001/coach-app-demo-3132026/us-central1"
npm install
npm test
```

## CI

Workflows:
- Node unit tests: `.github/workflows/node-unit-tests.yml`
- Node integration tests (runs against Firebase emulators): `.github/workflows/node-integration-emulators.yml`
- Python unit tests: `.github/workflows/python-unit-tests.yml`
- Python integration tests (runs against Firebase emulators): `.github/workflows/cloud-function-integration.yml`