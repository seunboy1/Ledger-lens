from ledger_lens_pipelines.extraction.chunking import PageRange
from ledger_lens_pipelines.extraction.merge import check_completeness


def test_completeness_passes_when_all_chunks_done():
    done = [PageRange(1, 40), PageRange(41, 80)]
    result = check_completeness(total_pages=80, pages_per_chunk=40, done_ranges=done)

    assert result.complete
    assert result.expected_chunks == 2
    assert result.done_chunks == 2
    assert result.missing_ranges == []


def test_completeness_fails_and_localizes_the_missing_range():
    done = [PageRange(1, 40)]  # second chunk never reported done
    result = check_completeness(total_pages=80, pages_per_chunk=40, done_ranges=done)

    assert not result.complete
    assert result.expected_chunks == 2
    assert result.done_chunks == 1
    assert result.missing_ranges == [PageRange(41, 80)]


def test_completeness_on_a_2000_page_document_with_one_dropped_chunk():
    # Simulate 50 expected chunks, chunk #27 (pages 1041-1080) silently failed.
    done = [PageRange(i * 40 + 1, i * 40 + 40) for i in range(50) if i != 26]
    result = check_completeness(total_pages=2000, pages_per_chunk=40, done_ranges=done)

    assert not result.complete
    assert result.missing_ranges == [PageRange(1041, 1080)]
    # The fix requeues only the missing 40 pages, not the other 1960.
    assert result.missing_ranges[0].page_count == 40
