# Ledger Lens — backend

FastAPI services for ingestion and retrieval. Fully open-source dependencies — Postgres+pgvector, MinIO, RabbitMQ — no AWS SDK anywhere.

## Layout

```
app/
├── main.py            — FastAPI app, router registration
├── config.py           — settings (env-driven, see .env.example)
├── api/
│   ├── deps.py          — tenant-context dependency (sets the RLS session var per request)
│   ├── schemas.py        — Pydantic request/response models
│   ├── ingestion.py       — upload + document status endpoints
│   └── chat.py            — conversations, messages, the SQL/semantic router in action
├── db/
│   ├── models.py          — SQLAlchemy models (Tenant, Document, DocumentChunk,
│   │                        RawExtractedRow, Transaction, LayoutSpec, Conversation, Message)
│   ├── session.py          — async engine/session factory
│   └── tenant.py           — sets `app.current_tenant_id` for Postgres RLS
└── services/
    ├── layout.py            — layout fingerprinting + CR/Credit/Deposit normalization
    ├── reconciliation.py     — the balance-proof verification logic
    ├── router.py              — SQL-vs-semantic question routing
    ├── storage.py              — MinIO (S3-compatible) client wrapper
    └── queue.py                — RabbitMQ publisher

migrations/0001_initial_schema_and_rls.sql  — pgvector extension + row-level security policies
tests/                                       — unit tests for reconciliation and layout logic
```

## Running locally

```bash
# 1. Start infra (Postgres+pgvector, MinIO, RabbitMQ)
docker compose -f ../infra/docker-compose.yml up -d

# 2. Apply the RLS migration (after tables exist — the app creates them on
#    startup in dev; use Alembic in production instead of create_all)
psql "postgresql://ledgerlens:ledgerlens@localhost:5432/ledgerlens" \
  -f migrations/0001_initial_schema_and_rls.sql

# 3. Install and run
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs` once running.

## What's real vs. scaffolded

**Real and tested** (`tests/`, 39 tests, end to end on the local profile):
- Ingestion API, local upload target, statement list/detail, review and row-correction endpoints (`api/ingestion.py`)
- Document reconciliation anchored on printed balances (`services/statement_proof.py`, `services/reconciliation.py`)
- Question planning and SQL execution over verified rows, with cited evidence (`services/planner.py`, `services/answering.py`, `api/chat.py`)
- Credit signals: cashflow, balances, salary, returned items, other-lender repayments, betting (`services/analytics.py`)
- Tenant scoping on every route (RLS on Postgres, explicit filters everywhere)

- Ask agent (`app/agent/`): LangGraph graph `agent ⇄ tools → verify` with SQL-backed LangChain tools and a grounding verifier (`tests/test_agent.py`, scripted model)
- MCP server (`app/mcp_server.py`): read-only tools for MCP clients, sharing `app/services/ledger_tools.py` with the agent (`tests/test_mcp.py`)

**Not yet real:**
- Auth: `api/deps.get_current_tenant_id` trusts a header. Replace with NextAuth + Keycloak/Supabase Auth before real data.
- Semantic search uses concept and recurrence ranking; pgvector embeddings (`embeddings` extra) are not generated yet.
- The agent has not been run against a live model here (no API key in this environment).
- The Postgres/MinIO/RabbitMQ path is written but not exercised in this environment.
