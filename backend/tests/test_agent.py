"""
LangGraph agent tests with a scripted chat model (no network).

They check the agent's contract, not a model's quality: it calls the SQL
tools, its reply is used only when every figure is grounded in a tool result,
and KPIs and evidence always come from the tools.
"""

import re
import uuid
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.agent import graph as agent_graph
from app.agent.graph import build_graph, check_grounding, run_agent
from app.agent.tools import build_tools
from app.db.session import async_session_factory
from app.dev.sample_statements import demo_statements
from app.dev.seed import DEMO_TENANT_ID
from app.main import app
from app.services.queue import drain_inline_jobs

pytestmark = pytest.mark.asyncio(loop_scope="module")
VERIFIED = [s for s in demo_statements() if s.misprint is None]
AUG_DEBITS = sum((abs(l.amount) for s in VERIFIED for l in s.lines if l.day.year == 2026 and l.day.month == 8 and l.amount < 0), Decimal(0))


class ScriptedModel(GenericFakeChatModel):
    """Replays a fixed list of AIMessages; tool binding is a no-op."""

    def bind_tools(self, tools, **kwargs):
        return self


def script(*messages):
    return ScriptedModel(messages=iter(list(messages)))


def call(name, **args):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}", "type": "tool_call"}])


def naira(d: Decimal) -> str:
    return f"₦{d:,.2f}"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def db():
    async with app.router.lifespan_context(app):
        await drain_inline_jobs()
        async with async_session_factory() as session:
            yield session


async def test_grounding_check():
    tools = ["Total debits came to ₦1,251,582.94 over 25 transactions."]
    assert check_grounding("Debits were ₦1,251,582.94 across 25 rows in August 2026.", tools, "debits in August 2026")["grounded"]
    bad = check_grounding("Debits were ₦1,300,000.00.", tools, "debits in August")
    assert not bad["grounded"] and bad["ungrounded"] == ["1300000.00"]


async def test_graph_shape():
    g = build_graph([], script(AIMessage(content="x")))
    assert {"agent", "tools", "verify"} <= set(g.get_graph().nodes)


async def test_agent_uses_tools_and_grounded_reply(db):
    q = "How much did I spend in August 2026?"
    model = script(
        call("query_transactions", question="total debits in August 2026"),
        AIMessage(content=f"You spent {naira(AUG_DEBITS)} in August 2026 across 3 banks, from 25 debit transactions."),
    )
    answer = await run_agent(db, DEMO_TENANT_ID, q, model=model)
    assert answer.engine == "agent"
    assert naira(AUG_DEBITS) in answer.content
    assert answer.evidence_ids, "evidence must come from the SQL tool"
    assert any(k.value == naira(AUG_DEBITS) for k in answer.kpis)
    titles = [s["title"] for s in answer.lineage]
    assert titles[0] == "Agent (LangGraph)" and titles[-1] == "Grounding check"
    assert "query_transactions" in answer.lineage[0]["detail"]


async def test_hallucinated_figure_is_rejected(db):
    q = "How much did I spend in August 2026?"
    model = script(
        call("query_transactions", question=q),
        AIMessage(content="You spent about ₦1,300,000.00 in August."),
    )
    answer = await run_agent(db, DEMO_TENANT_ID, q, model=model)
    assert answer.engine == "deterministic"
    assert "1,300,000" not in answer.content
    assert re.search(re.escape(naira(AUG_DEBITS)), answer.content)
    assert "rejected" in answer.lineage[-1]["detail"]


async def test_answer_without_tools_is_rejected(db):
    model = script(AIMessage(content="Probably around ₦500,000.00."))
    answer = await run_agent(db, DEMO_TENANT_ID, "How much did I spend in August 2026?", model=model)
    assert answer.engine == "deterministic"
    assert "without calling a data tool" in answer.lineage[-1]["detail"]


async def test_multi_tool_statement_question(db):
    model = script(
        call("list_statements"),
        call("statement_proof", statement="joint"),
        AIMessage(content="The Kestrel Bank joint statement is held for review: 25 of 26 rows reconcile."),
    )
    answer = await run_agent(db, DEMO_TENANT_ID, "Why is a statement held back?", model=model)
    assert answer.engine == "agent"
    assert answer.kpis == [] and answer.evidence_ids == []
    assert "statement_proof(statement='joint')" in answer.lineage[0]["detail"]


async def test_tools_return_sql_figures(db):
    tools = {t.name: t for t in build_tools(db, DEMO_TENANT_ID)}
    out = await tools["query_transactions"].ainvoke({"question": "total debits in August 2026"})
    assert naira(AUG_DEBITS) in out
    overview = await tools["workspace_overview"].ainvoke({})
    assert "₦845,000.00" in overview  # detected salary


async def test_chat_api_runs_the_agent(db, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "agent_mode", "on")
    reply = f"Total August 2026 debits were {naira(AUG_DEBITS)}."
    monkeypatch.setattr(
        agent_graph.llm_module,
        "get_chat_model",
        lambda: script(call("query_transactions", question="total debits in August 2026"), AIMessage(content=reply)),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as c:
        c.headers["X-Tenant-Id"] = str(DEMO_TENANT_ID)
        conv = (await c.post("/conversations", json={})).json()
        msg = (await c.post(f"/conversations/{conv['id']}/messages", json={"content": "August 2026 debits?"})).json()["assistant_message"]
    assert msg["engine"] == "agent"
    assert msg["content"] == reply
    assert msg["evidence"]["rows"]
    assert msg["evidence"]["lineage"][0]["title"] == "Agent (LangGraph)"


async def test_agent_failure_falls_back(db, monkeypatch):
    from app.agent import respond
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "agent_mode", "on")

    def broken():
        raise RuntimeError("provider down")

    monkeypatch.setattr(agent_graph.llm_module, "get_chat_model", broken)
    answer = await respond(db, DEMO_TENANT_ID, "total debits in August 2026")
    assert answer.engine == "deterministic"
    assert answer.lineage[0]["title"] == "Agent unavailable"
