# Ledger Lens

A multi-bank transaction intelligence platform. Customers upload or link bank statements from any bank — regardless of how that bank labels a credit or debit — and ask plain-language questions about their finances. Answers are backed by a visible source: the exact rows a question was answered from, never a black box.

Ledger Lens exists to solve three problems at once:

1. **Every bank labels transactions differently.** One bank uses `CR`/`DR`, another `Credit`/`Debit`, another `Deposit`/`Withdrawal`. Ledger Lens normalizes all of it into one canonical schema at ingestion time — once, not on every query.
2. **Sending an entire statement to an LLM on every question is slow, expensive, and produces wrong numbers.** A 2,000-page statement can cost dollars per query and the model still can't reliably sum a column of numbers over that much context. Ledger Lens computes every number with SQL and only ever shows the LLM the handful of rows relevant to one question.
3. **Extraction has to be provably correct, not just plausible.** Every bank statement carries a running balance. Ledger Lens verifies every extracted row against it — `opening + credits − debits = closing` — before any number reaches a user or a lending decision. A document that fails reconciliation goes to review, not into production data.

Everything below runs on open-source infrastructure. No AWS-specific service is required anywhere in the stack — see [Vendor substitutions](#vendor-substitutions).

## Contents

- [Architecture](#architecture)
- [Repository layout](#repository-layout)
- [Getting started](#getting-started)
- [How ingestion works](#how-ingestion-works)
- [How retrieval works](#how-retrieval-works)
- [The Ask agent (LangGraph)](#the-ask-agent-langgraph)
- [MCP server](#mcp-server)
- [Multi-tenancy](#multi-tenancy)
- [Vendor substitutions](#vendor-substitutions)
- [Status](#status)

## Architecture

Ledger Lens is one system across five layers: ingestion, extraction & verification, storage, analytics, and retrieval/chat. The full architecture — diagrams, component rationale, and the complete open-source stack table — lives in [`docs/architecture.md`](docs/architecture.md).

The short version:

```
Upload ──▶ Object storage ──▶ Ingest queue ──▶ Splitter ──▶ Chunk queue
                                                                  │
                     ┌────────────────────────────────────────────┘
                     ▼
     Layout fingerprint ──▶ [cache hit] ──▶ Deterministic parse
              │                                     │
        [cache miss]                                ▼
              ▼                              Reconciliation check
      Spec induction (LLM,                          │
      once per new layout)              ┌───────────┴───────────┐
              │                         ▼                       ▼
              └──────────────▶   Postgres (canonical)    Review queue
                                         │                (failed rows)
                                         ▼
                          Analytics views (pure SQL)
                                         │
                                         ▼
                    Router: SQL aggregation  ⟷  pgvector semantic search
                                         │
                                         ▼
                              Chat interface + evidence panel
```

The LLM appears in three places: writing a parsing spec the first time a new bank-statement layout is seen (cached forever after), repairing the rare row that fails reconciliation, and (optionally) the Ask agent, which decides which SQL tools to call and phrases the reply. It never reads a full statement and never computes a financial total: those are SQL, and the agent's reply is rejected if it contains a figure no tool returned.

## Repository layout

```
ledger-lens/
├── README.md                 — this file
├── docs/
│   └── architecture.md       — full architecture writeup (ingestion → chat)
├── frontend/                 — Next.js chat interface + dashboards
├── backend/                  — FastAPI services (ingestion API, retrieval API)
├── pipelines/                — Prefect flows (extraction, spec induction, reconciliation)
├── samples/                  — sample statement PDFs, manifest of expected results, ground truth
├── scripts/                  — dev_api.py, mcp_server.py, make_samples.py, upload_samples.py
├── video/                    — Remotion launch videos rendered from the app's components
└── infra/                    — Docker Compose / self-hosted service definitions
```

## Getting started

### Quick start (no Docker)

The **local profile** runs the whole product on one machine: SQLite instead of Postgres, a folder instead of MinIO, and an in-process queue instead of RabbitMQ. The extraction, reconciliation and retrieval code is the same code the full stack runs.

```bash
# Python 3.11+ and Node 20+
python3 -m venv pipelines/.venv
pipelines/.venv/bin/pip install -e "backend[dev,local,agent,mcp]" -e "pipelines[dev]"

# API on :8000. Seeds a demo workspace by pushing four synthetic PDF statements
# (three bank layouts, one with a misprinted amount) through the real pipeline.
pipelines/.venv/bin/python scripts/dev_api.py

# Web app on :3000 (second terminal)
cd frontend && npm install && npm run dev
```

Open http://localhost:3000, choose **Open the demo**, then try:

- **Overview**: cashflow, balances, detected salary and risk signals, all computed in SQL over verified rows.
- **Ask**: "What were my total debits in August 2026?", "Which of my payments look like subscriptions?". Open the evidence to see the rows and the query plan.
- **Statements**: one statement is held for review. Correct the flagged row and the whole statement is re-proven. **Try a sample** uploads a statement in a fourth layout the system has not seen, so you can watch it learn a layout.

Delete `backend/.ledgerlens/` to reset the demo.

**Sample statements:** `samples/statements/` has nine ready-made PDFs covering five bank layouts, a 73-page multi-chunk statement, a misprinted statement and two files that must fail. Each comes with expected outcomes and a ground-truth CSV. `scripts/upload_samples.py` pushes them through the API and checks every result. See [`samples/README.md`](samples/README.md).

With no `LLM_PROVIDER_API_KEY`, new layouts are learned from header heuristics and answers are templated from SQL results. Set a key (Groq, Together, or a local vLLM/Ollama endpoint) to use an LLM for spec induction and targeted row repair.

### Full stack

```bash
docker compose -f infra/docker-compose.yml up -d     # Postgres + pgvector, MinIO, RabbitMQ
cp backend/.env.example backend/.env
psql "postgresql://ledgerlens:ledgerlens@localhost:5432/ledgerlens" -f backend/migrations/0001_initial_schema_and_rls.sql
psql "postgresql://ledgerlens:ledgerlens@localhost:5432/ledgerlens" -f backend/migrations/0002_statement_balances_and_repairs.sql
cd backend && uvicorn app.main:app                    # API
python -m ledger_lens_pipelines.flows.consumer        # extraction worker (Prefect)
```

### Tests

```bash
cd backend   && PYTHONPATH=.:../pipelines ../pipelines/.venv/bin/python -m pytest   # 52 tests
cd pipelines && PYTHONPATH=../backend:. .venv/bin/python -m pytest                # 33 tests
cd frontend  && npm run lint && npm run build
```

The backend suite is end to end: it renders statements to PDF, runs them through extraction and reconciliation, asks questions over HTTP, and checks every figure against totals computed independently from the source data. It also covers the review loop, uploads, upload validation, and tenant isolation.

> `PYTHONPATH` is set explicitly because some macOS setups flag a virtualenv's editable-install `.pth` files as hidden, and Python 3.13+ ignores hidden `.pth` files.

## How ingestion works

1. A statement (PDF, any length) is uploaded directly to object storage via a pre-signed URL — never through the application server.
2. A Prefect flow splits it into page-range chunks and processes them in parallel.
3. Each chunk's layout is fingerprinted (a hash of its header row and column structure) and checked against a cache of known bank-statement layouts.
4. On a cache hit, the chunk is parsed deterministically — no AI, no tokens.
5. On a cache miss (a genuinely new layout), a small LLM call reads 2 sample pages and writes a structured parsing spec, which is validated and cached against that layout's fingerprint permanently. Because many banks share the same core banking platform (Finacle, T24, Flexcube, etc.), the number of *distinct layouts* is far smaller than the number of banks — this cache converges quickly.
6. Every parsed row is reconciled against the statement's running balance before being promoted into the canonical `transactions` table. Anything that doesn't reconcile is routed to a review queue, never silently trusted.

Full detail, including concurrency, idempotency, and how the pipeline avoids dropping or duplicating pages at scale, is in [`docs/architecture.md`](docs/architecture.md).

## How retrieval works

Every question is routed, not blindly answered:

- **Aggregation/filter questions** ("total debits in March") are answered with SQL directly against the structured `transactions` table — the LLM never does the arithmetic.
- **Fuzzy/semantic questions** ("which of these look like subscriptions") are answered by ranking verified rows on concept matches and recurrence (the same narration on three or more months at a stable amount reads as a subscription). The schema carries a `pgvector` embedding column for similarity search on the full stack, but embeddings are not generated yet.

Every answer in the chat interface carries a visible source: the exact rows it was derived from, shown in an evidence panel alongside the answer.

## The Ask agent (LangGraph)

Ask can run as a **LangGraph** tool-calling agent (`backend/app/agent/`). The model plans; SQL does the maths; a verifier decides whether the model's words are allowed through.

```
question ─▶ agent ⇄ tools ─▶ verify ─▶ answer
            (LLM)   (SQL)    (grounding check)
```

- **agent:** an OpenAI-compatible chat model (Groq, Together, vLLM, Ollama) via `langchain-openai`, with four tools bound.
- **tools:** LangChain tools run by LangGraph's `ToolNode`: `query_transactions` (the planner + SQL over verified rows), `list_statements`, `statement_proof`, `workspace_overview`. Each returns text for the model and a structured artifact for the app.
- **verify:** every number in the reply must appear in a tool result or the question. A reply that invents, rounds or recomputes a figure, or answers without calling a data tool, is discarded and the deterministic SQL answer is shown instead.
- **KPIs and evidence rows come from the tools' artifacts, never from the model's text.** The Query plan tab shows the agent's tool calls and the grounding verdict.

`AGENT_MODE=auto` (default) runs the agent when `LLM_PROVIDER_API_KEY` is set and the deterministic planner otherwise. `on`/`off` force it. Any agent error falls back to the deterministic answer.

Tests drive the graph with a scripted chat model (`tests/test_agent.py`): grounded replies pass, a hallucinated figure is rejected, an answer without tools is rejected, multi-tool questions work, and the chat API reports which engine answered. The agent has not yet been run against a live model in this repository's CI.

## MCP server

`backend/app/mcp_server.py` exposes a workspace to any MCP client (Claude Desktop, Claude Code, IDE agents) over stdio, built on the official Python SDK (`mcp` 2.x, `MCPServer`). Tools are read-only (annotated `readOnlyHint`) and run the same operations as the app (`app/services/ledger_tools.py`), so a client sees the same numbers as the UI:

| Tool | Returns |
|---|---|
| `ask(question)` | Answer, figures, filters, and the evidence rows, from SQL over reconciled statements |
| `list_statements()` | Each statement's bank, status and whether it counts in answers |
| `statement_proof(statement)` | Opening + credits − debits vs printed closing, plus rows that fail the running-balance check |
| `workspace_overview()` | Monthly in/out, balances, detected salary, risk signals |

```bash
pipelines/.venv/bin/python scripts/mcp_server.py   # stdio; run the API once first so the demo workspace exists
```

Claude Desktop / Claude Code config:

```json
{
  "mcpServers": {
    "ledger-lens": {
      "command": "/path/to/ledger-lens/pipelines/.venv/bin/python",
      "args": ["/path/to/ledger-lens/scripts/mcp_server.py"]
    }
  }
}
```

`tests/test_mcp.py` calls every tool through an in-process MCP client. The stdio transport has also been exercised end to end against the demo database.

## Multi-tenancy

Tenant isolation is enforced at the database layer via Postgres Row-Level Security, not in application code — every query, structured or semantic, is scoped to the caller's `tenant_id` by the database itself. A bug in query-routing logic cannot leak one customer's data into another's results.

## Vendor substitutions

Ledger Lens is built entirely on open-source infrastructure. Where a typical implementation might reach for a specific cloud vendor's managed service, Ledger Lens uses:

| Layer | Ledger Lens uses | Instead of |
|---|---|---|
| Object storage | MinIO | S3 |
| Queue / broker | RabbitMQ or Redis Streams | SQS |
| Orchestration | Prefect (self-hosted) | Step Functions / MWAA |
| OCR | pdfplumber, PyMuPDF, PaddleOCR | Textract |
| Database | Postgres + pgvector | RDS + OpenSearch/Kendra |
| Embeddings | BGE / E5 via sentence-transformers | Bedrock embeddings |
| LLM inference | Llama / Qwen via Groq, Together, HF, or self-hosted vLLM/Ollama | Bedrock / SageMaker |
| Agent orchestration | LangGraph (LangChain tool and model interfaces) | Bedrock Agents |
| Agent tool access | MCP server (official Python SDK) | — |
| Backend API | FastAPI | API Gateway + Lambda |
| Frontend | Next.js | Amplify |
| Auth | NextAuth + Keycloak / Supabase Auth | Cognito |
| Container hosting | Docker Compose → self-managed Kubernetes/Nomad | ECS / EKS / Fargate |

This matters for two reasons: cost control at scale, and a clean data-residency story when talking to banks and regulators about where financial data actually lives.

## Status

**Working and tested (local profile):**
- Upload → chunking → layout fingerprint → spec induction (LLM or heuristic) → deterministic parse → row and document reconciliation → promotion, idempotent and gap-checked
- Spec cache reuse across documents with the same layout (verified: no new induction for a known layout)
- Review queue: failing rows show the amount the printed balance implies; corrections are re-proven by the same arithmetic; accept is refused until the statement reconciles
- Chat: deterministic query planner (intent, type, month/quarter/range, bank, amount bounds, narration) executed as SQL over verified rows only, with coverage notes and cited rows
- Semantic path: concept and recurrence ranking (subscriptions, loans, betting, returned items) over verified rows
- Analytics: monthly in/out, month-end balances, salary detection, returned items, other-lender repayments, betting, counterparty concentration
- Frontend: landing page, demo sign-in, Overview, Ask with evidence panel, Statements with upload and review; responsive, light and dark, keyboard accessible
- Ask agent: LangGraph tool-calling loop over the SQL tools with a grounding verifier and deterministic fallback (tested with a scripted model)
- MCP server: four read-only tools over stdio, tested in-process and over a real stdio subprocess

**Built but not exercised here:** the full-stack path (Postgres RLS, MinIO, RabbitMQ, Prefect worker) and every live LLM call (spec induction, row repair, the Ask agent), which need Docker and an API key.

**Not built yet:** real SSO (the API trusts a dev-only `X-Tenant-Id` header), scanned-PDF OCR, pgvector embeddings for the semantic path, multi-currency, audit log. See [`docs/PRD.md`](docs/PRD.md).

See [`backend/README.md`](backend/README.md) and [`pipelines/README.md`](pipelines/README.md) for what's real vs. scaffolded in each layer.
