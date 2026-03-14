# demo-march

## Cloud Functions (Python)

- Start emulators (from `cloud-functions/`):
	- `firebase emulators:start --only functions,firestore`
- Run Python tests:
	- `powershell -NoProfile -ExecutionPolicy Bypass -File .\run-python-tests.ps1`
	- Integration-only (assumes emulators running): `./run-python-tests.ps1 -IntegrationOnly`

## App (React + Express)

### Express server

- Install + run (from `coach-mini-app/server`):
	- `npm install`
	- `set PY_FUNCTION_BASE_URL=http://127.0.0.1:5001/coach-app-demo-3132026/us-central1`
	- `npm run dev`

### React web

- Install + run (from `coach-mini-app/web`):
	- `npm install`
	- `npm run dev`

### Run all tests

- `powershell -NoProfile -ExecutionPolicy Bypass -File .\run-all-tests.ps1`

## CI

- GitHub Actions workflow runs the Express integration test against Firebase emulators:
	- `.github/workflows/node-integration-emulators.yml`