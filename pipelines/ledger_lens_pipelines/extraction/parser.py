"""
Applies a cached parsing spec to extracted rows — deterministic, no AI,
no tokens. This is what runs on every page after a layout's spec has been
induced once. See docs/architecture.md §2.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from ledger_lens_pipelines.extraction.ocr import ExtractedPage


@dataclass
class ParsedRow:
    page_number: int
    row_index: int
    raw_date: str
    raw_description: str
    raw_amount: str
    raw_type_label: str
    raw_balance: str | None
    amount: Decimal
    balance_after: Decimal | None


class ParseError(ValueError):
    """Raised for a row that doesn't fit the spec — routed to review, not guessed at."""


def _cell(cells: list[str], index: int | None) -> str | None:
    if index is None or index >= len(cells):
        return None
    return cells[index].strip()


def _to_decimal(raw: str) -> Decimal:
    cleaned = raw.replace(",", "").replace("₦", "").replace("$", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation as e:
        raise ParseError(f"Unparseable amount: {raw!r}") from e


def parse_page(page: ExtractedPage, spec: dict) -> list[ParsedRow]:
    columns = spec["columns"]
    skip_patterns = [re.compile(p) for p in spec.get("skip_row_patterns", [])]
    convention = spec["amount_convention"]

    parsed: list[ParsedRow] = []

    for row_index, row in enumerate(page.rows):
        cells = row.cells
        description = _cell(cells, columns.get("description")) or ""

        if any(p.search(description) for p in skip_patterns):
            continue
        if not description and not _cell(cells, columns.get("date")):
            continue  # blank row

        raw_date = _cell(cells, columns.get("date")) or ""
        raw_balance = _cell(cells, columns.get("balance"))

        if convention == "separate_debit_credit_columns":
            debit_raw = _cell(cells, columns.get("debit"))
            credit_raw = _cell(cells, columns.get("credit"))
            if credit_raw:
                amount = _to_decimal(credit_raw)
                raw_amount = credit_raw
                raw_type_label = "credit"
            elif debit_raw:
                amount = _to_decimal(debit_raw)
                raw_amount = debit_raw
                raw_type_label = "debit"
            else:
                continue  # neither column populated — not a transaction row

        elif convention == "single_signed_amount":
            amount_raw = _cell(cells, columns.get("amount")) or ""
            signed = _to_decimal(amount_raw)
            amount = abs(signed)
            raw_amount = amount_raw
            raw_type_label = "credit" if signed >= 0 else "debit"

        elif convention == "single_amount_with_flag":
            amount_raw = _cell(cells, columns.get("amount")) or ""
            flag_raw = _cell(cells, columns.get("type_flag")) or ""
            amount = _to_decimal(amount_raw)
            raw_amount = amount_raw
            raw_type_label = flag_raw

        else:
            raise ParseError(f"Unsupported amount_convention: {convention}")

        parsed.append(
            ParsedRow(
                page_number=page.page_number,
                row_index=row_index,
                raw_date=raw_date,
                raw_description=description,
                raw_amount=raw_amount,
                raw_type_label=raw_type_label,
                raw_balance=raw_balance,
                amount=amount,
                balance_after=_to_decimal(raw_balance) if raw_balance else None,
            )
        )

    return parsed


def parse_date(raw_date: str, date_format: str) -> datetime:
    return datetime.strptime(raw_date.strip(), date_format)


_OPENING = re.compile(r"(?i)\b(opening balance|balance b/?f|brought forward)\b")
_CLOSING = re.compile(r"(?i)\b(closing balance|balance c/?f|carried forward)\b")


def find_balance_anchors(page: ExtractedPage, spec: dict) -> dict[str, Decimal]:
    """
    Reads the statement's own printed opening and closing balances. These
    rows are skipped as transactions, but they are what the document-level
    proof (opening + credits - debits = closing) is checked against, and the
    opening balance anchors the very first transaction's row-level check.
    """

    columns = spec["columns"]
    anchors: dict[str, Decimal] = {}
    for row in page.rows:
        cells = row.cells
        text = " ".join(c for c in cells if c)
        balance_raw = _cell(cells, columns.get("balance"))
        if not balance_raw:
            continue
        try:
            value = _to_decimal(balance_raw)
        except ParseError:
            continue
        if _OPENING.search(text) and "opening" not in anchors:
            anchors["opening"] = value
        elif _CLOSING.search(text):
            anchors["closing"] = value
    return anchors
