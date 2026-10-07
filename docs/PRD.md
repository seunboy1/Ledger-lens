# Ledger Lens — Product Requirements Document

| | |
|---|---|
| **Status** | Draft v0.3 (adds the Ask agent and MCP server) |
| **Date** | 2026-09-30 |
| **Owner** | Oluwaseun Adeyo |
| **Related** | [`README.md`](../README.md) · [`docs/architecture.md`](architecture.md) · [`DESIGN.md`](../DESIGN.md) · [`reports/`](../reports/) |

---

## 1 · Summary

Ledger Lens turns bank statements from any bank into verified, queryable transaction data. Lending and credit teams can then ask plain-language questions ("What were total debits in March across all accounts?") and get answers that are **computed with SQL, proven against the statement's own running balance, and shown with the exact rows they came from.**

It replaces the current practice of pasting whole statements into an LLM, which is slow, costs money on every question and produces wrong totals. Instead, an LLM is used once per new statement layout to learn how to parse it, and a deterministic, reconciled pipeline does everything else.

---

## 2 · Problem

Lenders, especially in Nigeria and other markets where open-banking coverage is partial, underwrite on bank statements submitted as PDFs. Today:

1. **Every bank formats statements differently.** Column orders, date formats and credit/debit conventions (`CR`/`DR`, `Credit`/`Debit`, `Deposit`/`Withdrawal`, signed amounts) vary by bank and by core-banking platform. Template-based parsers need constant hand maintenance.
2. **LLM-per-document extraction is expensive and unreliable.** A long statement costs real money per query, and models can't reliably sum hundreds of rows. One missed or sign-flipped row silently corrupts every balance after it.
3. **Credit decisions need provenance.** A credit officer, auditor or regulator needs to know *where a number came from*. "The model said so" is not defensible.
4. **Open banking doesn't remove the PDF.** Our vendor research (`reports/Bank statement extraction vendor research.md`) found that Okra shut down in 2025, Stitch's Nigeria coverage can't be verified, and Mono is viable only for customers willing to link accounts. A large segment will keep submitting PDFs, so account linking adds to PDF extraction rather than replacing it.

---

## 3 · Goals and non-goals

### Goals
- **G1 — Correct numbers.** Every figure shown is computed in SQL over rows that passed balance reconciliation, or is explicitly marked as unverified.
- **G2 — Any bank, no manual onboarding.** A new statement layout is learned automatically on first sight and cached, so no one hand-writes bank configs.
- **G3 — Low marginal cost.** No LLM call in the per-page hot path. LLM cost scales with the number of *new layouts* and *failed rows*, not with pages or questions.
- **G4 — Visible evidence.** Every answer shows its route, its query plan, its tenant scope and the rows behind it.
- **G5 — Tenant isolation by construction.** Postgres Row-Level Security enforces isolation, not application code.
- **G6 — Self-hostable.** An open-source stack with no cloud-vendor lock-in, which supports the data-residency conversations with banks and regulators.

### Non-goals (v1)
- Making lending decisions or producing a credit score. We supply verified metrics, and the lender decides.
- Consumer personal-finance features (budgets, goals).
- Payments, money movement or account management.
- Building our own open-banking aggregator. We integrate one (Mono) instead.
- Fraud and tamper detection on PDFs (see §12 Future).
- Non-statement documents (payslips, invoices, KYC packs).

---

## 4 · Users and personas

| Persona | Who | Needs | Primary surfaces |
|---|---|---|---|
| **Credit analyst** (primary) | Works a queue of loan applications at a lender, e.g. the "Meridian Capital" demo tenant | Upload an applicant's statements, get income, spend, balance and risk signals fast, and answer ad-hoc questions with proof | Upload, chat + evidence, borrower dashboard |
| **Credit officer / approver** | Signs off on the decision | A trustworthy summary and the ability to drill into any number | Borrower dashboard, evidence panel |
| **Ops / review specialist** (internal) | Handles documents that failed reconciliation | See exactly which row failed and why, fix or reject it, with an audit trail | Review queue, layout-spec viewer |
| **Workspace admin** | IT or ops lead at the lender | SSO, members and roles, data retention | Settings |
| **Auditor / regulator** (indirect) | Reviews decisions after the fact | Reproducible lineage from answer → rows → document → page | Exported evidence, audit log |

---

## 5 · Key user stories

**Ingestion**
- As an analyst, I can drag in one or more PDF statements of any length and see each one's progress, so I know when data is ready.
- As an analyst, I see each document marked **Reconciled**, **Needs review** or **Failed**, and I never have to guess whether data is trustworthy.
- As an analyst, I'm told when an answer excludes documents that are still processing or under review.

**Asking questions**
- As an analyst, I can ask "total debits in March", "largest 5 credits last quarter", "average balance in Q2" or "payments to Zenith Bank over ₦500k" and get a number with KPI tiles.
- As an analyst, I can ask fuzzy questions ("which of these look like loan repayments to other lenders?") and get a ranked list of matching rows.
- As an analyst, for any answer I can open the evidence panel to see the rows, the raw bank label next to the normalized type, and the query plan (filters, route, tenant scope).
- As an analyst, I can give thumbs-down feedback with a reason, so bad answers get fixed.

**Analytics**
- As a credit officer, I can open a borrower view showing monthly inflow/outflow, salary detection, balance stats, bounced items, other-lender repayments, betting spend and counterparty concentration, and click any metric to see its rows.

**Review (internal)**
- As a reviewer, I see the failing row next to a crop of the source page, with the expected vs. extracted balance. I can accept an AI-proposed repair, edit the row or reject the document, and every action is logged.
- As a reviewer, I can see which layouts are cached, how many documents used each one, and its failure rate.

**Workspace**
- As an admin, I can sign my team in via Google Workspace or Microsoft SSO and assign Analyst, Reviewer or Admin roles.

---

## 6 · Functional requirements

Priority: **P0** = required for pilot, **P1** = required for GA, **P2** = later.

### 6.1 Ingestion
| ID | Requirement | Pri | Status |
|---|---|---|---|
| ING-1 | Upload PDFs directly to object storage via a pre-signed URL. File bytes never pass through the API. | P0 | Built (`POST /documents/upload`, `notify-uploaded`) |
| ING-2 | Split documents into page-range chunks (default 40) processed in parallel | P0 | Built (`chunking.py`) |
| ING-3 | Idempotent chunk processing using a deterministic chunk ID | P0 | Built |
| ING-4 | Completeness check: no gaps or overlaps, and requeue only the missing ranges | P0 | Built (`merge.py`) |
| ING-5 | Document status API: uploading, processing (with chunk progress), reconciled, needs_review, failed | P0 | Built (API + Statements UI with polling) |
| ING-6 | Text extraction for digital PDFs (pdfplumber / PyMuPDF) | P0 | Built |
| ING-7 | OCR for scanned statements (PaddleOCR) | P1 | Stub |
| ING-8 | Password-protected PDFs: prompt the user for the password, never store it | P1 | Not started |
| ING-9 | Per-tenant fair queuing so one large upload can't starve others | P1 | Designed |
| ING-10 | Account linking via Mono as an alternative source, normalized into the same schema | P2 | Not started |
| ING-11 | Deduplicate overlapping statements (the same account and period uploaded twice) | P1 | Not started |

### 6.2 Extraction and verification
| ID | Requirement | Pri | Status |
|---|---|---|---|
| EXT-1 | Layout fingerprint (header + column structure) with a spec-cache lookup | P0 | Built |
| EXT-2 | On a cache miss, an LLM induces a strict JSON parsing spec from 2 sample pages, which is validated on a 3rd held-out page before caching. Rate-limited with a token bucket. | P0 | Built; heuristic fallback when no LLM key (LLM path untested here) |
| EXT-3 | Deterministic parse supporting separate debit/credit columns, a single signed amount, and an amount + flag | P0 | Built |
| EXT-4 | Normalize transaction type to canonical credit/debit, and **reject unknown labels rather than guess** | P0 | Built |
| EXT-5 | Row-level reconciliation `balance[n] = balance[n−1] − debit + credit` plus a document-level `opening + credits − debits = closing` | P0 | Built, anchored on the printed opening balance |
| EXT-6 | Only fully reconciled rows are promoted to the canonical `transactions` table. Raw rows are kept in an immutable staging log. | P0 | Built |
| EXT-7 | Targeted LLM repair of a single failing row. The repaired row is flagged "AI-repaired" until a human confirms it. | P1 | Built; repaired rows flagged until a human confirms (LLM path untested here) |
| EXT-8 | Anything still failing goes to a human review queue | P0 | Built (review queue UI with implied-amount suggestion) |
| EXT-9 | Detect layout drift: invalidate or version a cached spec when its failure rate spikes | P1 | Not started |
| EXT-10 | Multi-currency: capture currency per account and never sum across currencies | P1 | Not started |

### 6.3 Retrieval and chat
| ID | Requirement | Pri | Status |
|---|---|---|---|
| CHAT-1 | Conversations: create, list, rename, delete, history | P0 | Built |
| CHAT-2 | Router: SQL aggregation vs. semantic search per question | P0 | Rule-based router built |
| CHAT-3 | Deterministic planner → `QueryPlan` (intent, type, date range, bank, amount bounds, keywords, limit) → SQL | P0 | Built; plan filters applied in SQL |
| CHAT-4 | Intents: total, count, average, largest, smallest, balance, list | P0 | Built |
| CHAT-5 | The LLM never computes numbers. It only phrases the answer from SQL results. | P0 | By design |
| CHAT-6 | Semantic path: embeddings (BGE/E5) on each transaction's rendered sentence, pgvector search, optional bge-reranker, and the top ~10–20 rows passed to the LLM | P1 | Partial: concept + recurrence ranking; pgvector embeddings not wired |
| CHAT-7 | Every answer returns route, KPIs, source summary, evidence rows, query-plan lineage and isolation note | P0 | Built |
| CHAT-8 | Wire the frontend to the real API (it currently uses `sample-data.ts`) | P0 | Built |
| CHAT-9 | Clarifying question when the plan is ambiguous ("March of which year?") instead of guessing | P1 | Not started |
| CHAT-10 | Answers state their coverage: accounts, period, and any excluded unreconciled documents | P0 | Built |
| CHAT-11 | Feedback with a reason, stored against the message and its plan | P1 | Built (helpful / not helpful stored per message) |
| CHAT-12 | Streaming responses | P2 | Not started |
| CHAT-13 | Export evidence rows as CSV | P1 | Not started |
| CHAT-14 | Ask agent: LangGraph tool-calling loop over the SQL tools; replies whose figures are not in a tool result are rejected and replaced by the deterministic answer; KPIs and evidence always come from tools | P1 | Built; tested with a scripted model, not yet with a live LLM |
| CHAT-15 | MCP server exposing read-only workspace tools (ask, statements, proofs, overview) to external agents | P2 | Built; tested in-process and over stdio |

### 6.4 Analytics and dashboards
| ID | Requirement | Pri | Status |
|---|---|---|---|
| ANA-1 | SQL views: monthly inflow/outflow, net cashflow, MoM consistency | P1 | Built as SQL queries (not yet materialized views) |
| ANA-2 | Salary detection (recurring credits of similar amount on a consistent day) | P1 | Built |
| ANA-3 | Balance stats: average, minimum, closing, volatility | P1 | Built |
| ANA-4 | Returned/bounced items (`RTN`, `NSF`, `REVERSAL`) | P1 | Built |
| ANA-5 | Other-lender repayments and betting/gambling spend via narration patterns | P1 | Built |
| ANA-6 | Counterparty concentration and transaction frequency | P2 | Partial: counterparty concentration |
| ANA-7 | Narration enrichment (merchant/category), cached per unique narration pattern | P2 | Not started |
| ANA-8 | Borrower dashboard. Every metric links to its rows. | P1 | Built (Overview) |
| ANA-9 | Internal dashboard: review queue, layout-spec cache, pipeline health | P1 | Not started |

### 6.5 Platform, security and admin
| ID | Requirement | Pri | Status |
|---|---|---|---|
| SEC-1 | Tenant isolation via Postgres RLS on every tenant table, with the session var set per request | P0 | Built |
| SEC-2 | Real authentication: NextAuth + Keycloak/Supabase Auth with Google and Microsoft SSO and email. Replace the `X-Tenant-Id` header stub. | P0 | **Stub** — must ship before any real data |
| SEC-3 | Roles: Analyst, Reviewer, Admin | P1 | Not started |
| SEC-4 | Audit log of uploads, questions, review actions and exports | P1 | Not started |
| SEC-5 | Encryption at rest (DB, object store) and TLS everywhere | P0 | Infra-dependent |
| SEC-6 | Data retention and deletion per tenant policy, including deleting a borrower's documents and derived rows | P1 | Not started |
| SEC-7 | Local single-machine profile (SQLite, local dir, in-process queue) for demos and dev | P0 | Built, with seeded demo workspace |
| SEC-8 | NDPR/NDPA (Nigeria Data Protection Act) compliance review before the pilot | P0 | Not started |

---

## 7 · Non-functional requirements

| Area | Target |
|---|---|
| **Accuracy** | 100% of promoted rows pass reconciliation, by construction. Reconciliation pass rate on first attempt ≥ 95% of documents for cached layouts. |
| **Answer correctness** | ≥ 99% of SQL-path answers match a hand-computed total on the eval set (§9) |
| **Ingestion latency** | A 50-page digital statement is reconciled in < 60s p95 on a cached layout. A 2,000-page statement in < 10 min with the default worker pool. |
| **Query latency** | SQL-path answers < 2s p95. Semantic-path answers < 5s p95. |
| **Cost** | LLM spend per document on a cached layout ≈ $0. Blended cost per statement page well below the $0.02–0.05/page charged by structured-extraction vendors (see research report). |
| **Availability** | 99.5% for the pilot, 99.9% for GA |
| **Isolation** | Zero cross-tenant reads. Covered by automated RLS tests that attempt cross-tenant access. |
| **Accessibility** | WCAG 2.1 AA (see `DESIGN.md` §10) |
| **Portability** | The whole stack runs on Docker Compose on a single VPS. No managed cloud service required. |

---

## 8 · User experience

Full visual and interaction spec: [`DESIGN.md`](../DESIGN.md). The UX rules the requirements depend on:

1. **Chat is the front door and the evidence panel is the proof.** Every data-bearing answer has an evidence chip that opens the rows and the query plan.
2. **Unverified data is visibly different.** Processing, needs-review and AI-repaired states each have their own status styling and are never shown as reconciled.
3. **Answers declare their coverage** (accounts, period, row count, exclusions).
4. **Normalization is visible.** The raw bank label (`"DR"`, `"Withdrawal"`) appears alongside the canonical type.

Key flows:
1. *Sign in → workspace → upload statements → watch status → ask the first question → open evidence.*
2. *Open borrower → scan the dashboard metrics → click a metric → see its rows → ask a follow-up in chat.*
3. *(Internal) Review queue → open a failing document → compare the row against the page crop → accept, edit or reject → the document re-reconciles.*

---

## 9 · Success metrics

**Pilot north star:** the share of analyst questions answered with a verifiable number, with no manual spreadsheet work.

| Metric | Pilot target |
|---|---|
| Documents auto-reconciled without human review | ≥ 90% |
| Median time from upload to "Reconciled" (≤ 100 pages) | < 2 min |
| Distinct layouts needed to cover 80% of volume | ≤ 40 (hypothesis from architecture doc) |
| Spec-induction LLM calls per 1,000 documents (after month 1) | Trending to < 20 |
| Answer accuracy on the eval set | ≥ 99% SQL path, ≥ 85% precision@10 semantic path |
| Answers with thumbs-down | < 5% |
| Analyst time per application on statement analysis | −50% vs. baseline |
| Weekly active analysts / seats | ≥ 70% |

**Eval set:** build it first. Collect 50+ real, consented, anonymized statements across the top Nigerian banks by borrower volume, with hand-labelled totals and 100 benchmark questions. It is used both to benchmark against a LandingAI/Textract baseline (per the research recommendation) and as a CI regression gate.

---

## 10 · Milestones

| Milestone | Scope | Exit criteria |
|---|---|---|
| **M0 — Prove the pipeline** | Run the end-to-end flow on live infra with a real LLM. Build the eval set. | 20 real statements from ≥ 5 banks reconcile. Cost per doc measured. |
| **M1 — Real answers** | Wire the frontend to the API (CHAT-8), apply plan filters in SQL (CHAT-3), coverage statements (CHAT-10), upload + document status UI | Analysts get correct answers on their own uploads |
| **M2 — Pilot-ready** | Real auth + SSO (SEC-2), roles, review queue UI, scanned OCR, dedup, NDPA review | One lender pilot with ≥ 5 analysts on real applications |
| **M3 — Credit signals** | Analytics views (ANA-1–5), borrower dashboard, semantic search with embeddings, CSV export | Credit officers use the dashboard in approval meetings |
| **M4 — GA** | Layout-drift detection, multi-currency, audit log, retention controls, responsive/mobile, Mono account linking | Second paying tenant onboarded self-serve |

---

## 11 · Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Layouts are more fragmented than the 20–40 hypothesis, so induction runs often | Med | Cost and latency up | Measure in M0. Induction is rate-limited and amortized either way. Fall back to a document-AI vendor for long-tail layouts. |
| Statements with no running-balance column can't be row-reconciled | Med | Weaker proof | Fall back to a document-level opening/closing check plus summary totals. Mark these documents "partially verified". |
| Scanned or low-quality PDFs break OCR | High | Review queue floods | PaddleOCR plus a quality score. Low-quality scans are routed to review early with a clear reason. |
| Layout drift silently breaks a cached spec | Med | Rows fail reconciliation | Reconciliation catches it (it fails safe). EXT-9 adds failure-rate alerts and spec versioning. |
| Planner misreads a question (wrong month or year) | Med | A wrong but "proven" answer | The query plan is always visible. Add clarification (CHAT-9). Eval-set regression tests. |
| Auth stub reaches production | Low | Critical data breach | A P0 blocker for any real data. CI check that fails if the header auth is enabled outside the local profile. |
| Building in-house costs more than buying | Med | Slower time to market | The research report recommends benchmarking against LandingAI/Textract in M0 and letting the numbers decide. |
| Regulatory / NDPA obligations for financial PII | Med | Blocks the pilot | Self-hosted and in-region deployment. Legal review in M2. Retention controls. |

---

## 12 · Future (post-GA)

- Statement tamper and fraud detection (font or metadata anomalies, balances that reconcile but are fabricated)
- Live account refresh via open banking, and cross-checking PDF data against linked-account data
- Rules and alerts ("flag any application with >2 bounced items in 90 days")
- API access for lenders' own loan-origination systems
- Additional markets (Ghana, Kenya, South Africa) and their bank layouts

---

## 13 · Open questions

1. **Currency and locale.** The UI sample data uses `$` and MM/DD, but the target market is Nigeria (₦, DD/MM). Is the pilot tenant NGN-only?
2. **Who uploads?** Only the analyst, or does the borrower upload via a link the lender sends? That decides whether we need a borrower-facing upload page.
3. **Borrower as an entity.** The data model has tenant → documents but no borrower/applicant object. Dashboards and "all accounts" questions need one. Do we add `Applicant` in M1?
4. **Build vs. buy for the long tail.** Do we keep a document-AI vendor as a fallback for layouts that fail induction, and which one?
5. **Semantic search scope.** Is it needed for the pilot, or can M1 ship SQL-only with semantic questions clearly marked unsupported?
6. **Retention defaults.** How long do we keep source PDFs vs. derived rows after a decision?
7. **Pricing model.** Per seat, per statement, or per page? This affects which cost metrics we instrument first.
