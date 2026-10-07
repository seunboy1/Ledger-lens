"""
Completeness check — the guardrail against silently dropped pages.

Distinct from idempotency (which prevents duplicates): this catches a
chunk that failed without anyone noticing. A document only proceeds to
reconciliation once this passes. See docs/architecture.md §8.
"""

from dataclasses import dataclass

from ledger_lens_pipelines.extraction.chunking import PageRange, expected_chunk_count, find_gaps


@dataclass
class CompletenessResult:
    complete: bool
    expected_chunks: int
    done_chunks: int
    missing_ranges: list[PageRange]


def check_completeness(total_pages: int, pages_per_chunk: int, done_ranges: list[PageRange]) -> CompletenessResult:
    expected = expected_chunk_count(total_pages, pages_per_chunk)
    gaps = find_gaps(total_pages, done_ranges)

    return CompletenessResult(
        complete=len(gaps) == 0,
        expected_chunks=expected,
        done_chunks=len(done_ranges),
        missing_ranges=gaps,
    )
