"""
Ledger Lens as an MCP server.

Lets any MCP client (Claude Desktop, Claude Code, an IDE agent) ask the
workspace questions and inspect statements and their balance proofs. All tools
are read-only and scoped to one workspace (settings.mcp_tenant_id). They run
the same SQL-backed operations as the app (app/services/ledger_tools.py), so
the numbers a client sees are the numbers the UI shows.

Run over stdio:
    pipelines/.venv/bin/python scripts/mcp_server.py
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from app.config import get_settings
from app.db.session import async_session_factory
from app.db.tenant import set_tenant_context
from app.services import ledger_tools as lt

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

INSTRUCTIONS = (
    "Ledger Lens reads bank statements from any bank, checks every row against the statement's own running "
    "balance, and answers questions with SQL over the rows that pass. Use `ask` for questions about money "
    "(totals, counts, balances, patterns); quote its figures exactly, they are computed by the database. "
    "Use `list_statements` and `statement_proof` to explain coverage or why a statement is held for review."
)


def build_server(tenant_id: uuid.UUID | None = None) -> MCPServer:
    tenant = tenant_id or uuid.UUID(get_settings().mcp_tenant_id)
    server = MCPServer("Ledger Lens", instructions=INSTRUCTIONS, version="0.2.0")

    @asynccontextmanager
    async def session():
        async with async_session_factory() as db:
            await set_tenant_context(db, tenant)
            yield db

    @server.tool(annotations=READ_ONLY)
    async def ask(question: str) -> dict:
        """Answer a question about the workspace's transactions, e.g. "total debits in August 2026" or
        "which payments look like subscriptions". Returns the answer, the figures, the filters applied and
        the evidence rows it was computed from. Only reconciled statements are counted."""
        async with session() as db:
            _, data = await lt.ask(db, tenant, question)
            return data

    @server.tool(annotations=READ_ONLY)
    async def list_statements() -> list[dict]:
        """List the workspace's bank statements: bank, status (reconciled, needs_review, processing, failed),
        row count, and whether it currently counts in answers."""
        async with session() as db:
            return await lt.list_statements(db, tenant)

    @server.tool(annotations=READ_ONLY)
    async def statement_proof(statement: str) -> list[dict]:
        """Balance proof for statements matching a bank name, filename or statement id: opening + credits −
        debits vs the printed closing balance, and any rows that fail the running-balance check."""
        async with session() as db:
            return await lt.statement_proof(db, tenant, statement)

    @server.tool(annotations=READ_ONLY)
    async def workspace_overview() -> dict:
        """Borrower overview: monthly money in and out, balances, detected salary, and risk signals
        (returned items, repayments to other lenders, betting)."""
        async with session() as db:
            return await lt.workspace_overview(db, tenant)

    return server
