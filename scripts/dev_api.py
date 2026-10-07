"""
Starts the API on the local profile (SQLite, local storage, in-process queue,
seeded demo workspace). No Docker required.

    pipelines/.venv/bin/python scripts/dev_api.py [--port 8000] [--data-dir PATH]

--data-dir keeps the SQLite database and uploaded files somewhere other than
backend/.ledgerlens (e.g. a throwaway sandbox for testing ingestion).

Paths are put on sys.path explicitly: some macOS setups mark a venv's
editable-install .pth files as hidden, and Python 3.13+ skips hidden .pth files.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT / "backend")
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "pipelines")]
os.environ["PYTHONPATH"] = os.pathsep.join([str(ROOT / "backend"), str(ROOT / "pipelines")])
os.environ.setdefault("LEDGER_LENS_PROFILE", "local")

import argparse  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
parser.add_argument("--data-dir", default=None)
args = parser.parse_args()
if args.data_dir:
    data = Path(args.data_dir).expanduser().resolve()
    data.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{data}/ledgerlens.db"
    os.environ["LOCAL_STORAGE_DIR"] = str(data / "storage")
os.environ.setdefault("API_BASE_URL", f"http://localhost:{args.port}")

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=args.port)
