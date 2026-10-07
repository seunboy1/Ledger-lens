"""
Question -> answer, with the arithmetic done by the database.

The flow for every question:

1. ``route_question`` picks SQL aggregation or semantic search.
2. ``build_plan`` turns the question into an inspectable QueryPlan
   (intent, type, date range, bank, amount bounds, narration keywords).
3. The plan is executed as SQL against verified rows only: transactions
   that passed reconciliation, from documents whose status is `reconciled`.
4. The answer text is templated from the SQL result. No model reads the
   rows or adds up a column; the numbers in the sentence are the numbers the
   query returned, and the evidence ids are the rows it returned them from.

The semantic path ranks candidate rows by concept matches and recurrence
(recurring debits of a stable amount read as subscriptions). When
embeddings are enabled on the full stack, pgvector similarity slots into
`_semantic_candidates` without changing the response contract.
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentStatus, Transaction, TransactionType
from app.services.planner import Intent, QueryPlan, build_plan
from app.services.router import RetrievalRoute, route_question

CURRENCY = "₦"
EVIDENCE_LIMIT = 60


def money(value: Decimal | float | int, signed: bool = False) -> str:
    v = Decimal(str(value)).quantize(Decimal("0.01"))
    text = f"{CURRENCY}{abs(v):,.2f}"
    if signed:
        return ("+" if v >= 0 else "−") + text
    return ("−" + text) if v < 0 else text


@dataclass
class Kpi:
    label: str
    value: str
    tone: str = "neutral"  # credit | debit | neutral


@dataclass
class Answer:
    route: RetrievalRoute
    plan: QueryPlan
    content: str
    kpis: list[Kpi] = field(default_factory=list)
    evidence_ids: list[uuid.UUID] = field(default_factory=list)
    focused_ids: list[uuid.UUID] = field(default_factory=list)
    lineage: list[dict] = field(default_factory=list)
    summary_title: str = ""
    summary_subtitle: str = ""
    source_summary: str | None = None
    matched_rows: int = 0
    engine: str = "deterministic"  # or "agent" when the LangGraph agent phrased the reply


def _dt(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def _verified(tenant_id: uuid.UUID):
    return and_(
        Transaction.tenant_id == tenant_id,
        Transaction.reconciled.is_(True),
        Document.status == DocumentStatus.reconciled,
    )


def _apply_plan(stmt: Select, plan: QueryPlan, *, with_keywords: bool = True) -> Select:
    if plan.transaction_type:
        stmt = stmt.where(Transaction.transaction_type == TransactionType(plan.transaction_type))
    if plan.date_range:
        stmt = stmt.where(
            Transaction.transaction_date >= _dt(plan.date_range.start),
            Transaction.transaction_date < _dt(plan.date_range.end),
        )
    if plan.bank:
        stmt = stmt.where(Transaction.bank_name == plan.bank)
    if plan.min_amount is not None:
        stmt = stmt.where(Transaction.amount >= plan.min_amount)
    if plan.max_amount is not None:
        stmt = stmt.where(Transaction.amount <= plan.max_amount)
    if with_keywords and plan.keywords:
        stmt = stmt.where(or_(*[Transaction.description.ilike(f"%{k}%") for k in plan.keywords]))
    return stmt


def _base(tenant_id: uuid.UUID, *columns) -> Select:
    return select(*columns).join(Document, Document.id == Transaction.document_id).where(_verified(tenant_id))


def _scope_text(plan: QueryPlan, banks_in_scope: int) -> str:
    parts = []
    if plan.date_range:
        parts.append(_period_label(plan))
    parts.append(plan.bank if plan.bank else f"{banks_in_scope} bank{'s' if banks_in_scope != 1 else ''}")
    if plan.keywords:
        parts.append("narration matching " + " / ".join(f'"{k}"' for k in plan.keywords))
    return ", ".join(parts)


def _period_label(plan: QueryPlan) -> str:
    dr = plan.date_range
    if dr is None:
        return "all dates"
    if re.fullmatch(r"\d{4}-\d{2}", dr.label):
        return f"{dr.start:%B %Y}"
    return dr.label


def _type_word(plan: QueryPlan, plural: bool = True) -> str:
    if plan.transaction_type == "credit":
        return "credits" if plural else "credit"
    if plan.transaction_type == "debit":
        return "debits" if plural else "debit"
    return "transactions" if plural else "transaction"


async def known_banks(db: AsyncSession, tenant_id: uuid.UUID) -> list[str]:
    result = await db.execute(_base(tenant_id, Transaction.bank_name).distinct())
    return sorted(b for (b,) in result.all() if b)


async def coverage_gaps(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, int]:
    result = await db.execute(
        select(Document.status, func.count()).where(Document.tenant_id == tenant_id).group_by(Document.status)
    )
    return {status.value: n for status, n in result.all()}


async def answer_question(db: AsyncSession, tenant_id: uuid.UUID, question: str, today: date | None = None) -> Answer:
    banks = await known_banks(db, tenant_id)
    route = route_question(question)
    plan = build_plan(question, known_banks=banks, today=today)

    if route == RetrievalRoute.semantic:
        answer = await _semantic(db, tenant_id, plan)
    else:
        answer = await _sql(db, tenant_id, plan, banks)

    gaps = await coverage_gaps(db, tenant_id)
    excluded = gaps.get("processing", 0) + gaps.get("uploaded", 0) + gaps.get("needs_review", 0)
    if excluded:
        answer.content += (
            f" This excludes {excluded} statement{'s' if excluded != 1 else ''} that "
            f"{'are' if excluded != 1 else 'is'} still processing or awaiting review."
        )

    answer.lineage = [
        {"title": "Question parsed", "detail": f"Intent: {plan.intent.value}. Filters: {plan.describe_filters()}"},
        {
            "title": "Routed to SQL aggregation" if route == RetrievalRoute.sql else "Routed to semantic search",
            "detail": (
                "Structured filter and aggregate, computed by the database"
                if route == RetrievalRoute.sql
                else "Concept and recurrence ranking over verified rows (no full-corpus read)"
            ),
        },
        {"title": "Verified rows only", "detail": "reconciled = true, statement status = reconciled"},
        {"title": "Tenant scope applied", "detail": f"tenant_id = {str(tenant_id)[:8]}..."},
        {"title": f"{answer.matched_rows} row{'s' if answer.matched_rows != 1 else ''} matched", "detail": f"{len(answer.evidence_ids)} shown as evidence"},
    ]
    answer.route = route
    return answer


async def _rows(db: AsyncSession, stmt: Select) -> list[Transaction]:
    return list((await db.execute(stmt)).scalars().all())


async def _sql(db: AsyncSession, tenant_id: uuid.UUID, plan: QueryPlan, banks: list[str]) -> Answer:
    filtered = _apply_plan(_base(tenant_id, Transaction), plan)
    answer = Answer(route=RetrievalRoute.sql, plan=plan, content="")

    if plan.intent == Intent.balance:
        # Balances come from the printed running balance, not from narration
        # matches, so keyword and type filters do not apply.
        plan.keywords = []
        plan.transaction_type = None
        n_banks = len(banks) if not plan.bank else 1
        await _balance(db, tenant_id, plan, answer, _scope_text(plan, n_banks))
        answer.summary_title = f"{answer.matched_rows:,} balance readings"
        answer.summary_subtitle = _period_label(plan) if plan.date_range else "All verified statements"
        answer.source_summary = f"Closing and lowest balances per account ({_scope_text(plan, n_banks)})"
        return answer

    agg = _apply_plan(
        _base(
            tenant_id,
            Transaction.transaction_type,
            func.count(Transaction.id),
            func.coalesce(func.sum(Transaction.amount), 0),
            func.avg(Transaction.amount),
        ),
        plan,
    ).group_by(Transaction.transaction_type)
    by_type: dict[str, tuple[int, Decimal, Decimal | None]] = {}
    for ttype, n, total, avg in (await db.execute(agg)).all():
        by_type[ttype.value] = (int(n), Decimal(str(total)), Decimal(str(avg)) if avg is not None else None)

    banks_in_scope = len(
        (await db.execute(_apply_plan(_base(tenant_id, Transaction.bank_name), plan).distinct())).all()
    )
    matched = sum(v[0] for v in by_type.values())
    answer.matched_rows = matched
    scope = _scope_text(plan, banks_in_scope)

    if matched == 0:
        answer.content = (
            f"No verified {_type_word(plan)} matched ({scope}). "
            "Try a different period, or check the Statements page for documents still in review."
        )
        answer.summary_title = "No matching rows"
        answer.summary_subtitle = scope
        return answer

    credits = by_type.get("credit", (0, Decimal(0), None))
    debits = by_type.get("debit", (0, Decimal(0), None))
    order = Transaction.transaction_date.asc()

    if plan.intent in (Intent.largest, Intent.smallest):
        direction = Transaction.amount.desc() if plan.intent == Intent.largest else Transaction.amount.asc()
        top = await _rows(db, filtered.order_by(direction, Transaction.transaction_date).limit(plan.limit))
        word = "largest" if plan.intent == Intent.largest else "smallest"
        lead = top[0]
        if len(top) == 1:
            answer.content = (
                f"The {word} {_type_word(plan, False)} ({scope}) is {money(lead.amount)} on "
                f"{lead.transaction_date:%d %b %Y}: {lead.description} at {lead.bank_name}."
            )
        else:
            answer.content = (
                f"The {len(top)} {word} {_type_word(plan)} ({scope}) range from {money(lead.amount)} to "
                f"{money(top[-1].amount)}. The {word} is {lead.description} at {lead.bank_name} "
                f"on {lead.transaction_date:%d %b %Y}."
            )
        answer.kpis = [Kpi(f"#{i + 1} {t.transaction_date:%d %b}", money(t.amount), t.transaction_type.value) for i, t in enumerate(top[:4])]
        answer.evidence_ids = [t.id for t in top]
        answer.focused_ids = [lead.id]
    elif plan.intent == Intent.count:
        answer.content = f"There {'is' if matched == 1 else 'are'} {matched:,} verified {_type_word(plan, matched != 1)} ({scope})."
        if not plan.transaction_type:
            answer.content += f" {credits[0]:,} credits and {debits[0]:,} debits."
        answer.kpis = [Kpi("Transactions", f"{matched:,}")]
        if not plan.transaction_type:
            answer.kpis += [Kpi("Credits", f"{credits[0]:,}", "credit"), Kpi("Debits", f"{debits[0]:,}", "debit")]
        rows = await _rows(db, filtered.order_by(order).limit(EVIDENCE_LIMIT))
        answer.evidence_ids = [t.id for t in rows]
    elif plan.intent == Intent.average:
        if plan.transaction_type:
            n, total, avg = by_type[plan.transaction_type]
            answer.content = f"The average {_type_word(plan, False)} ({scope}) is {money(avg)}, across {n:,} transactions totalling {money(total)}."
            answer.kpis = [Kpi("Average", money(avg), plan.transaction_type), Kpi("Count", f"{n:,}"), Kpi("Total", money(total))]
        else:
            answer.content = (
                f"Across {scope}, the average credit is {money(credits[2] or 0)} and the average debit is {money(debits[2] or 0)}."
            )
            answer.kpis = [Kpi("Avg credit", money(credits[2] or 0), "credit"), Kpi("Avg debit", money(debits[2] or 0), "debit")]
        rows = await _rows(db, filtered.order_by(order).limit(EVIDENCE_LIMIT))
        answer.evidence_ids = [t.id for t in rows]
    elif plan.intent == Intent.total or (plan.intent == Intent.list and (plan.transaction_type or plan.date_range)):
        if plan.transaction_type:
            n, total, _ = by_type[plan.transaction_type]
            answer.content = f"Total {_type_word(plan)} ({scope}) came to {money(total)} over {n:,} transaction{'s' if n != 1 else ''}."
            answer.kpis = [Kpi(_type_word(plan).title(), money(total), plan.transaction_type), Kpi("Transactions", f"{n:,}")]
        else:
            net = credits[1] - debits[1]
            answer.content = (
                f"Across {scope}, credits came to {money(credits[1])} over {credits[0]:,} transactions and "
                f"debits to {money(debits[1])} over {debits[0]:,}, a net {'inflow' if net >= 0 else 'outflow'} of {money(abs(net))}."
            )
            answer.kpis = [
                Kpi("Credits", money(credits[1]), "credit"),
                Kpi("Debits", money(debits[1]), "debit"),
                Kpi("Net", money(net, signed=True)),
            ]
        rows = await _rows(db, filtered.order_by(order).limit(EVIDENCE_LIMIT))
        biggest = await _rows(db, filtered.order_by(Transaction.amount.desc()).limit(1))
        answer.evidence_ids = [t.id for t in rows]
        answer.focused_ids = [biggest[0].id] if biggest else []
    else:
        rows = await _rows(db, filtered.order_by(Transaction.transaction_date.desc()).limit(plan.limit))
        answer.content = (
            f"Here are the {len(rows)} most recent verified {_type_word(plan)} ({scope}), "
            f"out of {matched:,} that match."
        )
        answer.kpis = [Kpi("Matching rows", f"{matched:,}")]
        answer.evidence_ids = [t.id for t in rows]

    answer.summary_title = f"{matched:,} rows, {banks_in_scope} bank{'s' if banks_in_scope != 1 else ''}"
    answer.summary_subtitle = _period_label(plan) if plan.date_range else "All verified statements"
    answer.source_summary = f"{matched:,} verified transactions ({scope})"
    return answer


async def _balance(db: AsyncSession, tenant_id: uuid.UUID, plan: QueryPlan, answer: Answer, scope: str) -> None:
    """Balance questions read the printed running balance, per bank, at the end of the period."""

    balance_plan = QueryPlan(question=plan.question, date_range=plan.date_range, bank=plan.bank)
    rows = await _rows(
        db,
        _apply_plan(_base(tenant_id, Transaction), balance_plan, with_keywords=False)
        .where(Transaction.balance_after.is_not(None))
        .order_by(Transaction.transaction_date, Transaction.page_number, Transaction.row_index),
    )
    if not rows:
        answer.content = f"No verified balances were found ({scope})."
        return

    by_account: dict[uuid.UUID, list[Transaction]] = defaultdict(list)
    for r in rows:
        by_account[r.document_id].append(r)

    closing_total = Decimal(0)
    lows: list[Transaction] = []
    lines = []
    for doc_rows in by_account.values():
        last = doc_rows[-1]
        low = min(doc_rows, key=lambda t: Decimal(str(t.balance_after)))
        closing_total += Decimal(str(last.balance_after))
        lows.append(low)
        lines.append(f"{last.bank_name} {money(last.balance_after)}")

    avg = sum(Decimal(str(r.balance_after)) for r in rows) / len(rows)
    lowest = min(lows, key=lambda t: Decimal(str(t.balance_after)))
    answer.content = (
        f"At the end of {_period_label(plan) if plan.date_range else 'the statement period'}, balances across "
        f"{len(by_account)} account{'s' if len(by_account) != 1 else ''} came to {money(closing_total)} "
        f"({'; '.join(lines)}). The lowest point was {money(lowest.balance_after)} at {lowest.bank_name} on "
        f"{lowest.transaction_date:%d %b %Y}."
    )
    answer.kpis = [
        Kpi("Closing, all accounts", money(closing_total)),
        Kpi("Lowest balance", money(lowest.balance_after), "debit"),
        Kpi("Average running balance", money(avg)),
    ]
    answer.matched_rows = len(rows)
    tail = [doc_rows[-1] for doc_rows in by_account.values()]
    answer.evidence_ids = [t.id for t in tail + lows]
    answer.focused_ids = [lowest.id]


# --- semantic path ------------------------------------------------------------

CONCEPTS: dict[str, list[str]] = {
    "subscription": ["subscription", "membership", "streamflix", "internet", "fibrelink", "gymhouse", "dstv", "premium"],
    "loan": ["loan", "repayment", "quickcred", "credit facility", "instalment"],
    "betting": ["bet", "luckyplay", "casino", "wallet funding"],
    "bounced": ["rtn", "returned", "insufficient", "reversal", "nsf", "dishonour"],
    "salary": ["salary", "payroll", "wages"],
    "fees": ["charges", "fee", "stamp duty", "maintenance", "withholding"],
    "transfer": ["trf", "transfer"],
    "utilities": ["powergrid", "token", "internet", "airtime"],
}

CONCEPT_NAMES = {
    "subscription": "subscriptions",
    "loan": "loan repayments",
    "betting": "betting",
    "bounced": "returned or bounced items",
    "salary": "salary",
    "fees": "fees and charges",
    "transfer": "transfers",
    "utilities": "utilities",
}

CONCEPT_TRIGGERS: dict[str, list[str]] = {
    "subscription": ["subscription", "recurring", "monthly", "membership"],
    "loan": ["loan", "lender", "repayment", "debt", "borrow"],
    "betting": ["bet", "betting", "gambl", "casino"],
    "bounced": ["bounce", "returned", "insufficient", "reversal", "nsf"],
    "salary": ["salary", "income", "employer", "payroll", "wage"],
    "fees": ["fee", "charge", "bank charges"],
    "transfer": ["transfer"],
    "utilities": ["utilit", "electric", "power", "airtime", "internet"],
}


def _concepts_for(question: str) -> list[str]:
    q = question.lower()
    return [c for c, triggers in CONCEPT_TRIGGERS.items() if any(t in q for t in triggers)]


def _normalize_narration(text: str) -> str:
    return re.sub(r"[\d*]+", "", text.lower()).strip()


async def _semantic(db: AsyncSession, tenant_id: uuid.UUID, plan: QueryPlan) -> Answer:
    answer = Answer(route=RetrievalRoute.semantic, plan=plan, content="")
    concepts = _concepts_for(plan.question)
    scope_plan = QueryPlan(question=plan.question, date_range=plan.date_range, bank=plan.bank, transaction_type=plan.transaction_type)
    candidates = await _rows(db, _apply_plan(_base(tenant_id, Transaction), scope_plan, with_keywords=False))

    # Recurrence: the same narration on 3+ distinct months at a stable amount.
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for t in candidates:
        groups[_normalize_narration(t.description)].append(t)
    recurring: set[str] = set()
    for key, txns in groups.items():
        months = {(t.transaction_date.year, t.transaction_date.month) for t in txns}
        amounts = [Decimal(str(t.amount)) for t in txns]
        if len(months) >= 3 and max(amounts) <= min(amounts) * Decimal("1.25"):
            recurring.add(key)

    terms = [term for c in concepts for term in CONCEPTS[c]] + plan.keywords
    scored: list[tuple[float, Transaction]] = []
    for t in candidates:
        text = t.description.lower()
        score = sum(2.0 for term in terms if term in text)
        key = _normalize_narration(t.description)
        if "subscription" in concepts and key in recurring and t.transaction_type == TransactionType.debit:
            score += 3.0
        if score > 0:
            scored.append((score, t))

    scored.sort(key=lambda st: (-st[0], st[1].transaction_date))
    top = [t for _, t in scored[:EVIDENCE_LIMIT]]
    answer.matched_rows = len(scored)

    if not top:
        answer.content = (
            "Nothing in the verified rows looks like that. Try naming a merchant, or ask a total such as "
            "\"total debits in August\"."
        )
        answer.summary_title = "No close matches"
        answer.summary_subtitle = "Semantic search"
        return answer

    patterns: dict[str, list[Transaction]] = defaultdict(list)
    for t in top:
        patterns[_normalize_narration(t.description)].append(t)
    ranked = sorted(patterns.items(), key=lambda kv: -sum(Decimal(str(t.amount)) for t in kv[1]))

    described = []
    for key, txns in ranked[:5]:
        total = sum(Decimal(str(t.amount)) for t in txns)
        months = len({(t.transaction_date.year, t.transaction_date.month) for t in txns})
        label = txns[0].description
        if key in recurring:
            described.append(f"{label} ({money(txns[0].amount)} monthly, {months} months)")
        else:
            described.append(f"{label} ({len(txns)}x, {money(total)} total)")

    topic = CONCEPT_NAMES.get(concepts[0], concepts[0]) if concepts else "your question"
    n = len(patterns)
    answer.content = (
        f"{n} pattern{'s' if n != 1 else ''} in the verified rows look{'' if n != 1 else 's'} like {topic}: "
        + "; ".join(described)
        + "."
    )
    total_all = sum(Decimal(str(t.amount)) for t in top)
    answer.kpis = [
        Kpi("Patterns", str(len(patterns))),
        Kpi("Matching rows", str(len(top))),
        Kpi("Total value", money(total_all), "debit" if all(t.transaction_type == TransactionType.debit for t in top) else "neutral"),
    ]
    answer.evidence_ids = [t.id for t in top]
    answer.focused_ids = [ranked[0][1][0].id]
    answer.summary_title = f"{len(top)} rows ranked"
    answer.summary_subtitle = "Concept and recurrence match"
    n_banks = len({t.bank_name for t in top})
    answer.source_summary = f"{len(top)} row{'s' if len(top) != 1 else ''} across {n_banks} bank{'s' if n_banks != 1 else ''}"
    return answer
