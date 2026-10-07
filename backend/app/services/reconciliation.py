"""
Balance reconciliation — the mechanism that makes extraction provably
correct instead of merely plausible.

Every bank statement carries a running balance. For any two consecutive
transactions, balance[n] must equal balance[n-1] plus a credit or minus a
debit. If every row in a document satisfies this, the extraction is
verified by arithmetic, not by trusting the model that helped parse it.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.db.models import TransactionType


@dataclass
class ReconciledRow:
    index: int
    ok: bool
    expected_balance: Decimal | None
    actual_balance: Decimal | None


@dataclass
class ReconciliationResult:
    total_rows: int
    passed_rows: int
    failing_indices: list[int] = field(default_factory=list)

    @property
    def score(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return self.passed_rows / self.total_rows

    @property
    def fully_reconciled(self) -> bool:
        return self.total_rows > 0 and self.passed_rows == self.total_rows


def reconcile_rows(
    rows: list[dict],
    tolerance: Decimal = Decimal("0.01"),
) -> ReconciliationResult:
    """
    Each row must have: amount (Decimal), transaction_type (TransactionType),
    balance_after (Decimal | None). Rows are assumed to be in statement order.

    A row with no balance_after (some banks omit it on certain row types,
    e.g. a summary line) is skipped from the check rather than counted as a
    failure — but it also can't anchor the next row's expected balance, so
    the chain restarts from the following row that does carry a balance.
    """

    total = 0
    passed = 0
    failing: list[int] = []
    previous_balance: Decimal | None = None

    for i, row in enumerate(rows):
        balance_after = row.get("balance_after")
        amount = row["amount"]
        txn_type = row["transaction_type"]

        if previous_balance is None or balance_after is None:
            previous_balance = balance_after
            continue

        total += 1
        signed_amount = amount if txn_type == TransactionType.credit else -amount
        expected = previous_balance + signed_amount

        if abs(expected - balance_after) <= tolerance:
            passed += 1
        else:
            failing.append(i)

        previous_balance = balance_after

    return ReconciliationResult(total_rows=total, passed_rows=passed, failing_indices=failing)


def document_level_check(
    opening_balance: Decimal,
    closing_balance: Decimal,
    total_credits: Decimal,
    total_debits: Decimal,
    tolerance: Decimal = Decimal("0.01"),
) -> bool:
    """
    Fallback check for statements that omit a per-row running balance:
    opening + credits - debits should equal closing, for the document
    as a whole. Weaker than row-level reconciliation (it can't localize
    a single bad row) but still catches systemic extraction errors.
    """

    expected_closing = opening_balance + total_credits - total_debits
    return abs(expected_closing - closing_balance) <= tolerance
