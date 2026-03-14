#!/usr/bin/env bash
set -euo pipefail

# Runs Express (API proxy) and Vite (React dev server) in one container.

cd /workspace/coach-mini-app

( cd server && npm run dev ) &
server_pid=$!

( cd web && npm run dev -- --host 0.0.0.0 --port 3000 ) &
web_pid=$!

cleanup() {
  kill "${server_pid}" "${web_pid}" 2>/dev/null || true
  wait || true
}

trap cleanup SIGINT SIGTERM

# Exit when either process exits.
wait -n "${server_pid}" "${web_pid}"
cleanup
