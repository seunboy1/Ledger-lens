"""
Statements: upload, status, proof and human review.

Upload deliberately does almost nothing on the request path. It records a
document, hands back an upload target, and returns. Splitting, extraction,
spec induction, parsing and reconciliation all happen off-request, from the
ingest queue (docs/architecture.md §1).

Review endpoints never mark data as trusted by fiat: a corrected row is
re-proven by the same balance arithmetic as the pipeline
(services/statement_proof.py), and "accept" is only allowed once the
document's arithmetic holds.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db
from app.api.schemas import (
    ChunkProgress,
    DocumentDetail,
    DocumentStatusResponse,
    DocumentSummary,
    LayoutOut,
    ProofOut,
    ReviewDecision,
    RowCorrection,
    TxnOut,
    TxnPage,
    UploadRequest,
    UploadResponse,
)
from app.config import get_settings
from app.db.models import (
    ChunkStatus,
    Document,
    DocumentChunk,
    DocumentStatus,
    LayoutSpec,
    Transaction,
    TransactionType,
)
from app.services import storage
from app.services.queue import publish_ingest_job
from app.services.statement_proof import compute_proof, load_document_rows, reconcile_document

router = APIRouter(prefix="/documents", tags=["statements"])
transactions_router = APIRouter(prefix="/transactions", tags=["statements"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024


def _safe_filename(name: str) -> str:
    base = name.replace("\\", "/").split("/")[-1].strip() or "statement.pdf"
    cleaned = "".join(c if c.isalnum() or c in "-_. " else "_" for c in base)[:120]
    return cleaned if cleaned.lower().endswith(".pdf") else cleaned + ".pdf"


async def _get_document(db: AsyncSession, tenant_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    document = await db.get(Document, document_id)
    if document is None or document.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Statement not found")
    return document


def _txn_out(t: Transaction) -> TxnOut:
    return TxnOut(
        id=t.id,
        date=t.transaction_date,
        description=t.description,
        amount=float(t.amount),
        type=t.transaction_type.value,
        raw_label=t.raw_type_label,
        bank=t.bank_name,
        balance_after=float(t.balance_after) if t.balance_after is not None else None,
        expected_balance=float(t.expected_balance) if t.expected_balance is not None else None,
        reconciled=t.reconciled,
        repair_source=t.repair_source,
        page_number=t.page_number,
    )


async def _summaries(db: AsyncSession, tenant_id: uuid.UUID, ids: list[uuid.UUID] | None = None) -> list[DocumentSummary]:
    stats = (
        select(
            Transaction.document_id,
            func.count(Transaction.id).label("n"),
            func.min(Transaction.transaction_date).label("start"),
            func.max(Transaction.transaction_date).label("end"),
        )
        .where(Transaction.tenant_id == tenant_id)
        .group_by(Transaction.document_id)
        .subquery()
    )
    stmt = (
        select(Document, stats.c.n, stats.c.start, stats.c.end)
        .outerjoin(stats, stats.c.document_id == Document.id)
        .where(Document.tenant_id == tenant_id)
        .order_by(Document.created_at.desc())
    )
    if ids is not None:
        stmt = stmt.where(Document.id.in_(ids))
    out = []
    for doc, n, start, end in (await db.execute(stmt)).all():
        out.append(
            DocumentSummary(
                id=doc.id,
                filename=doc.original_filename,
                bank_name=doc.bank_name,
                status=doc.status.value,
                page_count=doc.page_count,
                reconciliation_score=float(doc.reconciliation_score) if doc.reconciliation_score is not None else None,
                transaction_count=int(n or 0),
                period_start=start,
                period_end=end,
                error=doc.error,
                created_at=doc.created_at or datetime.now(timezone.utc),
            )
        )
    return out


@router.get("", response_model=list[DocumentSummary])
async def list_documents(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[DocumentSummary]:
    return await _summaries(db, tenant_id)


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def create_upload(
    body: UploadRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> UploadResponse:
    storage.ensure_bucket()

    document_id = uuid.uuid4()
    filename = _safe_filename(body.filename)
    storage_path = f"{tenant_id}/{document_id}/{filename}"

    db.add(
        Document(
            id=document_id,
            tenant_id=tenant_id,
            storage_path=storage_path,
            original_filename=filename,
            status=DocumentStatus.uploaded,
        )
    )
    await db.commit()

    return UploadResponse(
        document_id=document_id, upload_url=storage.presigned_upload_url(storage_path), storage_path=storage_path
    )


@router.put("/upload-content/{object_path:path}", status_code=204)
async def upload_content(
    object_path: str,
    request: Request,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
) -> Response:
    """
    Local-profile stand-in for MinIO's pre-signed PUT. Only exists when
    storage is a local directory; in production the browser uploads straight
    to object storage and this route returns 404.
    """

    if get_settings().storage_backend != "local":
        raise HTTPException(status_code=404, detail="Not found")
    if not object_path.startswith(f"{tenant_id}/"):
        raise HTTPException(status_code=403, detail="Upload target belongs to another workspace")

    body = await request.body()
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Statements are limited to 25 MB")
    if not body.startswith(b"%PDF"):
        raise HTTPException(status_code=415, detail="Only PDF statements are supported")
    try:
        storage.put_object(object_path, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid upload path") from e
    return Response(status_code=204)


@router.post("/{document_id}/notify-uploaded", status_code=202)
async def notify_uploaded(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    """
    Called once the direct-to-storage upload finishes (or by a MinIO
    bucket-notification webhook in production). Enqueues the ingest job and
    returns immediately.
    """

    document = await _get_document(db, tenant_id, document_id)
    if not storage.object_exists(document.storage_path):
        raise HTTPException(status_code=409, detail="Upload has not completed")
    if document.status == DocumentStatus.processing:
        return {"status": "queued"}

    document.status = DocumentStatus.processing
    await db.commit()
    await publish_ingest_job(str(document_id), str(tenant_id), document.storage_path)
    return {"status": "queued"}


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> DocumentStatusResponse:
    document = await _get_document(db, tenant_id, document_id)
    return DocumentStatusResponse(
        document_id=document.id,
        status=document.status.value,
        reconciliation_score=float(document.reconciliation_score) if document.reconciliation_score is not None else None,
        page_count=document.page_count,
    )


@router.get("/{document_id}", response_model=DocumentDetail)
async def get_document(
    document_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> DocumentDetail:
    document = await _get_document(db, tenant_id, document_id)
    summary = (await _summaries(db, tenant_id, [document.id]))[0]

    rows = await load_document_rows(db, document.id)
    proof = compute_proof(document, rows, apply=False)
    failing_ids = set(proof.failing_ids)
    failing = [t for t in rows if str(t.id) in failing_ids or (t.repair_source == "ai" and not t.reviewed)]

    layout = None
    if document.layout_spec_id:
        spec = await db.get(LayoutSpec, document.layout_spec_id)
        if spec is not None:
            layout = LayoutOut(
                fingerprint=spec.fingerprint[:12],
                amount_convention=spec.spec.get("amount_convention"),
                date_format=spec.spec.get("date_format"),
                induced_by=spec.spec.get("induced_by", "llm"),
                times_reused=spec.times_reused,
                columns={k: v for k, v in spec.spec.get("columns", {}).items() if v is not None},
            )

    chunk_counts = dict(
        (
            await db.execute(
                select(DocumentChunk.status, func.count()).where(DocumentChunk.document_id == document.id).group_by(DocumentChunk.status)
            )
        ).all()
    )
    total_chunks = sum(chunk_counts.values())
    if document.page_count:
        per = get_settings().pages_per_chunk
        total_chunks = max(total_chunks, -(-document.page_count // per))

    return DocumentDetail(
        **summary.model_dump(),
        proof=ProofOut(
            opening=float(proof.opening) if proof.opening is not None else None,
            closing_printed=float(proof.closing_printed) if proof.closing_printed is not None else None,
            closing_computed=float(proof.closing_computed) if proof.closing_computed is not None else None,
            total_credits=float(proof.total_credits),
            total_debits=float(proof.total_debits),
            rows_total=proof.rows_total,
            rows_verified=proof.rows_verified,
            document_check_ok=proof.document_check_ok,
            pending_ai_repairs=proof.pending_ai_repairs,
        ),
        layout=layout,
        chunks=ChunkProgress(
            done=chunk_counts.get(ChunkStatus.done, 0), failed=chunk_counts.get(ChunkStatus.failed, 0), total=total_chunks
        ),
        failing_rows=[_txn_out(t) for t in failing],
    )


@router.get("/{document_id}/transactions", response_model=TxnPage)
async def document_transactions(
    document_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> TxnPage:
    document = await _get_document(db, tenant_id, document_id)
    total = (await db.execute(select(func.count()).where(Transaction.document_id == document.id))).scalar_one()
    rows = (
        await db.execute(
            select(Transaction)
            .where(Transaction.document_id == document.id)
            .order_by(Transaction.page_number, Transaction.row_index, Transaction.transaction_date)
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return TxnPage(total=total, items=[_txn_out(t) for t in rows])


@router.post("/{document_id}/review", response_model=DocumentDetail)
async def review_document(
    document_id: uuid.UUID,
    body: ReviewDecision,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> DocumentDetail:
    document = await _get_document(db, tenant_id, document_id)

    if body.action == "reject":
        document.status = DocumentStatus.failed
        document.error = "Rejected in review"
    else:
        rows = await load_document_rows(db, document.id)
        for t in rows:
            if t.repair_source == "ai":
                t.reviewed = True
        proof = compute_proof(document, rows, apply=True)
        if not (proof.rows_total and proof.rows_verified == proof.rows_total and proof.document_check_ok is not False):
            raise HTTPException(
                status_code=409,
                detail="The statement still does not reconcile. Correct the flagged rows before accepting.",
            )
        document.status = DocumentStatus.reconciled
        document.error = None
    document.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return await get_document(document_id, tenant_id, db)


@transactions_router.patch("/{transaction_id}", response_model=DocumentDetail)
async def correct_transaction(
    transaction_id: uuid.UUID,
    body: RowCorrection,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> DocumentDetail:
    txn = await db.get(Transaction, transaction_id)
    if txn is None or txn.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if body.amount is None and body.transaction_type is None:
        raise HTTPException(status_code=422, detail="Nothing to change")

    document = await _get_document(db, tenant_id, txn.document_id)
    if body.amount is not None:
        txn.amount = round(body.amount, 2)
    if body.transaction_type is not None:
        txn.transaction_type = TransactionType(body.transaction_type)
    txn.repair_source = "human"
    txn.reviewed = True

    if document.status == DocumentStatus.failed:
        document.status = DocumentStatus.needs_review
    await reconcile_document(db, document)
    if document.status == DocumentStatus.reconciled:
        document.reviewed_at = datetime.now(timezone.utc)
        document.error = None
    await db.commit()
    return await get_document(document.id, tenant_id, db)
