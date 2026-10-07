"""
Splits a document's page count into fixed-size page-range chunks.

This is the mechanism that turns a 2,000-page statement into ~40-80
independent, parallelizable units of work instead of one long sequential
job. See docs/architecture.md §1.
"""

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class PageRange:
    start: int  # 1-indexed, inclusive
    end: int  # 1-indexed, inclusive

    @property
    def page_count(self) -> int:
        return self.end - self.start + 1


def compute_chunks(total_pages: int, pages_per_chunk: int) -> list[PageRange]:
    if total_pages <= 0:
        return []
    if pages_per_chunk <= 0:
        raise ValueError("pages_per_chunk must be positive")

    chunks: list[PageRange] = []
    start = 1
    while start <= total_pages:
        end = min(start + pages_per_chunk - 1, total_pages)
        chunks.append(PageRange(start=start, end=end))
        start = end + 1
    return chunks


def expected_chunk_count(total_pages: int, pages_per_chunk: int) -> int:
    if total_pages <= 0:
        return 0
    return ceil(total_pages / pages_per_chunk)


def find_gaps(total_pages: int, done_ranges: list[PageRange]) -> list[PageRange]:
    """
    Given the page ranges that have actually completed, returns the page
    ranges that are missing — i.e. what still needs to be (re)enqueued.
    Used by the completeness check so a dropped chunk requeues only the
    pages it covered, not the whole document. See docs/architecture.md §8.
    """

    if total_pages <= 0:
        return []

    covered = [False] * (total_pages + 1)  # 1-indexed
    for r in done_ranges:
        for p in range(r.start, r.end + 1):
            if 1 <= p <= total_pages:
                covered[p] = True

    gaps: list[PageRange] = []
    p = 1
    while p <= total_pages:
        if not covered[p]:
            gap_start = p
            while p <= total_pages and not covered[p]:
                p += 1
            gaps.append(PageRange(start=gap_start, end=p - 1))
        else:
            p += 1
    return gaps
