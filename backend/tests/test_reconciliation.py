from decimal import Decimal

from app.db.models import TransactionType
from app.services.reconciliation import document_level_check, reconcile_rows


def test_fully_reconciled_statement_scores_one():
    rows = [
        {"amount": Decimal("100.00"), "transaction_type": TransactionType.credit, "balance_after": Decimal("1100.00")},
        {"amount": Decimal("50.00"), "transaction_type": TransactionType.debit, "balance_after": Decimal("1050.00")},
        {"amount": Decimal("25.00"), "transaction_type": TransactionType.debit, "balance_after": Decimal("1025.00")},
    ]
    # opening balance implied by the first row's balance_after minus its own effect
    rows.insert(0, {"amount": Decimal("0"), "transaction_type": TransactionType.credit, "balance_after": Decimal("1000.00")})

    result = reconcile_rows(rows)

    assert result.fully_reconciled
    assert result.score == 1.0
    assert result.failing_indices == []


def test_single_bad_row_is_localized_not_whole_document():
    rows = [
        {"amount": Decimal("0"), "transaction_type": TransactionType.credit, "balance_after": Decimal("1000.00")},
        {"amount": Decimal("100.00"), "transaction_type": TransactionType.credit, "balance_after": Decimal("1100.00")},
        # corrupted row: balance jumps incorrectly
        {"amount": Decimal("50.00"), "transaction_type": TransactionType.debit, "balance_after": Decimal("9999.00")},
        {"amount": Decimal("25.00"), "transaction_type": TransactionType.debit, "balance_after": Decimal("9974.00")},
    ]

    result = reconcile_rows(rows)

    assert not result.fully_reconciled
    assert result.total_rows == 3
    assert result.passed_rows == 2
    assert result.failing_indices == [2]


def test_document_level_check_passes_when_totals_balance():
    assert document_level_check(
        opening_balance=Decimal("1000.00"),
        closing_balance=Decimal("1025.00"),
        total_credits=Decimal("100.00"),
        total_debits=Decimal("75.00"),
    )


def test_document_level_check_fails_when_totals_dont_balance():
    assert not document_level_check(
        opening_balance=Decimal("1000.00"),
        closing_balance=Decimal("2000.00"),
        total_credits=Decimal("100.00"),
        total_debits=Decimal("75.00"),
    )
