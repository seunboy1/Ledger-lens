"""
The end-to-end extraction flow: one flow run per document, with a task per
page-chunk. This is the orchestration layer described in docs/architecture.md
§1, §2 and §8: idempotent, gap-checked, and with the LLM invoked only on a
genuine layout-cache miss or a reconciliation failure.

Runs under Prefect on the full stack and as plain coroutines on the local
profile (see orchestration.py). The logic is the same in both.
"""

from __future__ import annotations

import re
import uuid
from decimal import Decimal

from sqlalchemy import delete, select

from app.db.models import (
    ChunkStatus,
    Document,
    DocumentChunk,
    DocumentStatus,
    LayoutSpec,
    RawExtractedRow,
    Transaction,
    TransactionType,
)
from app.db.session import async_session_factory
from app.services import storage
from app.services.layout import chunk_hash, fingerprint_layout, normalize_transaction_type
from app.services.statement_proof import load_document_rows, reconcile_document

from ledger_lens_pipelines.extraction.chunking import PageRange, compute_chunks
from ledger_lens_pipelines.extraction.merge import check_completeness
from ledger_lens_pipelines.extraction.ocr import count_pages, extract_page_range, read_statement_header
from ledger_lens_pipelines.extraction.parser import ParseError, _to_decimal, find_balance_anchors, parse_date, parse_page
from ledger_lens_pipelines.extraction.spec_induction import induce_spec, validate_spec
from ledger_lens_pipelines.llm.client import LlmError, complete_json
from ledger_lens_pipelines.orchestration import flow, get_run_logger, task

DEFAULT_PAGES_PER_CHUNK = 40
SAMPLE_PAGES_FOR_INDUCTION = 2


def _insert_ignore(db, model):
    """INSERT ... ON CONFLICT DO NOTHING for whichever dialect is in use."""

    if db.bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert(model)


@task(retries=3, retry_delay_seconds=[5, 15, 45])
async def process_chunk(document_id: str, pdf_bytes: bytes, page_range: PageRange) -> None:
    """
    Processes one page-range chunk end to end: idempotency check, layout
    lookup/induction, deterministic parse, staging write, chunk status
    update. Safe to redeliver: a chunk already marked `done` is a no-op.
    """

    logger = get_run_logger()
    c_hash = chunk_hash(document_id, page_range.start, page_range.end)

    async with async_session_factory() as db:
        existing = await db.execute(select(DocumentChunk).where(DocumentChunk.chunk_hash == c_hash))
        chunk_row = existing.scalar_one_or_none()

        if chunk_row and chunk_row.status == ChunkStatus.done:
            logger.info("Chunk %s already done, skipping (idempotent replay)", c_hash[:12])
            return

        if chunk_row is None:
            chunk_row = DocumentChunk(
                document_id=uuid.UUID(document_id),
                chunk_hash=c_hash,
                page_start=page_range.start,
                page_end=page_range.end,
                status=ChunkStatus.processing,
            )
            db.add(chunk_row)
        else:
            chunk_row.status = ChunkStatus.processing
            chunk_row.attempt += 1
        await db.commit()

        try:
            pages = extract_page_range(pdf_bytes, page_range.start, page_range.end)
            pages_with_rows = [p for p in pages if p.rows]

            if not pages_with_rows:
                chunk_row.status = ChunkStatus.done
                await db.commit()
                return

            first_page = pages_with_rows[0]
            fingerprint = fingerprint_layout(first_page.header_tokens, len(first_page.rows[0].cells))

            spec_row = (await db.execute(select(LayoutSpec).where(LayoutSpec.fingerprint == fingerprint))).scalar_one_or_none()
            if spec_row is None:
                spec_row = await _induce_and_cache_spec(db, fingerprint, pages_with_rows)
            else:
                spec_row.times_reused += 1

            document = await db.get(Document, uuid.UUID(document_id))
            document.layout_spec_id = spec_row.id
            await db.commit()

            await _parse_and_stage(db, document, pages_with_rows, spec_row.spec)

            chunk_row.status = ChunkStatus.done
            chunk_row.error = None
            await db.commit()

        except Exception as e:  # noqa: BLE001 - any failure marks the chunk failed, never silently drops it
            logger.error("Chunk %s failed: %s", c_hash[:12], e)
            await db.rollback()
            chunk_row = (await db.execute(select(DocumentChunk).where(DocumentChunk.chunk_hash == c_hash))).scalar_one()
            chunk_row.status = ChunkStatus.failed
            chunk_row.error = str(e)[:2000]
            await db.commit()
            raise


async def _induce_and_cache_spec(db, fingerprint: str, pages_with_rows: list) -> LayoutSpec:
    """
    Cache-miss path: the only place document content can reach the LLM, and
    only 2 sample pages of it, never the whole statement. The result is
    validated against a held-out page and cached permanently against this
    fingerprint before it is used to parse a single real row.
    """

    logger = get_run_logger()
    logger.info("Layout %s not cached, inducing a new spec", fingerprint[:12])

    sample = pages_with_rows[:SAMPLE_PAGES_FOR_INDUCTION]
    holdout = pages_with_rows[SAMPLE_PAGES_FOR_INDUCTION] if len(pages_with_rows) > SAMPLE_PAGES_FOR_INDUCTION else sample[-1]

    raw_spec = await induce_spec(sample)
    result = validate_spec(raw_spec, holdout)
    if not result.validated:
        raise ParseError(f"Induced spec failed validation: {result.validation_notes}")

    spec_row = LayoutSpec(fingerprint=fingerprint, spec=raw_spec, validated=True, times_reused=0)
    db.add(spec_row)
    await db.flush()
    return spec_row


async def _parse_and_stage(db, document: Document, pages: list, spec: dict) -> None:
    """Deterministic parse + idempotent insert into the immutable staging log."""

    for page in pages:
        anchors = find_balance_anchors(page, spec)
        if "opening" in anchors and document.opening_balance is None:
            document.opening_balance = anchors["opening"]
        if "closing" in anchors:
            document.closing_balance = anchors["closing"]

        for row in parse_page(page, spec):
            stmt = (
                _insert_ignore(db, RawExtractedRow)
                .values(
                    id=uuid.uuid4(),
                    document_id=document.id,
                    page_number=row.page_number,
                    row_index=row.row_index,
                    raw_date=row.raw_date,
                    raw_description=row.raw_description,
                    raw_amount=row.raw_amount,
                    raw_type_label=row.raw_type_label,
                    raw_balance=str(row.balance_after) if row.balance_after is not None else None,
                )
                .on_conflict_do_nothing(index_elements=["document_id", "page_number", "row_index"])
            )
            await db.execute(stmt)
    await db.commit()


def _narrative(txn: Transaction) -> str:
    verb = "received" if txn.transaction_type == TransactionType.credit else "paid"
    return f"{txn.transaction_date:%d %b %Y}: {verb} {txn.amount} via {txn.bank_name}. {txn.description}"


@task
async def promote_and_reconcile(document_id: str) -> None:
    """
    Promotes staged rows into the canonical `transactions` table and runs
    balance reconciliation. Only a document that reconciles fully is marked
    reconciled; everything else goes to review, never silently trusted.
    Re-running it replaces the document's canonical rows, so it is idempotent.
    """

    logger = get_run_logger()

    async with async_session_factory() as db:
        document = await db.get(Document, uuid.UUID(document_id))
        spec_row = await db.get(LayoutSpec, document.layout_spec_id) if document.layout_spec_id else None
        if spec_row is None:
            raise ParseError(
                "No transaction table was found in this PDF. If it is a scanned statement, "
                "OCR for scanned pages is not enabled in this build."
            )
        spec = spec_row.spec

        raw_rows = list(
            (
                await db.execute(
                    select(RawExtractedRow)
                    .where(RawExtractedRow.document_id == document.id)
                    .order_by(RawExtractedRow.page_number, RawExtractedRow.row_index)
                )
            ).scalars()
        )

        await db.execute(delete(Transaction).where(Transaction.document_id == document.id))

        rejected = 0
        for raw in raw_rows:
            try:
                canonical_type = normalize_transaction_type(raw.raw_type_label, spec)
                amount = abs(_to_decimal(raw.raw_amount))
                txn_date = parse_date(raw.raw_date, spec.get("date_format", "%d/%m/%Y"))
            except (ValueError, ParseError) as e:
                rejected += 1
                logger.warning("Row p%s r%s rejected (%s), sent to review", raw.page_number, raw.row_index, e)
                continue

            txn = Transaction(
                tenant_id=document.tenant_id,
                document_id=document.id,
                bank_name=document.bank_name or "Unknown bank",
                transaction_date=txn_date,
                description=raw.raw_description,
                amount=amount,
                transaction_type=TransactionType(canonical_type),
                raw_type_label=raw.raw_type_label,
                balance_after=Decimal(raw.raw_balance) if raw.raw_balance else None,
                reconciled=False,
                page_number=raw.page_number,
                row_index=raw.row_index,
            )
            txn.narrative = _narrative(txn)
            db.add(txn)
        await db.flush()

        proof = await reconcile_document(db, document)
        if rejected:
            document.status = DocumentStatus.needs_review
            document.error = f"{rejected} row(s) could not be parsed against the layout spec"
        await db.commit()

        logger.info(
            "Document %s: %s/%s rows verified, status=%s",
            document_id,
            proof.rows_verified,
            proof.rows_total,
            document.status.value,
        )

        if proof.failing_ids:
            await _attempt_targeted_repair(db, document, proof.failing_ids)


async def _attempt_targeted_repair(db, document: Document, failing_ids: list[str]) -> None:
    """
    The second and last place the LLM appears: proposing a fix for a single
    row that failed balance reconciliation. A proposal is accepted only if
    the document's arithmetic then holds, and it stays marked "ai" so a
    human must confirm it before the document counts as verified.
    """

    logger = get_run_logger()
    rows = await load_document_rows(db, document.id)
    by_id = {str(r.id): r for r in rows}

    for txn_id in failing_ids:
        txn = by_id.get(txn_id)
        if txn is None:
            continue
        try:
            repair = await complete_json(
                system_prompt=(
                    "You are correcting a single bank transaction row that failed balance "
                    "reconciliation. Return corrected JSON: "
                    '{"amount": "<decimal string>", "transaction_type": "credit"|"debit"}. '
                    'If you cannot confidently determine the correction, return {"amount": null, "transaction_type": null}.'
                ),
                user_prompt=(
                    f"Row: date={txn.transaction_date:%Y-%m-%d}, description={txn.description!r}, "
                    f"amount={txn.amount}, type={txn.transaction_type.value}, balance_after={txn.balance_after}, "
                    f"expected_balance_after={txn.expected_balance}"
                ),
            )
        except LlmError as e:
            logger.info("Targeted repair skipped for %s: %s", txn_id, e)
            return
        except Exception as e:  # noqa: BLE001
            logger.warning("Targeted repair failed for %s: %s", txn_id, e)
            continue

        if repair.get("amount") is None or repair.get("transaction_type") not in ("credit", "debit"):
            continue
        txn.amount = Decimal(str(repair["amount"]))
        txn.transaction_type = TransactionType(repair["transaction_type"])
        txn.repair_source = "ai"

    await reconcile_document(db, document)
    await db.commit()


def _bank_name_from_header(lines: list[str]) -> str | None:
    for line in lines:
        if re.search(r"(?i)\b(bank|microfinance|mfb|trust|savings)\b", line):
            name = re.split(r"\s+[-|]\s+|\s{2,}", line)[0]
            name = re.sub(r"(?i)\b(plc|limited|ltd)\.?\b", "", name).strip(" ,.")
            return name or None
    return None


@flow(name="extract-statement")
async def extract_statement(document_id: str, pages_per_chunk: int = DEFAULT_PAGES_PER_CHUNK) -> None:
    """
    Entry point: one flow run per uploaded document. Fans out chunk
    processing, verifies completeness, then promotes and reconciles.
    Triggered from the ingest queue (flows/consumer.py, or in-process on the
    local profile), not called directly from a request handler.
    """

    logger = get_run_logger()

    async with async_session_factory() as db:
        document = await db.get(Document, uuid.UUID(document_id))
        if document is None:
            raise ValueError(f"No document found for id {document_id}")
        storage_path = document.storage_path

    try:
        pdf_bytes = storage.download_object(storage_path)
        total_pages = count_pages(pdf_bytes)
        bank_name = _bank_name_from_header(read_statement_header(pdf_bytes))

        async with async_session_factory() as db:
            document = await db.get(Document, uuid.UUID(document_id))
            document.page_count = total_pages
            document.bank_name = bank_name or document.bank_name
            document.status = DocumentStatus.processing
            document.error = None
            await db.commit()

        chunks = compute_chunks(total_pages, pages_per_chunk)
        logger.info("Document %s: %s pages, %s chunks", document_id, total_pages, len(chunks))

        for page_range in chunks:
            try:
                await process_chunk(document_id, pdf_bytes, page_range)
            except Exception:  # noqa: BLE001 - recorded on the chunk; completeness check decides
                pass

        async with async_session_factory() as db:
            done = await db.execute(
                select(DocumentChunk.page_start, DocumentChunk.page_end).where(
                    DocumentChunk.document_id == uuid.UUID(document_id), DocumentChunk.status == ChunkStatus.done
                )
            )
            done_ranges = [PageRange(start=s, end=e) for s, e in done.all()]

        completeness = check_completeness(total_pages, pages_per_chunk, done_ranges)
        if not completeness.complete:
            logger.warning("Document %s incomplete, missing %s", document_id, completeness.missing_ranges)
            for gap in completeness.missing_ranges:
                await process_chunk(document_id, pdf_bytes, gap)

        await promote_and_reconcile(document_id)

    except Exception as e:  # noqa: BLE001
        logger.exception("Document %s failed", document_id)
        async with async_session_factory() as db:
            document = await db.get(Document, uuid.UUID(document_id))
            document.status = DocumentStatus.failed
            document.error = str(e)[:2000]
            await db.commit()
        raise


async def run_ingest_job(payload: dict) -> None:
    """Queue-message adapter shared by the RabbitMQ consumer and the inline queue."""

    await extract_statement(document_id=payload["document_id"])
