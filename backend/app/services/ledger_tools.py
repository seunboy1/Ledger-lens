"""
Read-only operations over one workspace, shared by the LangGraph agent's tools
(app/agent) and the MCP server (app/mcp_server.py).

Every function takes a session that is already scoped to the tenant, and every
figure it returns is computed by the database over verified rows. Nothing
here asks a model anything.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentStatus, Transaction
from app.services.analytics import overview
from app.services.answering import Answer, answer_question, money
from app.services.statement_proof import compute_proof, load_document_rows


def answer_to_dict(answer: Answer, rows: list[Transaction]) -> dict:
    by_id = {t.id: t for t in rows}
    return {
        "answer": answer.content,
        "route": answer.route.value,
        "filters": answer.plan.describe_filters(),
        "intent": answer.plan.intent.value,
        "matched_rows": answer.matched_rows,
        "figures": [{"label": k.label, "value": k.value} for k in answer.kpis],
        "rows": [
            {
                "id": str(t.id),
                "date": t.transaction_date.strftime("%d %b %Y"),
                "description": t.description,
                "type": t.transaction_type.value,
                "amount": money(t.amount),
                "bank": t.bank_name,
                "printed_label": t.raw_type_label,
            }
            for i in answer.evidence_ids
            if (t := by_id.get(i)) is not None
        ],
    }


async def ask(db: AsyncSession, tenant_id: uuid.UUID, question: str) -> tuple[Answer, dict]:
    """Plan the question, run it as SQL over verified rows, return the answer and its rows."""

    answer = await answer_question(db, tenant_id, question)
    rows = []
    if answer.evidence_ids:
        rows = list(
            (
                await db.execute(
                    select(Transaction).where(Transaction.tenant_id == tenant_id, Transaction.id.in_(answer.evidence_ids))
                )
            ).scalars()
        )
    return answer, answer_to_dict(answer, rows)


async def list_statements(db: AsyncSession, tenant_id: uuid.UUID) -> list[dict]:
    stats = (
        select(Transaction.document_id, func.count(Transaction.id).label("n"))
        .where(Transaction.tenant_id == tenant_id)
        .group_by(Transaction.document_id)
        .subquery()
    )
    result = await db.execute(
        select(Document, stats.c.n)
        .outerjoin(stats, stats.c.document_id == Document.id)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at)
    )
    return [
        {
            "id": str(d.id),
            "bank": d.bank_name,
            "filename": d.original_filename,
            "status": d.status.value,
            "rows": int(n or 0),
            "reconciliation_score": float(d.reconciliation_score) if d.reconciliation_score is not None else None,
            "counts_in_answers": d.status == DocumentStatus.reconciled,
        }
        for d, n in result.all()
    ]


async def statement_proof(db: AsyncSession, tenant_id: uuid.UUID, query: str) -> list[dict]:
    """Balance proof for statements matching a document id, bank name or filename."""

    stmt = select(Document).where(Document.tenant_id == tenant_id)
    try:
        stmt = stmt.where(Document.id == uuid.UUID(query))
    except ValueError:
        like = f"%{query.strip()}%"
        stmt = stmt.where(or_(Document.bank_name.ilike(like), Document.original_filename.ilike(like)))
    docs = list((await db.execute(stmt.order_by(Document.created_at))).scalars())

    out = []
    for doc in docs:
        rows = await load_document_rows(db, doc.id)
        p = compute_proof(doc, rows, apply=False)
        failing = [t for t in rows if str(t.id) in set(p.failing_ids)]
        out.append(
            {
                "id": str(doc.id),
                "bank": doc.bank_name,
                "filename": doc.original_filename,
                "status": doc.status.value,
                "opening_balance": money(p.opening) if p.opening is not None else None,
                "total_credits": money(p.total_credits),
                "total_debits": money(p.total_debits),
                "computed_closing": money(p.closing_computed) if p.closing_computed is not None else None,
                "printed_closing": money(p.closing_printed) if p.closing_printed is not None else None,
                "closing_matches": p.document_check_ok,
                "rows_verified": p.rows_verified,
                "rows_total": p.rows_total,
                "rows_failing": [
                    {
                        "date": t.transaction_date.strftime("%d %b %Y"),
                        "description": t.description,
                        "extracted_amount": money(t.amount),
                        "printed_balance": money(t.balance_after) if t.balance_after is not None else None,
                        "expected_balance": money(t.expected_balance) if t.expected_balance is not None else None,
                    }
                    for t in failing
                ],
            }
        )
    return out


async def workspace_overview(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    data = await overview(db, tenant_id)
    k = data["kpis"]
    fmt = lambda v: money(v) if v is not None else None  # noqa: E731
    salary = data["salary"]
    return {
        "months": [
            {"month": m["month"], "money_in": money(m["inflow"]), "money_out": money(m["outflow"]), "month_end_balance": money(m["closing_balance"])}
            for m in data["months"]
        ],
        "average_monthly_in": fmt(k["avg_monthly_inflow"]),
        "average_monthly_out": fmt(k["avg_monthly_outflow"]),
        "latest_month_end_balance": fmt(k["closing_balance"]),
        "lowest_running_balance": fmt(k["min_balance"]),
        "salary": None
        if not salary
        else {
            "narration": salary["narration"],
            "bank": salary["bank"],
            "average_amount": money(salary["average_amount"]),
            "usual_day_of_month": salary["typical_day"],
            "months_seen": salary["months"],
        },
        "risk_signals": {
            name: {"count": s["count"], "total": money(s["total"])} for name, s in data["signals"].items()
        },
        "statements": data["documents"],
    }


def as_text(value, indent: int = 0) -> str:
    """Compact, model-friendly rendering of the dicts above (keeps figures verbatim)."""

    pad = "  " * indent
    if isinstance(value, dict):
        return "\n".join(
            f"{pad}{k}:\n{as_text(v, indent + 1)}" if isinstance(v, (dict, list)) and v else f"{pad}{k}: {v}"
            for k, v in value.items()
        )
    if isinstance(value, list):
        return "\n".join(f"{pad}-\n{as_text(v, indent + 1)}" if isinstance(v, (dict, list)) else f"{pad}- {v}" for v in value) or f"{pad}(none)"
    return f"{pad}{value}"

