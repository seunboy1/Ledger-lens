"""
Upload sample statements through the real ingestion API and check each outcome
against samples/statements/manifest.json.

    pipelines/.venv/bin/python scripts/upload_samples.py            # files not already in the demo seed
    pipelines/.venv/bin/python scripts/upload_samples.py 05 07      # specific files (by prefix)
    pipelines/.venv/bin/python scripts/upload_samples.py --all      # everything (duplicates seeded data)

Same path as the browser: request an upload target, PUT the bytes, notify, then
poll until extraction and reconciliation finish. Exits non-zero on any mismatch.
"""

from __future__ import annotations

import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "samples" / "statements"
API = os.environ.get("LEDGER_LENS_API", "http://localhost:8000")
TERMINAL = {"reconciled", "needs_review", "failed"}


def naira(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"))


def main(argv: list[str]) -> int:
    manifest = json.loads((SAMPLES / "manifest.json").read_text())
    args = [a for a in argv if not a.startswith("--")]
    if args:
        chosen = [m for m in manifest if any(m["file"].startswith(a) for a in args)]
    elif "--all" in argv:
        chosen = manifest
    else:
        chosen = [m for m in manifest if not m["in_demo_seed"]]

    with httpx.Client(base_url=API, timeout=60) as c:
        try:
            tenant = c.get("/auth/demo-session").raise_for_status().json()["tenant_id"]
        except httpx.HTTPError as e:
            print(f"Cannot reach the API at {API} ({e}). Start it with: pipelines/.venv/bin/python scripts/dev_api.py")
            return 2
        c.headers["X-Tenant-Id"] = tenant

        failures = 0
        for m in chosen:
            path = SAMPLES / m["file"]
            started = time.monotonic()
            up = c.post("/documents/upload", json={"filename": m["file"]}).raise_for_status().json()
            target = up["upload_url"]
            if target.startswith(API):
                c.put(target[len(API):], content=path.read_bytes(), headers={"Content-Type": "application/pdf"}).raise_for_status()
            else:
                httpx.put(target, content=path.read_bytes()).raise_for_status()
            c.post(f"/documents/{up['document_id']}/notify-uploaded").raise_for_status()

            detail = None
            while time.monotonic() - started < 300:
                detail = c.get(f"/documents/{up['document_id']}").raise_for_status().json()
                if detail["status"] in TERMINAL:
                    break
                time.sleep(1)

            problems = []
            if detail["status"] != m["expected_status"]:
                problems.append(f"status {detail['status']} != expected {m['expected_status']}")
            if "rows" in m and m["expected_status"] != "failed":
                if detail["transaction_count"] != m["rows"]:
                    problems.append(f"rows {detail['transaction_count']} != {m['rows']}")
                proof = detail["proof"]
                if proof["opening"] is None or naira(proof["opening"]) != naira(m["opening_balance"]):
                    problems.append(f"opening {proof['opening']} != {m['opening_balance']}")
                if proof["closing_printed"] is None or naira(proof["closing_printed"]) != naira(m["closing_balance"]):
                    problems.append(f"printed closing {proof['closing_printed']} != {m['closing_balance']}")
                if m["expected_status"] == "reconciled" and naira(proof["total_debits"]) != naira(m["total_debits"]):
                    problems.append(f"debits {proof['total_debits']} != {m['total_debits']}")
                if "misprint" in m:
                    flagged = [r["description"] for r in detail["failing_rows"]]
                    if flagged != [m["misprint"]["narration"]]:
                        problems.append(f"flagged rows {flagged} != [{m['misprint']['narration']}]")

            secs = time.monotonic() - started
            chunks = detail["chunks"]["total"] if detail else 0
            layout = (detail or {}).get("layout") or {}
            how = f"{layout.get('induced_by', '-')}, reused {layout.get('times_reused', 0)}x" if layout else "-"
            mark = "PASS" if not problems else "FAIL"
            failures += bool(problems)
            print(f"{mark}  {m['file']:<46} {detail['status']:<13} rows={detail['transaction_count']:<5} chunks={chunks:<2} spec=({how})  {secs:5.1f}s")
            if detail.get("error") and detail["status"] == "failed":
                print(f"      reason: {detail['error']}")
            for p in problems:
                print(f"      {p}")

    print(f"\n{len(chosen) - failures}/{len(chosen)} matched the manifest")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
