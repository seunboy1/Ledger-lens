"""
Test environment: the local profile on a throwaway SQLite file and storage
directory. Must run before any `app` module is imported, because settings
are read once at import time.
"""

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="ledgerlens-test-")
os.environ.update(
    {
        "LEDGER_LENS_PROFILE": "local",
        "DATABASE_URL": f"sqlite+aiosqlite:///{_tmp}/test.db",
        "LOCAL_STORAGE_DIR": f"{_tmp}/storage",
        "LLM_PROVIDER_API_KEY": "",
        "API_BASE_URL": "http://testserver",
    }
)
