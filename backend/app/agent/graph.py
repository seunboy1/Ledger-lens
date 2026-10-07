"""
LangGraph agent for Ask.

    START → agent ──(tool calls)──▶ tools ──▶ agent ──(final reply)──▶ verify → END

* agent:  the chat model with Ledger Lens's tools bound. It decides which tools
          to call and phrases the reply, and is told never to compute figures.
* tools:  LangGraph's ToolNode running the SQL-backed tools (app/agent/tools.py).
* verify: the grounding check. Every number in the reply must appear in a tool
          result (or in the question). A reply that invents or recomputes a
          figure, or that answers without calling a data tool, is discarded and
          the deterministic SQL answer is returned instead.

KPIs and evidence rows are taken from the tools' structured artifacts, never
parsed from the model's text.
"""

from __future__ import annotations

import re
import uuid
from decimal import Decimal, InvalidOperation
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import llm as llm_module
from app.agent.tools import build_tools
from app.services.answering import Answer, answer_question

SYSTEM = """You are Ledger Lens, an assistant for credit analysts reviewing bank statements.

Rules:
- Always call a tool to get data before answering. Never answer from memory.
- Never calculate, round, convert or estimate a number. Copy figures exactly as the tools give them, including ₦ and decimals.
- State the period and the banks the answer covers, and say if statements are excluded because they are still in review.
- Reply in one to three short sentences. No preamble, no markdown."""

DATA_TOOLS = {"query_transactions", "statement_proof", "workspace_overview", "list_statements"}
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
MAX_STEPS = 8


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    question: str
    verdict: dict


def numbers_in(text: str) -> set[Decimal]:
    out = set()
    for raw in NUMBER.findall(text):
        try:
            out.add(Decimal(raw.replace(",", "")))
        except InvalidOperation:
            continue
    return out


def check_grounding(reply: str, tool_texts: list[str], question: str) -> dict:
    allowed = numbers_in(question)
    for t in tool_texts:
        allowed |= numbers_in(t)
    used = numbers_in(reply)
    ungrounded = sorted(str(n) for n in used - allowed)
    return {"grounded": not ungrounded, "figures": len(used), "ungrounded": ungrounded}


def build_graph(tools, model):
    bound = model.bind_tools(tools)

    async def agent(state: AgentState):
        response = await bound.ainvoke([SystemMessage(SYSTEM), *state["messages"]])
        return {"messages": [response]}

    async def verify(state: AgentState):
        msgs = state["messages"]
        reply = msgs[-1].content if isinstance(msgs[-1], AIMessage) else ""
        tool_msgs = [m for m in msgs if isinstance(m, ToolMessage)]
        verdict = check_grounding(str(reply), [str(m.content) for m in tool_msgs], state["question"])
        verdict["used_tools"] = [m.name for m in tool_msgs]
        if not any(m.name in DATA_TOOLS for m in tool_msgs):
            verdict["grounded"] = False
            verdict["reason"] = "answered without calling a data tool"
        elif not str(reply).strip():
            verdict["grounded"] = False
            verdict["reason"] = "empty reply"
        elif verdict["ungrounded"]:
            verdict["reason"] = "figures not found in any tool result: " + ", ".join(verdict["ungrounded"])
        return {"verdict": verdict}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_node("verify", verify)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: "verify"})
    graph.add_edge("tools", "agent")
    graph.add_edge("verify", END)
    return graph.compile()


async def run_agent(db: AsyncSession, tenant_id: uuid.UUID, question: str, model=None) -> Answer:
    tools = build_tools(db, tenant_id)
    app = build_graph(tools, model or llm_module.get_chat_model())
    state = await app.ainvoke(
        {"messages": [HumanMessage(question)], "question": question, "verdict": {}},
        config={"recursion_limit": MAX_STEPS * 2 + 2},
    )

    msgs = state["messages"]
    verdict = state["verdict"]
    tool_msgs = [m for m in msgs if isinstance(m, ToolMessage)]
    calls = [f"{c['name']}({', '.join(f'{k}={v!r}' for k, v in c['args'].items())})" for m in msgs if isinstance(m, AIMessage) for c in m.tool_calls]
    primary = next(
        (m.artifact["answer"] for m in reversed(tool_msgs) if m.name == "query_transactions" and isinstance(m.artifact, dict)),
        None,
    )

    if verdict.get("grounded"):
        answer = primary or await answer_question(db, tenant_id, question)
        if primary is None:
            # Non-transaction question (e.g. a statement proof): no KPIs or rows to show.
            answer.kpis, answer.evidence_ids, answer.focused_ids, answer.matched_rows = [], [], [], 0
            answer.summary_title, answer.summary_subtitle, answer.source_summary = "Agent answer", "From statement tools", None
        answer.content = str(msgs[-1].content).strip()
        answer.engine = "agent"
        check = f"All {verdict['figures']} figures in the reply appear in tool results" if verdict["figures"] else "Reply contains no figures"
    else:
        answer = await answer_question(db, tenant_id, question)
        check = f"Reply rejected ({verdict.get('reason', 'ungrounded')}); the computed answer is shown instead"

    answer.lineage = [
        {"title": "Agent (LangGraph)", "detail": "Tool calls: " + ("; ".join(calls) if calls else "none")},
        *answer.lineage,
        {"title": "Grounding check", "detail": check},
    ]
    return answer
