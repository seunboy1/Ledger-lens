import pytest

from app.services.layout import fingerprint_layout, normalize_transaction_type


def test_fingerprint_is_stable_regardless_of_case_and_whitespace():
    a = fingerprint_layout(["Date", " Description ", "DEBIT", "credit", "Balance"], 5)
    b = fingerprint_layout(["date", "description", "debit", "CREDIT", "balance"], 5)
    assert a == b


def test_fingerprint_differs_for_different_column_count():
    a = fingerprint_layout(["Date", "Description", "Amount"], 3)
    b = fingerprint_layout(["Date", "Description", "Amount"], 4)
    assert a != b


@pytest.mark.parametrize("label,expected", [
    ("CR", "credit"),
    ("Credit", "credit"),
    ("Deposit", "credit"),
    ("DR", "debit"),
    ("Debit", "debit"),
    ("Withdrawal", "debit"),
])
def test_normalize_transaction_type_handles_known_bank_variants(label, expected):
    assert normalize_transaction_type(label) == expected


def test_normalize_transaction_type_uses_spec_overrides():
    spec = {"credit_markers": ["INFLOW"], "debit_markers": ["OUTFLOW"]}
    assert normalize_transaction_type("INFLOW", spec) == "credit"
    assert normalize_transaction_type("OUTFLOW", spec) == "debit"


def test_normalize_transaction_type_raises_on_unknown_label():
    with pytest.raises(ValueError):
        normalize_transaction_type("???")
