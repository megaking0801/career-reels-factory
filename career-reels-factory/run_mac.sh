#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "Missing .venv. Run ./setup_mac.sh first."
  exit 1
fi

echo "Starting: http://localhost:8000  (Ctrl+C to stop)"
# --reload: auto-restart on code edits while developing
exec ./.venv/bin/python -m uvicorn app.main:app --reload
