# Ledger Lens — Architecture

End-to-end: statement ingestion → normalized storage → analytics → user dashboard → chat interface. Fully open-source, no AWS-specific service anywhere in the stack.

## Contents

1. [Data ingestion](#1--data-ingestion)
2. [Extraction & verification](#2--extraction--verification)
3. [Data storage](#3--data-storage)
4. [Analytics](#4--analytics)
5. [Retrieval & chat interface](#5--retrieval--chat-interface)
6. [User & analytics dashboards](#6--user--analytics-dashboards)
7. [Full stack — no AWS anywhere](#7--full-stack--no-aws-anywhere)
8. [Ingestion at scale: concurrency, backpressure, idempotency](#8--ingestion-at-scale-concurrency-backpressure-idempotency)

---

## 1 · Data ingestion

**Upload path**

- Client requests a pre-signed upload URL from the API, then uploads the PDF directly to object storage. File bytes never pass through the application server.
- **Object storage: MinIO** (open source) — an S3-API-compatible object store, self-hosted. Every component that would normally call "S3" calls MinIO instead, using the same S3 SDK.
- On upload completion, MinIO's own bucket-notification feature publishes a message onto the ingest queue — no AWS EventBridge equivalent needed.

**Queueing and job orchestration**

- **Message broker: RabbitMQ or Redis Streams** (open source) — replaces SQS. Durable, self-hosted, with the same core guarantees: at-least-once delivery, visibility timeouts, dead-letter queues.
- **Orchestration: Prefect** (open source, self-hosted) — one flow per document, with a dynamic task fan-out per page-chunk. Tracks retries, concurrency limits, and per-chunk state without hand-rolled bookkeeping.
- A **Splitter** task breaks a large document into 25–50 page chunks, each its own queue message — this is what lets a 2,000-page statement process in parallel across many workers instead of one long sequential job.

**Concurrency & backpressure**

- OCR workers are pull-based: each requests one chunk, finishes it, requests the next. The pool self-limits to its own capacity — no separate throttle needed on the queue side.
- The one deliberately rate-limited resource is the LLM spec-induction call (see §2) — a token bucket caps how often it's invoked, since it's the only externally-metered, costed step in the pipeline.
- The chunk queue is partitioned by `tenant_id` so one customer's large statement can't starve every other customer's smaller uploads behind it.

## 2 · Extraction & verification

The LLM appears exactly twice — never in the per-page hot path.

```
Page-chunk (OCR) → Layout fingerprint → [cache hit]  → Deterministic parse
                                       → [cache miss] → Spec induction (LLM, once per layout)
                                                              │
                                                              ▼
                                                     Deterministic parse
                                                              │
                                                              ▼
                                                       Reconciliation
                                                        │         │
                                                  [100% pass]  [row fails]
                                                        │         │
                                                        ▼         ▼
                                                    Postgres   Targeted repair (LLM, rare)
                                                                    │
                                                              still failing → Review queue
```

1. **OCR / text extraction** — pdfplumber and PyMuPDF for digital PDFs, **PaddleOCR** (open source) for scanned statements. No cloud OCR service.
2. **Layout fingerprint** — hash of the header row + column structure, checked against a cache.
3. **Spec induction (AI, cache-miss only)** — on an unseen layout, 2 sample pages go to an LLM, which returns a strict JSON parsing spec: column mapping, date format, credit/debit markers. Validated against a 3rd held-out page before being cached, permanently, keyed on the layout fingerprint.
4. **Deterministic parse** — the cached spec is applied in code across every chunk. No AI, no tokens.
5. **Reconciliation** — every row checked: `balance[n] == balance[n-1] − debit[n] + credit[n]`. 100% reconciled → auto-accepted. Any failing row → targeted repair (AI, on that single row) or a human review queue — never silently trusted.

**Where the LLM itself runs**

- **Embeddings: BGE or E5** via `sentence-transformers` (open source) — runs on CPU at this scale, no GPU required.
- **Chat / spec-induction LLM: open-weight models** (Llama 3.1/3.3, Qwen2.5) — served via a managed open-weight inference provider (Groq, Together, HF Inference Providers) early on, or self-hosted via **vLLM/Ollama** once volume justifies owning the GPU.

**Why the "200+ bank configs" problem shrinks**

Specs are induced automatically, not hand-written — nobody manually onboards a bank. And critically: many banks run the same underlying core banking platform (Finacle, T24/Temenos, Flexcube), so banks on the same platform share a statement layout. The number of *distinct layouts* is much smaller than the number of banks — expect roughly 20–40 layouts to cover the large majority of real volume, reached automatically as documents flow through the system.

## 3 · Data storage

**Postgres + pgvector** (open source) — a single self-hosted Postgres instance holds everything:

- **Structured table** (`transactions`) — canonical rows, fully SQL-queryable: filters, date ranges, `SUM`/`GROUP BY` aggregation. Answers "total debits in March" directly.
- **Vector column** (`pgvector` extension) — each transaction (or small cluster) rendered as a natural-language sentence and embedded, for fuzzy/semantic questions ("which look like subscriptions").
- **Full-text** (`tsvector`) — native Postgres keyword search, usable alongside vector search for hybrid ranking without a second search system.

**Multi-tenancy** — Postgres Row-Level Security, scoped on `tenant_id`, enforced at the database layer, not in application code. Even a bug in query-routing logic can't leak one customer's data into another's results.

**Immutability & audit** — raw extracted rows are kept in a separate immutable staging log, never overwritten; the canonical table is derived from it. This preserves a full audit trail of what was extracted, when, from which document version, with what reconciliation score.

## 4 · Analytics

Every credit-risk metric is SQL. The LLM never computes a number.

- Average monthly inflow/outflow, net cashflow, month-over-month consistency
- Salary detection — recurring credits of similar amount, consistent day of month
- Average/minimum/closing balance, balance volatility
- Returned/bounced items — narration matching (`RTN`, `NSF`, `REVERSAL`)
- Existing loan repayments to other lenders, betting/gambling spend — narration-pattern matching
- Counterparty concentration, transaction frequency

These are materialized as SQL views (or a lightweight dbt project) over the `transactions` table — deterministic, re-runnable, and defensible to a regulator or credit officer in a way "the model computed it" never is.

The one legitimate re-entry point for AI is **narration enrichment** — mapping a messy narration string to a merchant/category — done once per unique narration pattern and cached, converging to a small, mostly-static set across a whole portfolio.

## 5 · Retrieval & chat interface

A router decides SQL vs. semantic search per question — the corpus is never dumped into context.

- **Router** — a lightweight classifier (rule-based keyword check, or a cheap LLM call) decides: aggregation/filter question → SQL path; fuzzy/semantic question → vector search path.
- **SQL path** — text-to-SQL (or a constrained query builder) against the structured table. The LLM never does the arithmetic itself.
- **Semantic path** — today, concept and recurrence ranking over verified rows. Target: pgvector similarity search over transaction narratives (the embedding column exists), optionally reranked with **bge-reranker**, before the top ~10–20 rows go to the model.
- **Agent** — a LangGraph tool-calling graph (`agent ⇄ tools → verify`, `backend/app/agent/`). The model chooses among SQL-backed LangChain tools (`query_transactions`, `list_statements`, `statement_proof`, `workspace_overview`) and phrases the reply; a verify node rejects any reply containing a figure that no tool returned, falling back to the deterministic answer. KPIs and evidence come from the tools' structured artifacts, not the model's text. Runs when an LLM key is configured (`AGENT_MODE=auto`); otherwise the deterministic planner answers directly.
- **MCP server** — the same read-only operations exposed to external agents (Claude Desktop, Claude Code, IDEs) through the official MCP Python SDK over stdio (`backend/app/mcp_server.py`).
- **Chat UI** — Next.js: conversation history sidebar, answer bubbles with a routing tag ("routed to SQL aggregation" / "routed to semantic search"), and a source-evidence panel showing the exact retrieved rows behind every answer.

Every answer traces back to specific rows — the same principle as the reconciliation proof in ingestion: nothing the user sees is trusted without a visible source.

## 6 · User & analytics dashboards

- **Customer/user dashboard** — Next.js, reading directly from the analytics SQL views: cashflow charts, risk indicators, document status (processing / reconciled / needs review), all scoped by RLS to the logged-in tenant.
- **Internal credit/risk team dashboard** — a separate view/role over the same views, plus the review queue for documents that failed reconciliation, and visibility into the layout-spec cache.
- **Auth** — NextAuth (open source), backed by Keycloak or Supabase Auth (open source) instead of a cloud identity provider.

## 7 · Full stack — no AWS anywhere

| Layer | Component | Replaces |
|---|---|---|
| Object storage | MinIO | S3 |
| Queue / broker | RabbitMQ / Redis Streams | SQS |
| Orchestration | Prefect (self-hosted) | Step Functions / MWAA |
| OCR | pdfplumber, PyMuPDF, PaddleOCR | Textract |
| Database | Postgres + pgvector | RDS + OpenSearch/Kendra |
| Embeddings | BGE / E5 (sentence-transformers) | Bedrock embeddings |
| Reranking | bge-reranker | — |
| LLM inference | Llama/Qwen via Groq, Together, HF, or self-hosted vLLM/Ollama | Bedrock / SageMaker |
| Agent orchestration | LangGraph (LangChain tool and model interfaces) | Bedrock Agents |
| Agent tool access | MCP server (official Python SDK) | — |
| Backend API | FastAPI | API Gateway + Lambda |
| Frontend | Next.js | Amplify |
| Auth | NextAuth + Keycloak / Supabase Auth | Cognito |
| Container hosting | Docker Compose (local) → self-managed Kubernetes/Nomad (scale) | ECS / EKS / Fargate |

Every row in this table can run on a single VPS or a small self-managed cluster — nothing here requires a specific cloud vendor, which matters both for cost control and for the data-residency story with banks and regulators.

## 8 · Ingestion at scale: concurrency, backpressure, idempotency

**Orchestration** — Prefect runs one flow per document, with a dynamic `.map()` over the chunk list produced by the Splitter. This gives per-task retry policies, concurrency limits, and a queryable record of every chunk's state (pending / running / succeeded / failed) without hand-rolled bookkeeping.

**Idempotency** — every chunk has a deterministic id: `hash(document_id + page_start + page_end)`. Before processing, a worker checks a `processed_chunks` table (or Redis set) for that id:

- Present with `status = done` → skip, return the cached result (safe against redelivery).
- Absent, or `status = failed` → process normally, then mark done.

This makes at-least-once queue delivery behave like exactly-once *processing*, without needing a heavier exactly-once-delivery system.

**No silently dropped pages** — a completeness check runs after all chunks for a document report a terminal state:

1. Compute expected chunk count: `ceil(total_pages / chunk_size)`.
2. Compare against chunks actually marked `done`.
3. Verify page ranges are contiguous — no gaps, no overlaps.
4. Any gap auto-requeues just the missing page range, not the whole document.

A document only moves to reconciliation once this check passes.

**Retry policy** — exponential backoff, capped at 3 attempts per chunk, then to a dead-letter queue. A single corrupted page (a poison pill) can't block the rest of the document.

**Ordering** — chunks are processed out of order on purpose; order is reconstructed once, at the Merger step, using each chunk's `page_start`/`page_end` metadata. This is what lets throughput scale horizontally with zero coordination overhead between workers.

**Throughput control** — OCR is CPU-bound, so scaling is horizontal (more worker pods/processes), autoscaled against queue depth. Chunk size (pages per unit of work) is the main tuning knob — 25–50 pages is a reasonable starting point.

### Guarantees this gives

| Failure mode | What prevents it |
|---|---|
| Duplicate page processed twice | Deterministic chunk id + idempotency check before processing |
| Page silently dropped | Completeness check (expected vs. actual chunk count, contiguous ranges) before a document can reconcile |
| One bad page blocks the whole document | Chunk-level retries + dead-letter queue, isolated from sibling chunks |
| One customer's huge document starves others | Per-tenant partitioned/fair queuing on the chunk queue |
| OCR fleet overwhelmed by a traffic spike | Pull-based worker model + queue absorbing the burst, not the workers |
| Wrong numbers reach a credit decision | Row-by-row balance reconciliation gates promotion to the canonical table |
