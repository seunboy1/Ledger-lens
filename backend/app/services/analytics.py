"""
Credit-risk signals over verified rows (docs/architecture.md §4).

Every figure is a database aggregate over transactions that passed
reconciliation. Pattern-based signals (salary, betting, other-lender
repayments, returned items) match narration text, and each one returns
the ids of the rows it counted so the UI can show its evidence.
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from decimal import Decimal
from statistics import pstdev

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Document, DocumentStatus, Transaction, TransactionType


def _month_expr():
    if get_settings().is_postgres:
        return func.to_char(Transaction.transaction_date, "YYYY-MM")
    return func.strftime("%Y-%m", Transaction.transaction_date)


def _verified(tenant_id: uuid.UUID):
    return (
        Transaction.tenant_id == tenant_id,
        Transaction.reconciled.is_(True),
        Document.status == DocumentStatus.reconciled,
    )


SIGNALS = {
    "betting": [r"\bbet\b", r"casino", r"luckyplay", r"sportsbook"],
    "other_lender_repayments": [r"loan repayment", r"quickcred", r"credit facility"],
    "returned_items": [r"\brtn\b", r"insufficient funds", r"\breversal\b", r"\bnsf\b", r"returned"],
}

SALARY_PATTERN = re.compile(r"(?i)salary|payroll|wages")


async def overview(db: AsyncSession, tenant_id: uuid.UUID) -> dict:
    month = _month_expr().label("month")

    monthly_stmt = (
        select(month, Transaction.transaction_type, func.sum(Transaction.amount), func.count(Transaction.id))
        .join(Document, Document.id == Transaction.document_id)
        .where(*_verified(tenant_id))
        .group_by(month, Transaction.transaction_type)
        .order_by(month)
    )
    months: dict[str, dict] = {}
    for m, ttype, total, n in (await db.execute(monthly_stmt)).all():
        row = months.setdefault(m, {"month": m, "inflow": Decimal(0), "outflow": Decimal(0), "count": 0})
        row["inflow" if ttype == TransactionType.credit else "outflow"] += Decimal(str(total))
        row["count"] += int(n)

    # Month-end balance per account, summed across accounts. Accounts with no
    # activity in a month carry their last known balance forward.
    rows = (
        await db.execute(
            select(Transaction.document_id, Transaction.bank_name, month, Transaction.balance_after)
            .join(Document, Document.id == Transaction.document_id)
            .where(*_verified(tenant_id), Transaction.balance_after.is_not(None))
            .order_by(Transaction.transaction_date, Transaction.page_number, Transaction.row_index)
        )
    ).all()
    month_keys = sorted(months)
    last_by_doc_month: dict[uuid.UUID, dict[str, Decimal]] = defaultdict(dict)
    all_balances: list[Decimal] = []
    for doc_id, _bank, m, bal in rows:
        last_by_doc_month[doc_id][m] = Decimal(str(bal))
        all_balances.append(Decimal(str(bal)))
    for m in month_keys:
        total = Decimal(0)
        for per_month in last_by_doc_month.values():
            known = [k for k in per_month if k <= m]
            if known:
                total += per_month[max(known)]
        months[m]["closing_balance"] = total
        months[m]["net"] = months[m]["inflow"] - months[m]["outflow"]

    series = [months[m] for m in month_keys]
    n_months = len(series) or 1
    avg_in = sum((r["inflow"] for r in series), Decimal(0)) / n_months
    avg_out = sum((r["outflow"] for r in series), Decimal(0)) / n_months
    nets = [float(r["net"]) for r in series]

    # --- salary detection: recurring credits, similar amount, similar day ---
    credits = (
        await db.execute(
            select(Transaction)
            .join(Document, Document.id == Transaction.document_id)
            .where(*_verified(tenant_id), Transaction.transaction_type == TransactionType.credit)
            .order_by(Transaction.transaction_date)
        )
    ).scalars().all()
    salary = _detect_salary([c for c in credits if SALARY_PATTERN.search(c.description)]) or _detect_salary(list(credits))

    # --- narration-pattern risk signals --------------------------------------
    debits = (
        await db.execute(
            select(Transaction)
            .join(Document, Document.id == Transaction.document_id)
            .where(*_verified(tenant_id), Transaction.transaction_type == TransactionType.debit)
        )
    ).scalars().all()
    signals = {}
    for key, patterns in SIGNALS.items():
        hits = [d for d in debits if any(re.search(p, d.description, re.I) for p in patterns)]
        signals[key] = {
            "count": len(hits),
            "total": sum((Decimal(str(h.amount)) for h in hits), Decimal(0)),
            "transaction_ids": [str(h.id) for h in hits],
        }

    # --- counterparty concentration (debits) ---------------------------------
    debit_rows = (
        await db.execute(
            select(Transaction.description, func.sum(Transaction.amount), func.count(Transaction.id))
            .join(Document, Document.id == Transaction.document_id)
            .where(*_verified(tenant_id), Transaction.transaction_type == TransactionType.debit)
            .group_by(Transaction.description)
        )
    ).all()
    total_debits = sum((Decimal(str(t)) for _, t, _ in debit_rows), Decimal(0)) or Decimal(1)
    counterparties = sorted(
        (
            {"name": d, "total": Decimal(str(t)), "count": int(n), "share": float(Decimal(str(t)) / total_debits)}
            for d, t, n in debit_rows
        ),
        key=lambda r: -r["total"],
    )[:6]

    docs = (
        await db.execute(select(Document.status, func.count()).where(Document.tenant_id == tenant_id).group_by(Document.status))
    ).all()

    return {
        "months": series,
        "kpis": {
            "avg_monthly_inflow": avg_in,
            "avg_monthly_outflow": avg_out,
            "net_volatility": Decimal(str(round(pstdev(nets), 2))) if len(nets) > 1 else Decimal(0),
            "min_balance": min(all_balances) if all_balances else None,
            "avg_balance": (sum(all_balances, Decimal(0)) / len(all_balances)) if all_balances else None,
            "closing_balance": series[-1]["closing_balance"] if series else None,
        },
        "salary": salary,
        "signals": signals,
        "counterparties": counterparties,
        "documents": {s.value: n for s, n in docs},
    }


def _detect_salary(credits: list[Transaction]) -> dict | None:
    """Same narration, 3+ months, amount within 10%, day of month within 4 days."""

    groups: dict[str, list[Transaction]] = defaultdict(list)
    for c in credits:
        groups[re.sub(r"[\d*]+", "", c.description.lower()).strip()].append(c)

    best = None
    for txns in groups.values():
        months = {(t.transaction_date.year, t.transaction_date.month) for t in txns}
        if len(months) < 3:
            continue
        amounts = [Decimal(str(t.amount)) for t in txns]
        days = [t.transaction_date.day for t in txns]
        if max(amounts) > min(amounts) * Decimal("1.10") or max(days) - min(days) > 4:
            continue
        candidate = {
            "detected": True,
            "narration": txns[0].description,
            "bank": txns[0].bank_name,
            "average_amount": sum(amounts, Decimal(0)) / len(amounts),
            "typical_day": round(sum(days) / len(days)),
            "months": len(months),
            "transaction_ids": [str(t.id) for t in txns],
        }
        if best is None or candidate["average_amount"] > best["average_amount"]:
            best = candidate
    return best
