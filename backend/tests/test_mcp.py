"""MCP server tests: an in-process MCP client calls the real tools against the seeded workspace."""

import json
from decimal import Decimal

import pytest
import pytest_asyncio
from mcp import Client

from app.dev.sample_statements import demo_statements
from app.dev.seed import DEMO_TENANT_ID
from app.main import app
from app.mcp_server import build_server
from app.services.queue import drain_inline_jobs

pytestmark = pytest.mark.asyncio(loop_scope="module")


def payload(result):
    if getattr(result, "structured_content", None) is not None:
        data = result.structured_content
        return data.get("result", data) if isinstance(data, dict) and set(data) == {"result"} else data
    return json.loads(result.content[0].text)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def seeded():
    async with app.router.lifespan_context(app):
        await drain_inline_jobs()
        yield


async def call(name: str, args: dict | None = None):
    # A fresh in-process client per call: its task group must open and close in the same task.
    async with Client(build_server(DEMO_TENANT_ID)) as c:
        return payload(await c.call_tool(name, args or {}))


async def test_tools_are_listed_read_only(seeded):
    async with Client(build_server(DEMO_TENANT_ID)) as c:
        tools = {t.name: t for t in (await c.list_tools()).tools}
    assert {"ask", "list_statements", "statement_proof", "workspace_overview"} <= set(tools)
    assert all(t.annotations and t.annotations.read_only_hint for t in tools.values())


async def test_ask_returns_sql_figures_and_rows(seeded):
    verified = [s for s in demo_statements() if s.misprint is None]
    # Harbour Trust: no other test modifies it, so this holds in any test order.
    total = sum((l.amount for s in verified for l in s.lines if l.day.month == 7 and l.amount > 0 and s.bank.startswith("Harbour")), Decimal(0))
    data = await call("ask", {"question": "Total credits at Harbour in July 2026"})
    assert f"₦{total:,.2f}" in data["answer"]
    assert data["route"] == "sql" and data["rows"]
    assert all(r["bank"] == "Harbour Trust Bank" for r in data["rows"])


async def test_statements_and_proof(seeded):
    docs = await call("list_statements")
    assert {d["status"] for d in docs} >= {"reconciled"}
    proofs = await call("statement_proof", {"statement": "harbour"})
    assert proofs and proofs[0]["closing_matches"] is True


async def test_overview(seeded):
    data = await call("workspace_overview")
    assert data["salary"]["average_amount"] == "₦845,000.00"
    assert data["salary"]["usual_day_of_month"] == 25
