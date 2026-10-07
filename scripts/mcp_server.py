"""
Run the Ledger Lens MCP server over stdio (local profile, demo workspace).

    pipelines/.venv/bin/python scripts/mcp_server.py

Claude Desktop / Claude Code config:
    {"mcpServers": {"ledger-lens": {"command": "<repo>/pipelines/.venv/bin/python",
                                    "args": ["<repo>/scripts/mcp_server.py"]}}}

Start the API once first (scripts/dev_api.py) so the demo workspace exists.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT / "backend")
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "pipelines")]
os.environ.setdefault("LEDGER_LENS_PROFILE", "local")
os.environ.setdefault("DEV_SEED", "false")  # read-only: never seed from the MCP process

from app.mcp_server import build_server  # noqa: E402

build_server().run()  # stdio
