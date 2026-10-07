"""
LangChain tools for the agent, bound to one tenant-scoped session per request.

Each tool returns (content, artifact): the content is what the model reads
(figures verbatim from SQL), the artifact carries structured results (the
deterministic Answer, row ids) that the graph uses for KPIs and evidence, so
those never pass through the model's text.
"""

from __future__ import annotations

import uuid

from langchain_core.tools import BaseTool, StructuredTool
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import ledger_tools as lt


def build_tools(db: AsyncSession, tenant_id: uuid.UUID) -> list[BaseTool]:
    async def query_transactions(question: str):
        answer, data = await lt.ask(db, tenant_id, question)
        rows = data.pop("rows")
        text = lt.as_text(data)
        if rows:
            text += "\nrows (first 8 of the evidence):\n" + "\n".join(
                f"  {r['date']} | {r['description']} | {r['type']} {r['amount']} | {r['bank']}" for r in rows[:8]
            )
        return text, {"answer": answer}

    async def list_statements():
        docs = await lt.list_statements(db, tenant_id)
        return lt.as_text(docs), {"statements": docs}

    async def statement_proof(statement: str):
        proofs = await lt.statement_proof(db, tenant_id, statement)
        return (lt.as_text(proofs) if proofs else f"No statement matches {statement!r}."), {"proofs": proofs}

    async def workspace_overview():
        data = await lt.workspace_overview(db, tenant_id)
        return lt.as_text(data), {"overview": data}

    specs = [
        (
            query_transactions,
            "Answer a question about transactions (totals, counts, averages, largest/smallest, balances, "
            "or patterns like subscriptions, loan repayments, betting). Pass the user's question, rephrased "
            "if needed. Returns the computed figures, the filters applied and the evidence rows. Only rows "
            "from reconciled statements are counted.",
        ),
        (list_statements, "List the workspace's bank statements with their status and whether they count in answers."),
        (
            statement_proof,
            "Balance proof for a statement: opening + credits - debits vs the printed closing balance, and any "
            "rows that do not reconcile. Pass a bank name, filename or statement id.",
        ),
        (
            workspace_overview,
            "Borrower overview: monthly money in and out, balances, detected salary and risk signals "
            "(returned items, other-lender repayments, betting).",
        ),
    ]
    return [
        StructuredTool.from_function(coroutine=fn, name=fn.__name__, description=desc, response_format="content_and_artifact")
        for fn, desc in specs
    ]
