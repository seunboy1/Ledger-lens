from ledger_lens_pipelines.extraction.chunking import PageRange, compute_chunks, expected_chunk_count, find_gaps


def test_compute_chunks_splits_evenly():
    chunks = compute_chunks(total_pages=100, pages_per_chunk=40)
    assert chunks == [PageRange(1, 40), PageRange(41, 80), PageRange(81, 100)]


def test_compute_chunks_handles_exact_multiple():
    chunks = compute_chunks(total_pages=80, pages_per_chunk=40)
    assert chunks == [PageRange(1, 40), PageRange(41, 80)]


def test_compute_chunks_single_chunk_when_smaller_than_chunk_size():
    chunks = compute_chunks(total_pages=10, pages_per_chunk=40)
    assert chunks == [PageRange(1, 10)]


def test_compute_chunks_empty_document():
    assert compute_chunks(total_pages=0, pages_per_chunk=40) == []


def test_a_2000_page_statement_produces_50_chunks_at_40_pages_each():
    chunks = compute_chunks(total_pages=2000, pages_per_chunk=40)
    assert len(chunks) == 50
    assert chunks[0] == PageRange(1, 40)
    assert chunks[-1] == PageRange(1961, 2000)


def test_expected_chunk_count_matches_compute_chunks_length():
    for total, per in [(2000, 40), (99, 25), (1, 40), (0, 40)]:
        assert expected_chunk_count(total, per) == len(compute_chunks(total, per))


def test_find_gaps_returns_empty_when_fully_covered():
    done = [PageRange(1, 40), PageRange(41, 80), PageRange(81, 100)]
    assert find_gaps(100, done) == []


def test_find_gaps_finds_a_missing_middle_chunk():
    done = [PageRange(1, 40), PageRange(81, 100)]  # chunk 2 (41-80) never completed
    gaps = find_gaps(100, done)
    assert gaps == [PageRange(41, 80)]


def test_find_gaps_finds_multiple_disjoint_missing_ranges():
    done = [PageRange(1, 20)]
    gaps = find_gaps(100, done)
    assert gaps == [PageRange(21, 100)]


def test_find_gaps_with_no_pages_done_returns_the_whole_document():
    gaps = find_gaps(50, [])
    assert gaps == [PageRange(1, 50)]
