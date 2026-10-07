"""
Layout fingerprinting and canonical-type normalization.

A "layout" is a bank statement's header row + column structure. Many banks
share the same layout because they run the same core banking platform
(Finacle, T24, Flexcube, etc.) — fingerprinting by layout rather than by
bank is what keeps the number of parsing specs far smaller than the number
of banks. See docs/architecture.md §2.
"""

import hashlib
import json


def fingerprint_layout(header_tokens: list[str], column_count: int) -> str:
    """
    Deterministic hash of a statement's header row + column count.
    Two documents with the same fingerprint are assumed parseable by the
    same cached spec — this is the cache key for layout_specs.
    """

    normalized_tokens = [t.strip().lower() for t in header_tokens]
    payload = json.dumps({"tokens": normalized_tokens, "columns": column_count}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def chunk_hash(document_id: str, page_start: int, page_end: int) -> str:
    """
    Deterministic id for a page-range chunk. Used as the idempotency key —
    a chunk message redelivered by the queue hashes to the same value, so
    a worker can detect "already processed" and skip re-work safely.
    """

    payload = f"{document_id}:{page_start}:{page_end}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# Fallback marker lists used only until a bank's spec explicitly overrides
# them — the induced LayoutSpec.spec["credit_markers"] / ["debit_markers"]
# take precedence once a layout has been learned.
DEFAULT_CREDIT_MARKERS = {"cr", "credit", "deposit", "c"}
DEFAULT_DEBIT_MARKERS = {"dr", "debit", "withdrawal", "d"}


def normalize_transaction_type(raw_label: str, spec: dict | None = None) -> str:
    """
    Maps a bank's own label ("CR", "Credit", "Deposit", "DR", "Debit",
    "Withdrawal", ...) to the canonical enum the rest of the system uses.
    Raises ValueError on an unrecognized label rather than guessing —
    an unrecognized label should route to human review, not a silent
    wrong classification.
    """

    label = raw_label.strip().lower()

    credit_markers = set(spec.get("credit_markers", [])) if spec else set()
    debit_markers = set(spec.get("debit_markers", [])) if spec else set()
    credit_markers = {m.lower() for m in credit_markers} | DEFAULT_CREDIT_MARKERS
    debit_markers = {m.lower() for m in debit_markers} | DEFAULT_DEBIT_MARKERS

    if label in credit_markers:
        return "credit"
    if label in debit_markers:
        return "debit"

    raise ValueError(f"Unrecognized transaction type label: {raw_label!r}")
