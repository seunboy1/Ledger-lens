"""
Document-level reconciliation over canonical rows.

`reconcile_rows` (services/reconciliation.py) is the pure arithmetic check.
This module applies it to one document's stored transactions, anchored on
the opening balance printed on the statement, and writes the outcome back:
which rows are verified, what the running balance *should* have been on the
rows that are not, the document's score and its status.

It is called by the extraction pipeline after promotion and again by the
review API whenever a human corrects a row, so a fix is always re-proven by
the same arithmetic rather than trusted because someone typed it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document, DocumentStatus, Transaction, TransactionType
from app.services.reconciliation import document_level_check, reconcile_rows

TOLERANCE = Decimal("0.01")


@dataclass
class DocumentProof:
    opening: Decimal | None
    closing_printed: Decimal | None
    total_credits: Decimal
    total_debits: Decimal
    closing_computed: Decimal | None
    rows_total: int
    rows_verified: int
    failing_ids: list[str]
    document_check_ok: bool | None
    pending_ai_repairs: int

    @property
    def fully_verified(self) -> bool:
        return (
            self.rows_total > 0
            and self.rows_verified == self.rows_total
            and self.document_check_ok is not False
            and self.pending_ai_repairs == 0
        )


def _signed(txn: Transaction) -> Decimal:
    amount = Decimal(str(txn.amount))
    return amount if txn.transaction_type == TransactionType.credit else -amount


async def load_document_rows(db: AsyncSession, document_id) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(Transaction.document_id == document_id)
        .order_by(Transaction.page_number, Transaction.row_index, Transaction.transaction_date)
    )
    return list(result.scalars().all())


def compute_proof(document: Document, rows: list[Transaction], *, apply: bool = True) -> DocumentProof:
    opening = Decimal(str(document.opening_balance)) if document.opening_balance is not None else None
    closing = Decimal(str(document.closing_balance)) if document.closing_balance is not None else None

    recon_input: list[dict] = []
    if opening is not None:
        # Synthetic anchor: lets the first real transaction be checked too.
        recon_input.append({"amount": Decimal(0), "transaction_type": TransactionType.credit, "balance_after": opening})
    for txn in rows:
        recon_input.append(
            {
                "amount": Decimal(str(txn.amount)),
                "transaction_type": txn.transaction_type,
                "balance_after": Decimal(str(txn.balance_after)) if txn.balance_after is not None else None,
            }
        )

    result = reconcile_rows(recon_input, tolerance=TOLERANCE)
    offset = 1 if opening is not None else 0
    failing = {i - offset for i in result.failing_indices}

    credits = sum((Decimal(str(t.amount)) for t in rows if t.transaction_type == TransactionType.credit), Decimal(0))
    debits = sum((Decimal(str(t.amount)) for t in rows if t.transaction_type == TransactionType.debit), Decimal(0))

    doc_ok: bool | None = None
    closing_computed: Decimal | None = None
    if opening is not None:
        closing_computed = opening + credits - debits
        if closing is not None:
            doc_ok = document_level_check(opening, closing, credits, debits, tolerance=TOLERANCE)

    if apply:
        previous: Decimal | None = opening
        for i, txn in enumerate(rows):
            ok = i not in failing
            txn.reconciled = ok
            if not ok and previous is not None:
                txn.expected_balance = previous + _signed(txn)
            elif ok:
                txn.expected_balance = None
            if txn.balance_after is not None:
                previous = Decimal(str(txn.balance_after))

    # When there is no opening balance the first row anchors the chain and is
    # not itself checked; count it as verified only via the document check.
    rows_total = len(rows)
    rows_verified = rows_total - len(failing)
    pending_ai = sum(1 for t in rows if t.repair_source == "ai" and not t.reviewed)

    return DocumentProof(
        opening=opening,
        closing_printed=closing,
        total_credits=credits,
        total_debits=debits,
        closing_computed=closing_computed,
        rows_total=rows_total,
        rows_verified=rows_verified,
        failing_ids=[str(rows[i].id) for i in sorted(failing) if 0 <= i < rows_total],
        document_check_ok=doc_ok,
        pending_ai_repairs=pending_ai,
    )


async def reconcile_document(db: AsyncSession, document: Document) -> DocumentProof:
    rows = await load_document_rows(db, document.id)
    proof = compute_proof(document, rows, apply=True)

    document.reconciliation_score = (proof.rows_verified / proof.rows_total) if proof.rows_total else 0
    if document.status != DocumentStatus.failed:
        document.status = DocumentStatus.reconciled if proof.fully_verified else DocumentStatus.needs_review
    return proof
