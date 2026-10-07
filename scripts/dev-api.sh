#!/usr/bin/env bash
# Runs the API on the local profile: SQLite, local file storage, in-process
# extraction queue, and the seeded demo workspace. No Docker required.
#
# PYTHONPATH is set explicitly because some macOS setups mark the venv's
# editable-install .pth files as hidden, and Python 3.13+ skips hidden .pth files.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${LEDGER_LENS_VENV:-$ROOT/pipelines/.venv}"
cd "$ROOT/backend"
export PYTHONPATH="$ROOT/backend:$ROOT/pipelines${PYTHONPATH:+:$PYTHONPATH}"
export LEDGER_LENS_PROFILE="${LEDGER_LENS_PROFILE:-local}"
exec "$VENV/bin/uvicorn" app.main:app --host 127.0.0.1 --port "${PORT:-8000}" "$@"
