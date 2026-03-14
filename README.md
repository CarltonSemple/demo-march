# demo-march

A small end-to-end demo:
- Firebase Cloud Functions (Python) + Firestore
- Express proxy API
- React (Vite) web UI

## Prerequisites (if not using Docker to run everything)

- Node.js 20+ and npm
- Python 3.13 (Functions runtime is `python313`)
- Firebase CLI (`npm i -g firebase-tools`)
- Java (required for the Firestore emulator)

## Run locally (end-to-end)

Open three terminals.

### 1) Start Firebase emulators
In the first terminal, run
```bash
docker build -t emulators -f ./cloud-functions/Dockerfile.emulators ./cloud-functions
docker run --rm -it -e MAILERSEND_API_KEY="<insert_mailersend_api_key_here>" -e MAIL_FROM_EMAIL="meetings@test-p7kx4xwrpevg9yjr.mlsender.net" -e SEND_FROM_EMULATOR="true" -p 5001:5001 -p 8081:8081 -p 9099:9099 -p 4001:4001 emulators
```

Useful URLs/ports:
- Functions emulator: `http://127.0.0.1:5001/coach-app-demo-3132026/us-central1`
- Firestore emulator: `127.0.0.1:8081`
- Auth emulator: `127.0.0.1:9099`
- Emulator UI: `http://127.0.0.1:4001/`


### 2) Run Express + React in Docker

This runs the Express proxy (port 3005) and the React/Vite dev server (port 3000) in one container.
In the second terminal, run
```bash
docker build -t coach-mini-app -f coach-mini-app/Dockerfile.dev .
docker run --rm -it -p 3000:3000 -p 3005:3005 -e PY_FUNCTION_BASE_URL="http://host.docker.internal:5001/coach-app-demo-3132026/us-central1" coach-mini-app
```

### 3) Run Seed Script
This script creates two users in the Firebase Auth emulator and the firestore backend via the firebase cloud functions
```bash
python ./scripts/create_seed_users.py
```


Open `http://localhost:3000`.

Vite proxies `/api/*` to Express (`http://localhost:3005`).

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

## Tests

### Node (Express) integration tests

From `coach-mini-app/server` (assumes emulators are running):

```bash
npm test
```

### Cloud Function (Python) tests

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