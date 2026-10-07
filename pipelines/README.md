# Ledger Lens — extraction pipeline

The Prefect flow that turns an uploaded PDF into reconciled rows in Postgres. This is the implementation of docs/architecture.md §2 and §8 — the part that makes "the LLM never reads a full statement" true rather than aspirational.

## How it fits together

```
consumer.py  (RabbitMQ, pulls one ingest-job message at a time)
    │
    ▼
extract_statement()          — one Prefect flow run per document
    │
    ├─ compute_chunks()        — split into page-range chunks (chunking.py)
    │
    ├─ process_chunk()  ×N     — one Prefect task per chunk, mapped, idempotent
    │     ├─ extract_page_range()      — pdfplumber, no AI (ocr.py)
    │     ├─ fingerprint_layout()      — hash header + column count (backend: app/services/layout.py)
    │     ├─ [cache hit]  → reuse cached LayoutSpec
    │     ├─ [cache miss] → induce_spec() + validate_spec()   — the ONE AI call per new layout (spec_induction.py)
    │     └─ parse_page()              — deterministic, no AI (parser.py)
    │
    ├─ check_completeness()    — gap detection; requeues only missing ranges (merge.py)
    │
    └─ promote_and_reconcile()
          ├─ normalize_transaction_type()  — CR/Credit/Deposit → canonical (backend: app/services/layout.py)
          ├─ reconcile_rows()               — the balance proof (backend: app/services/reconciliation.py)
          └─ _attempt_targeted_repair()      — the OTHER AI call, only on rows that fail reconciliation
```

Two AI calls, total, per document lifecycle in the common case: one to learn a genuinely new layout (amortized to zero after the first document of that shape), and — rarely — one per row that fails the balance-reconciliation check. Everything else in the diagram above is deterministic Python with unit test coverage.

## Layout

```
ledger_lens_pipelines/
├── extraction/
│   ├── chunking.py       — page-range splitting, expected-chunk-count, gap detection
│   ├── ocr.py             — pdfplumber-based text/table extraction (PaddleOCR fallback stubbed)
│   ├── spec_induction.py   — builds the induction prompt, validates the LLM's proposed spec
│   ├── parser.py            — applies a cached spec to rows; supports all 3 amount conventions
│   └── merge.py               — completeness check wrapping chunking.find_gaps
├── flows/
│   ├── extract_statement.py    — the Prefect flow + its tasks
│   └── consumer.py               — RabbitMQ consumer that triggers the flow
└── llm/
    └── client.py                  — OpenAI-compatible client (Groq/Together/HF/self-hosted vLLM)
```

Reuses the backend's models, DB session, and two of its services directly rather than duplicating them:
`app.db.models`, `app.db.session`, `app.services.layout` (fingerprinting + normalization), `app.services.reconciliation`, `app.services.storage`.

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ../backend
pip install -e .
cp ../backend/.env.example ../backend/.env   # shared config — same DB/queue/storage settings

# start the worker (requires infra/docker-compose.yml running, and
# LLM_PROVIDER_API_KEY set for spec induction to actually work)
python -m ledger_lens_pipelines.flows.consumer
```

Uploading a document through the backend API (`POST /documents/upload` → client uploads to the returned URL → `POST /documents/{id}/notify-uploaded`) publishes a message this consumer picks up and turns into a flow run.

## What's tested vs. what needs live infra

**Unit-tested without any infra** (25 tests, `pytest tests/`):
- `chunking.py` — including the exact 2,000-page → 50-chunk case from the architecture doc, and gap-detection localizing a single dropped chunk out of fifty
- `merge.py` — completeness check on top of chunking
- `parser.py` — all three amount conventions (separate debit/credit columns, single signed amount, single amount + flag), thousands-separator/currency stripping, skip-row patterns, and refusing to guess on an unparseable amount
- `spec_induction.validate_spec` — the deterministic sanity-check run on every LLM-proposed spec before it's cached

**Needs live infra to exercise end-to-end** (not run in this environment — no Docker daemon available):
- The full `extract_statement` flow against a real Postgres + MinIO + RabbitMQ stack
- `induce_spec` / `complete_json` against a real LLM endpoint (needs `LLM_PROVIDER_API_KEY`)
- The scanned-statement OCR path (`ocr.extract_scanned_page` is a stub — page rasterization isn't wired up yet)

Run `docker compose -f ../infra/docker-compose.yml up -d`, set `LLM_PROVIDER_API_KEY` in `.env`, and upload a real statement through the backend to exercise the rest.
