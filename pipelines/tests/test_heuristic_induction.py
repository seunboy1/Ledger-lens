from decimal import Decimal

import pytest

from ledger_lens_pipelines.extraction.ocr import ExtractedPage, ExtractedRow
from ledger_lens_pipelines.extraction.parser import find_balance_anchors, parse_page
from ledger_lens_pipelines.extraction.spec_induction import induce_spec_heuristic, validate_spec


def page(header, rows):
    return ExtractedPage(page_number=1, header_tokens=header, rows=[ExtractedRow(cells=r) for r in rows])


def test_separate_columns_prefers_transaction_date_over_value_date():
    p = page(
        ["Value Date", "Trans Date", "Narration", "Debit", "Credit", "Balance"],
        [["02/04/2026", "01/04/2026", "Opening Balance", "", "", "1,000.00"],
         ["03/04/2026", "02/04/2026", "POS PURCHASE", "200.00", "", "800.00"]],
    )
    spec = induce_spec_heuristic([p])
    assert spec["columns"]["date"] == 1
    assert spec["amount_convention"] == "separate_debit_credit_columns"
    assert spec["date_format"] == "%d/%m/%Y"
    assert validate_spec(spec, p).validated
    rows = parse_page(p, spec)
    assert len(rows) == 1 and rows[0].amount == Decimal("200.00")
    assert find_balance_anchors(p, spec) == {"opening": Decimal("1000.00")}


def test_flag_convention_collects_markers():
    p = page(
        ["Txn Date", "Details", "Amount", "DR/CR", "Balance"],
        [["01-Jul-2026", "POS SETTLEMENT", "500.00", "CR", "1,500.00"],
         ["02-Jul-2026", "FEE", "75.00", "DR", "1,425.00"]],
    )
    spec = induce_spec_heuristic([p])
    assert spec["amount_convention"] == "single_amount_with_flag"
    assert spec["date_format"] == "%d-%b-%Y"
    assert spec["credit_markers"] == ["CR"] and spec["debit_markers"] == ["DR"]


def test_signed_amount_convention_and_iso_dates():
    p = page(["Date", "Description", "Amount", "Balance"], [["2026-04-27", "INWARD TRANSFER", "150,000.00", "1,400,000.00"]])
    spec = induce_spec_heuristic([p])
    assert spec["amount_convention"] == "single_signed_amount"
    assert spec["date_format"] == "%Y-%m-%d"


def test_unrecognisable_header_fails_validation_instead_of_guessing():
    p = page(["Col A", "Col B", "Col C"], [["x", "y", "z"]])
    spec = induce_spec_heuristic([p])
    assert not validate_spec(spec, p).validated


@pytest.mark.parametrize("line", ["Closing Balance", "Balance C/F", "Carried forward"])
def test_closing_anchor_variants(line):
    p = page(["Date", "Description", "Amount", "Balance"], [["2026-09-30", line, "", "9,999.00"]])
    spec = induce_spec_heuristic([p])
    assert find_balance_anchors(p, spec) == {"closing": Decimal("9999.00")}


def test_every_sample_layout_round_trips_through_extraction():
    """Render each synthetic bank layout to PDF and parse it back without a model."""
    from app.dev.sample_statements import crestline_household_account, demo_statements, palmgrove_current_account, render_pdf
    from ledger_lens_pipelines.extraction.ocr import count_pages, extract_page_range

    for statement in [*demo_statements(), palmgrove_current_account(), crestline_household_account()]:
        pdf = render_pdf(statement)
        pages = [p for p in extract_page_range(pdf, 1, count_pages(pdf)) if p.rows]
        spec = induce_spec_heuristic(pages[:2])
        assert validate_spec(spec, pages[-1]).validated, statement.filename
        rows = [r for p in pages for r in parse_page(p, spec)]
        assert len(rows) == len(statement.lines), statement.filename
        anchors = {}
        for p in pages:
            anchors.update(find_balance_anchors(p, spec))
        assert anchors == {"opening": statement.opening, "closing": statement.closing}, statement.filename
