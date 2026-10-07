"""
Shared FastAPI dependencies.

get_tenant_db is the important one: it yields a DB session that has
already had the caller's tenant_id set as the Postgres session variable
every RLS policy checks against (see app/db/tenant.py and
migrations/0001_initial_schema_and_rls.sql). Every route that touches
tenant data should depend on this, not on get_db directly.
"""

import uuid
from collections.abc import AsyncIterator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.db.tenant import set_tenant_context


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> uuid.UUID:
    """
    Placeholder auth: reads the tenant from a header. Replace with a real
    session/JWT lookup (NextAuth + Keycloak/Supabase Auth, per the
    architecture doc) before this leaves development — nothing here should
    be trusted as authorization in production.
    """

    if not x_tenant_id:
        raise HTTPException(status_code=401, detail="Missing X-Tenant-Id header")
    try:
        return uuid.UUID(x_tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid tenant id") from e


async def get_tenant_db(
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
) -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        await set_tenant_context(session, tenant_id)
        yield session
