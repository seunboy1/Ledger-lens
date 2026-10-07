"""
Demo workspace seed (local profile only).

Creates a fictional lender workspace and pushes four synthetic statements
through the real ingestion path: stored as PDFs, enqueued, then extracted,
induced, parsed and reconciled by the pipeline exactly as an upload would
be. One statement carries a misprinted amount so the review queue has
something real in it.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select

from app.db.models import Document, DocumentStatus, Tenant
from app.db.session import async_session_factory
from app.services import storage
from app.services.queue import publish_ingest_job

log = logging.getLogger(__name__)

DEMO_TENANT_ID = uuid.UUID("6f1c2a52-8d0e-4c1b-9a51-3e7d2c9b0a11")
DEMO_TENANT_NAME = "Meridian Capital"


async def ensure_demo_workspace() -> None:
    from app.dev.sample_statements import demo_statements, render_pdf

    async with async_session_factory() as db:
        if await db.get(Tenant, DEMO_TENANT_ID) is None:
            db.add(Tenant(id=DEMO_TENANT_ID, name=DEMO_TENANT_NAME))
            await db.commit()

        existing = (await db.execute(select(func.count()).where(Document.tenant_id == DEMO_TENANT_ID))).scalar_one()
        if existing:
            return

        storage.ensure_bucket()
        queued: list[Document] = []
        for statement in demo_statements():
            document_id = uuid.uuid4()
            path = f"{DEMO_TENANT_ID}/{document_id}/{statement.filename}"
            storage.put_object(path, render_pdf(statement))
            document = Document(
                id=document_id,
                tenant_id=DEMO_TENANT_ID,
                storage_path=path,
                original_filename=statement.filename,
                status=DocumentStatus.processing,
            )
            db.add(document)
            queued.append(document)
        await db.commit()

    for document in queued:
        await publish_ingest_job(str(document.id), str(DEMO_TENANT_ID), document.storage_path)
    log.info("Demo workspace seeded with %s statements", len(queued))
