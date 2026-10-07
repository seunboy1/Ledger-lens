"""
End-to-end API tests on the local profile.

Startup seeds the demo workspace, which pushes four synthetic PDF statements
through the real pipeline (extraction -> layout fingerprint -> spec
induction -> deterministic parse -> reconciliation). Every number the chat
returns is then checked against ground truth computed independently from
the statement generator, not against the system's own output.
"""

import re
import uuid
from decimal import Decimal

import httpx
import pytest
import pytest_asyncio

from app.dev.sample_statements import (
    Statement,
    demo_statements,
    kestrel_joint_account_with_misprint,
    render_pdf,
)
from app.dev.seed import DEMO_TENANT_ID
from app.main import app
from app.services.queue import drain_inline_jobs

pytestmark = pytest.mark.asyncio(loop_scope="module")

STATEMENTS = demo_statements()
VERIFIED = [s for s in STATEMENTS if s.misprint is None]
MISPRINTED = next(s for s in STATEMENTS if s.misprint is not None)


def ngn(text: str) -> list[Decimal]:
    return [Decimal(m.replace(",", "")) for m in re.findall(r"₦([\d,]+\.\d{2})", text)]


def month_total(statements: list[Statement], year: int, month: int, sign: int, bank: str | None = None) -> Decimal:
    return sum(
        (
            abs(line.amount)
            for s in statements
            if bank is None or s.bank.startswith(bank)
            for line in s.lines
            if line.day.year == year and line.day.month == month and (line.amount > 0) == (sign > 0)
        ),
        Decimal(0),
    )


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def client():
    async with app.router.lifespan_context(app):
        await drain_inline_jobs()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            c.headers["X-Tenant-Id"] = str(DEMO_TENANT_ID)
            yield c


async def ask(client: httpx.AsyncClient, question: str) -> dict:
    conv = (await client.post("/conversations", json={})).json()
    r = await client.post(f"/conversations/{conv['id']}/messages", json={"content": question})
    assert r.status_code == 200, r.text
    return r.json()["assistant_message"]


async def test_health_and_auth(client):
    assert (await client.get("/health")).json()["status"] == "ok"
    r = await client.get("/documents", headers={"X-Tenant-Id": ""})
    assert r.status_code == 401
    r = await client.get("/documents", headers={"X-Tenant-Id": "not-a-uuid"})
    assert r.status_code == 400


async def test_demo_session(client):
    body = (await client.get("/auth/demo-session")).json()
    assert body["tenant_id"] == str(DEMO_TENANT_ID)
    assert body["workspace"] == "Meridian Capital"


async def test_seeded_statements_went_through_the_pipeline(client):
    docs = (await client.get("/documents")).json()
    assert len(docs) == 4
    by_name = {d["filename"]: d for d in docs}
    for s in VERIFIED:
        d = by_name[s.filename]
        assert d["status"] == "reconciled", d
        assert d["transaction_count"] == len(s.lines)
        assert d["reconciliation_score"] == 1.0
    bad = by_name[MISPRINTED.filename]
    assert bad["status"] == "needs_review"

    ws = (await client.get("/workspace")).json()
    # Three distinct layouts; the joint Kestrel statement reused the cached spec.
    assert ws["layouts_learned"] == 3
    assert {b["name"] for b in ws["banks"]} == {"Kestrel Bank", "Harbour Trust Bank", "Oakline Microfinance Bank"}
    assert ws["documents"]["needs_review"] == 1


async def test_document_proof_matches_printed_balances(client):
    docs = (await client.get("/documents")).json()
    kestrel = next(d for d in docs if d["filename"] == VERIFIED[0].filename)
    detail = (await client.get(f"/documents/{kestrel['id']}")).json()
    s = VERIFIED[0]
    assert Decimal(str(detail["proof"]["opening"])) == s.opening
    assert Decimal(str(detail["proof"]["closing_printed"])) == s.closing
    assert Decimal(str(detail["proof"]["closing_computed"])).quantize(Decimal("0.01")) == s.closing
    assert detail["proof"]["document_check_ok"] is True
    assert detail["layout"]["amount_convention"] == "separate_debit_credit_columns"
    assert detail["layout"]["induced_by"] == "heuristic"
    assert detail["layout"]["times_reused"] >= 1
    assert detail["failing_rows"] == []


async def test_total_debits_for_a_month_are_exact(client):
    msg = await ask(client, "What were my total debits in August 2026?")
    assert msg["route_kind"] == "sql"
    expected = month_total(VERIFIED, 2026, 8, -1)
    assert ngn(msg["content"])[0] == expected
    assert "awaiting review" in msg["content"]  # coverage note: the misprinted statement is excluded
    assert msg["evidence"]["total_rows"] == sum(
        1 for s in VERIFIED for l in s.lines if l.day.year == 2026 and l.day.month == 8 and l.amount < 0
    )
    assert msg["evidence"]["rows"], "answer must cite rows"
    assert all(r["type"] == "debit" for r in msg["evidence"]["rows"])


async def test_net_question_reports_both_sides(client):
    msg = await ask(client, "What was my net cashflow in July 2026?")
    credits = month_total(VERIFIED, 2026, 7, +1)
    debits = month_total(VERIFIED, 2026, 7, -1)
    values = ngn(msg["content"])
    assert values[0] == credits and values[1] == debits and values[2] == abs(credits - debits)


async def test_bank_filter(client):
    msg = await ask(client, "Total credits at Oakline in September 2026")
    assert ngn(msg["content"])[0] == month_total(VERIFIED, 2026, 9, +1, bank="Oakline")
    assert {r["bank"] for r in msg["evidence"]["rows"]} == {"Oakline Microfinance Bank"}


async def test_largest_debits(client):
    msg = await ask(client, "Show my top 3 largest debits")
    amounts = sorted((abs(l.amount) for s in VERIFIED for l in s.lines if l.amount < 0), reverse=True)[:3]
    assert len(msg["evidence"]["rows"]) == 3
    assert ngn(msg["content"])[:2] == [amounts[0], amounts[2]]


async def test_balance_at_period_end(client):
    msg = await ask(client, "What was my balance at the end of September 2026?")
    expected_closing = sum((s.closing for s in VERIFIED if s.end.month == 9), Decimal(0))
    assert ngn(msg["content"])[0] == expected_closing


async def test_semantic_subscriptions(client):
    msg = await ask(client, "Which of my payments look like subscriptions?")
    assert msg["route_kind"] == "semantic"
    narrations = {r["description"] for r in msg["evidence"]["rows"]}
    assert {"STREAMFLIX NG SUBSCRIPTION", "GYMHOUSE MONTHLY MEMBERSHIP", "FIBRELINK HOME INTERNET"} <= narrations


async def test_no_match_is_honest(client):
    msg = await ask(client, "Total debits in January 2025")
    assert msg["content"].startswith("No verified debits matched")
    assert msg["evidence"]["rows"] == []


async def test_analytics_overview(client):
    data = (await client.get("/analytics/overview")).json()
    assert [m["month"] for m in data["months"]] == ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
    aug = next(m for m in data["months"] if m["month"] == "2026-08")
    assert Decimal(str(aug["outflow"])).quantize(Decimal("0.01")) == month_total(VERIFIED, 2026, 8, -1)
    assert data["salary"]["detected"] is True
    assert data["salary"]["typical_day"] == 25
    assert isinstance(data["kpis"]["avg_monthly_inflow"], float)  # numbers, not strings
    assert data["salary"]["months"] == 6
    assert data["signals"]["returned_items"]["count"] == 1
    assert data["signals"]["other_lender_repayments"]["count"] == 6
    assert data["signals"]["betting"]["count"] >= 6


async def test_review_flow_fixes_the_misprinted_row(client):
    docs = (await client.get("/documents")).json()
    doc = next(d for d in docs if d["filename"] == MISPRINTED.filename)
    detail = (await client.get(f"/documents/{doc['id']}")).json()
    assert detail["proof"]["document_check_ok"] is False
    assert len(detail["failing_rows"]) == 1
    row = detail["failing_rows"][0]

    index, printed = MISPRINTED.misprint
    true_amount = abs(MISPRINTED.lines[index].amount)
    assert Decimal(str(row["amount"])) == abs(printed)

    # Accepting before the arithmetic holds is refused.
    r = await client.post(f"/documents/{doc['id']}/review", json={"action": "accept"})
    assert r.status_code == 409

    r = await client.patch(f"/transactions/{row['id']}", json={"amount": float(true_amount)})
    assert r.status_code == 200, r.text
    fixed = r.json()
    assert fixed["status"] == "reconciled"
    assert fixed["proof"]["document_check_ok"] is True
    assert fixed["failing_rows"] == []

    # The corrected statement now counts towards answers.
    msg = await ask(client, "What were my total debits in August 2026?")
    assert ngn(msg["content"])[0] == month_total(STATEMENTS, 2026, 8, -1)
    assert "awaiting review" not in msg["content"]


async def test_upload_flow_and_layout_cache_reuse(client):
    statement = kestrel_joint_account_with_misprint(seed=99)
    statement.misprint = None
    statement.filename = "fresh-upload.pdf"

    r = await client.post("/documents/upload", json={"filename": "../../fresh upload.pdf"})
    assert r.status_code == 201
    up = r.json()
    assert ".." not in up["storage_path"]
    put_path = up["upload_url"].split("/documents/upload-content/", 1)[1]

    r = await client.put(f"/documents/upload-content/{put_path}", content=b"not a pdf")
    assert r.status_code == 415
    r = await client.put(f"/documents/upload-content/{uuid.uuid4()}/x/y.pdf", content=b"%PDF-1.4")
    assert r.status_code == 403

    r = await client.post(f"/documents/{up['document_id']}/notify-uploaded")
    assert r.status_code == 409  # nothing uploaded yet

    r = await client.put(f"/documents/upload-content/{put_path}", content=render_pdf(statement))
    assert r.status_code == 204
    r = await client.post(f"/documents/{up['document_id']}/notify-uploaded")
    assert r.status_code == 202
    await drain_inline_jobs()

    detail = (await client.get(f"/documents/{up['document_id']}")).json()
    assert detail["status"] == "reconciled"
    assert detail["bank_name"] == "Kestrel Bank"
    assert detail["transaction_count"] == len(statement.lines)
    assert detail["layout"]["times_reused"] >= 2  # no new induction for a known layout
    assert (await client.get("/workspace")).json()["layouts_learned"] == 3


async def test_conversation_crud_and_feedback(client):
    conv = (await client.post("/conversations", json={})).json()
    sent = (await client.post(f"/conversations/{conv['id']}/messages", json={"content": "How many credits in June 2026?"})).json()
    assert sent["conversation"]["title"].startswith("How many credits in June 2026")
    reply = sent["assistant_message"]
    expected = sum(1 for s in STATEMENTS for l in s.lines if l.day.year == 2026 and l.day.month == 6 and l.amount > 0)
    assert f"{expected:,} verified credits" in reply["content"]

    msgs = (await client.get(f"/conversations/{conv['id']}/messages")).json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]

    r = await client.post(f"/conversations/{conv['id']}/messages/{reply['id']}/feedback", json={"helpful": False})
    assert r.json()["is_helpful"] is False

    r = await client.patch(f"/conversations/{conv['id']}", json={"title": "June credits"})
    assert r.json()["title"] == "June credits"
    assert (await client.delete(f"/conversations/{conv['id']}")).status_code == 204
    assert (await client.get(f"/conversations/{conv['id']}/messages")).status_code == 404


async def test_tenant_isolation(client):
    from app.db.models import Tenant
    from app.db.session import async_session_factory

    other = uuid.uuid4()
    async with async_session_factory() as db:
        db.add(Tenant(id=other, name="Another lender"))
        await db.commit()

    mine = (await client.get("/documents")).json()
    conv = (await client.post("/conversations", json={})).json()
    headers = {"X-Tenant-Id": str(other)}

    assert (await client.get("/documents", headers=headers)).json() == []
    assert (await client.get(f"/documents/{mine[0]['id']}", headers=headers)).status_code == 404
    assert (await client.get(f"/conversations/{conv['id']}/messages", headers=headers)).status_code == 404
    assert (await client.get("/conversations", headers=headers)).json() == []
    other_conv = (await client.post("/conversations", json={}, headers=headers)).json()
    r = await client.post(f"/conversations/{other_conv['id']}/messages", json={"content": "total debits"}, headers=headers)
    assert r.json()["assistant_message"]["evidence"]["rows"] == []
    assert (await client.get("/analytics/overview", headers=headers)).json()["months"] == []


async def test_pdf_without_a_table_fails_with_a_clear_reason(client):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, "Thank you for banking with us.")
    up = (await client.post("/documents/upload", json={"filename": "letter.pdf"})).json()
    path = up["upload_url"].split("/documents/upload-content/", 1)[1]
    await client.put(f"/documents/upload-content/{path}", content=bytes(pdf.output()))
    await client.post(f"/documents/{up['document_id']}/notify-uploaded")
    await drain_inline_jobs()

    detail = (await client.get(f"/documents/{up['document_id']}")).json()
    assert detail["status"] == "failed"
    assert "No transaction table was found" in detail["error"]
