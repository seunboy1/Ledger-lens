"""
Sets the Postgres session variable that every RLS policy checks against.

This is called once per request (see api/deps.py) — after this runs, every
query on this connection is transparently filtered to the caller's tenant
by the database itself, not by application-level WHERE clauses.

On SQLite (local profile) there is no RLS; isolation there relies on the
explicit tenant filters every query in this codebase also carries. Those
filters are belt-and-braces in production and the only belt in dev — which
is exactly why the local profile is never a deployment target.
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings


async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    if not get_settings().is_postgres:
        return
    await session.execute(text("SELECT set_config('app.current_tenant_id', :tenant_id, false)"), {"tenant_id": str(tenant_id)})
