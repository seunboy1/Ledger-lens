from decimal import Decimal

import pytest

from ledger_lens_pipelines.extraction.ocr import ExtractedPage, ExtractedRow
from ledger_lens_pipelines.extraction.parser import ParseError, parse_date, parse_page


def test_parses_separate_debit_credit_columns():
    spec = {
        "columns": {"date": 0, "description": 1, "debit": 2, "credit": 3, "balance": 4},
        "amount_convention": "separate_debit_credit_columns",
        "skip_row_patterns": [],
    }
    page = ExtractedPage(
        page_number=1,
        header_tokens=["Date", "Description", "Debit", "Credit", "Balance"],
        rows=[
            ExtractedRow(cells=["04/03/2026", "POS Purchase", "1,240.00", "", "8,760.00"]),
            ExtractedRow(cells=["09/03/2026", "Salary", "", "3,500.00", "12,260.00"]),
        ],
    )

    rows = parse_page(page, spec)

    assert len(rows) == 2
    assert rows[0].raw_type_label == "debit"
    assert rows[0].amount == Decimal("1240.00")
    assert rows[0].balance_after == Decimal("8760.00")
    assert rows[1].raw_type_label == "credit"
    assert rows[1].amount == Decimal("3500.00")


def test_parses_single_signed_amount_convention():
    spec = {
        "columns": {"date": 0, "description": 1, "amount": 2, "balance": 3},
        "amount_convention": "single_signed_amount",
        "skip_row_patterns": [],
    }
    page = ExtractedPage(
        page_number=1,
        header_tokens=[],
        rows=[
            ExtractedRow(cells=["06/03/2026", "Adobe Subscription", "-54.99", "8705.01"]),
            ExtractedRow(cells=["09/03/2026", "Deposit", "3500.00", "12205.01"]),
        ],
    )

    rows = parse_page(page, spec)

    assert rows[0].raw_type_label == "debit"
    assert rows[0].amount == Decimal("54.99")  # stored as absolute value
    assert rows[1].raw_type_label == "credit"


def test_parses_single_amount_with_flag_convention():
    spec = {
        "columns": {"date": 0, "description": 1, "amount": 2, "type_flag": 3, "balance": 4},
        "amount_convention": "single_amount_with_flag",
        "skip_row_patterns": [],
    }
    page = ExtractedPage(
        page_number=1,
        header_tokens=[],
        rows=[
            ExtractedRow(cells=["11/03/2026", "Purchase", "299.00", "DR", "11906.01"]),
            ExtractedRow(cells=["14/03/2026", "Refund", "15.99", "CR", "11922.00"]),
        ],
    )

    rows = parse_page(page, spec)

    assert rows[0].raw_type_label == "DR"
    assert rows[1].raw_type_label == "CR"


def test_skip_row_patterns_exclude_summary_lines():
    spec = {
        "columns": {"date": 0, "description": 1, "debit": 2, "credit": 3, "balance": 4},
        "amount_convention": "separate_debit_credit_columns",
        "skip_row_patterns": [r"^Opening Balance", r"^Total"],
    }
    page = ExtractedPage(
        page_number=1,
        header_tokens=[],
        rows=[
            ExtractedRow(cells=["01/03/2026", "Opening Balance", "", "", "10000.00"]),
            ExtractedRow(cells=["04/03/2026", "POS Purchase", "1240.00", "", "8760.00"]),
            ExtractedRow(cells=["", "Total", "1240.00", "3500.00", ""]),
        ],
    )

    rows = parse_page(page, spec)

    assert len(rows) == 1
    assert rows[0].raw_description == "POS Purchase"


def test_thousands_separators_and_currency_symbols_are_stripped():
    spec = {
        "columns": {"date": 0, "description": 1, "debit": 2, "credit": 3, "balance": 4},
        "amount_convention": "separate_debit_credit_columns",
        "skip_row_patterns": [],
    }
    page = ExtractedPage(
        page_number=1,
        header_tokens=[],
        rows=[ExtractedRow(cells=["04/03/2026", "Big Purchase", "$1,234,567.89", "", "0.00"])],
    )

    rows = parse_page(page, spec)

    assert rows[0].amount == Decimal("1234567.89")


def test_unparseable_amount_raises_parse_error_rather_than_guessing():
    spec = {
        "columns": {"date": 0, "description": 1, "debit": 2, "credit": 3, "balance": 4},
        "amount_convention": "separate_debit_credit_columns",
        "skip_row_patterns": [],
    }
    page = ExtractedPage(
        page_number=1,
        header_tokens=[],
        rows=[ExtractedRow(cells=["04/03/2026", "Corrupted", "not-a-number", "", "0.00"])],
    )

    with pytest.raises(ParseError):
        parse_page(page, spec)


def test_parse_date_respects_the_specs_format():
    assert parse_date("04/03/2026", "%d/%m/%Y").day == 4
    assert parse_date("03/04/2026", "%m/%d/%Y").day == 4
