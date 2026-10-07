"""
Induces a parsing spec from a small sample of pages — the ONLY point in
the whole pipeline where the LLM sees document content, and only on a
layout-fingerprint cache miss. The spec it returns is cached forever
against that fingerprint (see flows/extract_statement.py), so the LLM
never touches this bank's layout again.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime

from app.config import get_settings
from ledger_lens_pipelines.extraction.ocr import ExtractedPage
from ledger_lens_pipelines.llm.client import LlmError, complete_json

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a precise bank-statement parsing analyst. You will be shown \
raw extracted table rows from a bank statement and must return a strict JSON parsing \
specification describing how to read this exact layout. Do not invent columns that \
aren't present. Respond with JSON only, matching this shape exactly:

{
  "columns": {"date": <int>, "description": <int>, "debit": <int|null>, "credit": <int|null>, \
"amount": <int|null>, "type_flag": <int|null>, "balance": <int|null>},
  "date_format": "<strftime-style format, e.g. %d/%m/%Y>",
  "amount_convention": "separate_debit_credit_columns" | "single_signed_amount" | \
"single_amount_with_flag",
  "credit_markers": [<strings that mean credit, e.g. "CR", "Credit", "Deposit">],
  "debit_markers": [<strings that mean debit, e.g. "DR", "Debit", "Withdrawal">],
  "skip_row_patterns": [<regex strings for rows to ignore, e.g. "^Opening Balance">]
}

Column indices are 0-indexed positions into each row's cell list. Use null for any \
column that doesn't apply to this statement's convention."""


@dataclass
class SpecInductionResult:
    spec: dict
    validated: bool
    validation_notes: str | None = None


def _rows_as_text(pages: list[ExtractedPage], max_rows: int = 15) -> str:
    lines = []
    for page in pages:
        if page.header_tokens:
            lines.append(f"HEADER: {page.header_tokens}")
        for row in page.rows[:max_rows]:
            lines.append(str(row.cells))
    return "\n".join(lines)


async def induce_spec(sample_pages: list[ExtractedPage]) -> dict:
    """
    Sends a small sample (2 pages, per the architecture doc) to the LLM and
    returns the parsing spec it proposes. Callers are expected to validate
    the result against a held-out page (see validate_spec) before caching it.

    With no inference provider configured (or if the provider fails), the
    spec is induced from header heuristics instead. Either way the output is
    the same strict structure and goes through the same validation, so the
    rest of the pipeline cannot tell the difference.
    """

    if get_settings().llm_provider_api_key:
        user_prompt = (
            "Here are sample rows extracted from a bank statement. Return the "
            "parsing spec as described.\n\n" + _rows_as_text(sample_pages)
        )
        try:
            spec = await complete_json(SYSTEM_PROMPT, user_prompt)
            spec.setdefault("induced_by", "llm")
            return spec
        except (LlmError, Exception) as e:  # noqa: BLE001
            log.warning("LLM spec induction failed (%s); falling back to header heuristics", e)

    return induce_spec_heuristic(sample_pages)


# --- heuristic induction ---------------------------------------------------

_DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%d-%b-%Y",
    "%d %b %Y",
    "%d-%b-%y",
    "%d/%m/%y",
    "%m/%d/%Y",
    "%d.%m.%Y",
]

_SKIP_ROWS = [r"(?i)^(opening|closing) balance", r"(?i)balance [bc]/?f", r"(?i)(brought|carried) forward"]


def _find(header: list[str], patterns: list[str], exclude: list[str] | None = None) -> int | None:
    for i, raw in enumerate(header):
        token = raw.lower().strip()
        if exclude and any(re.search(x, token) for x in exclude):
            continue
        if any(re.search(p, token) for p in patterns):
            return i
    return None


def _first_not_none(*values: int | None) -> int | None:
    return next((v for v in values if v is not None), None)


def _detect_date_format(samples: list[str]) -> str | None:
    samples = [s.strip() for s in samples if s and s.strip()]
    if not samples:
        return None
    for fmt in _DATE_FORMATS:
        try:
            for value in samples:
                datetime.strptime(value, fmt)
            return fmt
        except ValueError:
            continue
    return None


def induce_spec_heuristic(sample_pages: list[ExtractedPage]) -> dict:
    """
    Deterministic spec induction from a statement's header row. Covers the
    three amount conventions the parser supports; anything it cannot place
    produces a spec that validate_spec rejects, which routes the document to
    review rather than guessing.
    """

    header = next((p.header_tokens for p in sample_pages if p.header_tokens), [])
    columns: dict[str, int | None] = {
        # Prefer the transaction date over a value date when both exist.
        "date": _first_not_none(_find(header, [r"date"], exclude=[r"value"]), _find(header, [r"date"])),
        "description": _find(header, [r"narration", r"description", r"details", r"particulars", r"remarks", r"transaction"], exclude=[r"date", r"type"]),
        "debit": _find(header, [r"debit", r"withdraw", r"money out", r"paid out", r"^dr$"], exclude=[r"/"]),
        "credit": _find(header, [r"credit", r"deposit", r"lodg", r"money in", r"paid in", r"^cr$"], exclude=[r"/"]),
        "amount": _find(header, [r"amount", r"value$"], exclude=[r"date"]),
        "type_flag": _find(header, [r"dr\s*/\s*cr", r"cr\s*/\s*dr", r"^type$", r"indicator", r"flag"]),
        "balance": _find(header, [r"balance"]),
    }

    if columns["debit"] is not None and columns["credit"] is not None:
        convention = "separate_debit_credit_columns"
        columns["amount"] = None
        columns["type_flag"] = None
    elif columns["amount"] is not None and columns["type_flag"] is not None:
        convention = "single_amount_with_flag"
        columns["debit"] = columns["credit"] = None
    elif columns["amount"] is not None:
        convention = "single_signed_amount"
        columns["debit"] = columns["credit"] = columns["type_flag"] = None
    else:
        convention = "unknown"

    date_samples: list[str] = []
    flag_values: set[str] = set()
    for page in sample_pages:
        for row in page.rows:
            cells = row.cells
            if columns["date"] is not None and columns["date"] < len(cells):
                date_samples.append(cells[columns["date"]])
            if columns["type_flag"] is not None and columns["type_flag"] < len(cells):
                flag_values.add(cells[columns["type_flag"]].strip())

    date_format = _detect_date_format([d for d in date_samples if re.search(r"\d", d)][:20]) or "%d/%m/%Y"

    credit_markers = sorted(v for v in flag_values if re.match(r"(?i)^(c|cr|credit|deposit)$", v))
    debit_markers = sorted(v for v in flag_values if re.match(r"(?i)^(d|dr|debit|withdrawal)$", v))

    return {
        "columns": columns,
        "date_format": date_format,
        "amount_convention": convention,
        "credit_markers": credit_markers,
        "debit_markers": debit_markers,
        "skip_row_patterns": _SKIP_ROWS,
        "induced_by": "heuristic",
    }


def validate_spec(spec: dict, holdout_page: ExtractedPage) -> SpecInductionResult:
    """
    Sanity-checks an induced spec against a page it wasn't derived from,
    before the spec is trusted and cached. This is deliberately cheap and
    deterministic — no second LLM call — since its only job is catching an
    obviously wrong spec (e.g. a column index out of range) before it's
    applied to an entire document.
    """

    columns = spec.get("columns", {})
    required = ["date", "description"]
    for key in required:
        if columns.get(key) is None:
            return SpecInductionResult(spec=spec, validated=False, validation_notes=f"missing required column: {key}")

    convention = spec.get("amount_convention")
    if convention == "separate_debit_credit_columns":
        if columns.get("debit") is None or columns.get("credit") is None:
            return SpecInductionResult(
                spec=spec, validated=False, validation_notes="separate_debit_credit_columns needs both debit and credit"
            )
    elif convention in ("single_signed_amount", "single_amount_with_flag"):
        if columns.get("amount") is None:
            return SpecInductionResult(spec=spec, validated=False, validation_notes=f"{convention} needs an amount column")
    else:
        return SpecInductionResult(spec=spec, validated=False, validation_notes=f"unrecognized amount_convention: {convention}")

    if holdout_page.rows:
        max_index = max(v for v in columns.values() if v is not None)
        sample_row = holdout_page.rows[0].cells
        if max_index >= len(sample_row):
            return SpecInductionResult(
                spec=spec,
                validated=False,
                validation_notes=f"column index {max_index} out of range for holdout row width {len(sample_row)}",
            )

    return SpecInductionResult(spec=spec, validated=True)
