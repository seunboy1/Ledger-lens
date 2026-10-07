from ledger_lens_pipelines.extraction.ocr import ExtractedPage, ExtractedRow
from ledger_lens_pipelines.extraction.spec_induction import validate_spec


def _holdout(cells: list[str]) -> ExtractedPage:
    return ExtractedPage(page_number=3, header_tokens=[], rows=[ExtractedRow(cells=cells)])


def test_valid_spec_passes_validation():
    spec = {
        "columns": {"date": 0, "description": 1, "debit": 2, "credit": 3, "balance": 4},
        "amount_convention": "separate_debit_credit_columns",
        "credit_markers": ["CR"],
        "debit_markers": ["DR"],
        "skip_row_patterns": [],
    }
    holdout = _holdout(["04/03/2026", "Purchase", "100.00", "", "900.00"])

    result = validate_spec(spec, holdout)

    assert result.validated
    assert result.validation_notes is None


def test_missing_required_column_fails_validation():
    spec = {
        "columns": {"date": 0, "description": None, "debit": 2, "credit": 3, "balance": 4},
        "amount_convention": "separate_debit_credit_columns",
    }
    holdout = _holdout(["04/03/2026", "Purchase", "100.00", "", "900.00"])

    result = validate_spec(spec, holdout)

    assert not result.validated
    assert "description" in result.validation_notes


def test_separate_columns_convention_requires_both_debit_and_credit():
    spec = {
        "columns": {"date": 0, "description": 1, "debit": 2, "credit": None, "balance": 4},
        "amount_convention": "separate_debit_credit_columns",
    }
    holdout = _holdout(["04/03/2026", "Purchase", "100.00", "", "900.00"])

    result = validate_spec(spec, holdout)

    assert not result.validated


def test_unrecognized_amount_convention_fails_validation():
    spec = {
        "columns": {"date": 0, "description": 1},
        "amount_convention": "something_the_model_made_up",
    }
    holdout = _holdout(["04/03/2026", "Purchase"])

    result = validate_spec(spec, holdout)

    assert not result.validated
    assert "unrecognized amount_convention" in result.validation_notes


def test_column_index_out_of_range_for_holdout_row_fails_validation():
    spec = {
        "columns": {"date": 0, "description": 1, "amount": 5},  # index 5 doesn't exist below
        "amount_convention": "single_signed_amount",
    }
    holdout = _holdout(["04/03/2026", "Purchase", "100.00"])  # only 3 cells

    result = validate_spec(spec, holdout)

    assert not result.validated
    assert "out of range" in result.validation_notes
