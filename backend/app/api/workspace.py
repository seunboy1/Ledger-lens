"""
Workspace-level reads: who am I, what's in here, and the borrower overview.

`/auth/demo-session` exists only while the dev seed is on (local profile).
It hands the browser the demo workspace's tenant id, which the dev-only
header auth in api/deps.py then accepts. Real deployments replace both with
NextAuth + Keycloak/Supabase Auth (docs/PRD.md, SEC-2).
"""

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_tenant_db
from app.api.schemas import as_utc
from app.config import get_settings
from app.db.models import Document, DocumentStatus, LayoutSpec, Tenant, Transaction
from app.db.session import async_session_factory
from app.dev.seed import DEMO_TENANT_ID
from app.services.analytics import overview

router = APIRouter(tags=["workspace"])


@router.get("/auth/demo-session")
async def demo_session() -> dict:
    if not get_settings().dev_seed:
        raise HTTPException(status_code=404, detail="Not found")
    async with async_session_factory() as db:
        tenant = await db.get(Tenant, DEMO_TENANT_ID)
    if tenant is None:
        raise HTTPException(status_code=503, detail="Demo workspace is still being created")
    return {"tenant_id": str(tenant.id), "workspace": tenant.name, "user": {"name": "Demo analyst", "role": "Credit analyst"}}


@router.get("/workspace")
async def workspace(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Workspace not found")

    doc_counts = dict(
        (await db.execute(select(Document.status, func.count()).where(Document.tenant_id == tenant_id).group_by(Document.status))).all()
    )
    verified = (
        select(Transaction.bank_name, func.count(Transaction.id), func.min(Transaction.transaction_date), func.max(Transaction.transaction_date))
        .join(Document, Document.id == Transaction.document_id)
        .where(Transaction.tenant_id == tenant_id, Transaction.reconciled.is_(True), Document.status == DocumentStatus.reconciled)
        .group_by(Transaction.bank_name)
    )
    banks = [
        {"name": b, "transactions": int(n), "from": as_utc(start), "to": as_utc(end)}
        for b, n, start, end in (await db.execute(verified)).all()
    ]
    layout_ids = select(Document.layout_spec_id).where(Document.tenant_id == tenant_id, Document.layout_spec_id.is_not(None))
    layouts = (await db.execute(select(func.count()).select_from(LayoutSpec).where(LayoutSpec.id.in_(layout_ids)))).scalar_one()

    return {
        "tenant": {"id": str(tenant.id), "name": tenant.name},
        "banks": sorted(banks, key=lambda b: b["name"]),
        "documents": {s.value: doc_counts.get(s, 0) for s in DocumentStatus},
        "verified_transactions": sum(b["transactions"] for b in banks),
        "layouts_learned": layouts,
        "currency": "NGN",
    }


def _numbers(value):
    """Money is computed as Decimal; JSON consumers get plain numbers."""

    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {k: _numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_numbers(v) for v in value]
    return value


@router.get("/analytics/overview")
async def analytics_overview(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_tenant_db),
) -> dict:
    return _numbers(await overview(db, tenant_id))
