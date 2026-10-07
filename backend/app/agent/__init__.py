"""
The Ask agent: a LangGraph tool-calling loop over Ledger Lens's SQL-backed
tools, with a grounding check before anything reaches the user.

`respond()` is the single entry point used by the chat API. It runs the agent
when enabled and falls back to the deterministic planner (same SQL, templated
prose) when the agent is off, errors, or fails the grounding check.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.answering import Answer, answer_question

log = logging.getLogger(__name__)


def agent_enabled() -> bool:
    s = get_settings()
    return s.agent_mode == "on" or (s.agent_mode == "auto" and bool(s.llm_provider_api_key))


async def respond(db: AsyncSession, tenant_id: uuid.UUID, question: str) -> Answer:
    if not agent_enabled():
        return await answer_question(db, tenant_id, question)
    try:
        from app.agent.graph import run_agent  # imported lazily: optional dependency

        return await run_agent(db, tenant_id, question)
    except Exception as e:  # noqa: BLE001 - any agent failure degrades to the deterministic answer
        log.warning("Agent failed (%s); using the deterministic answer", e)
        answer = await answer_question(db, tenant_id, question)
        answer.lineage.insert(0, {"title": "Agent unavailable", "detail": "Answered by the deterministic planner instead"})
        return answer
