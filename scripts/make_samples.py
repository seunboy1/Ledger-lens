"""
Generate the sample ingestion set in samples/statements/.

    pipelines/.venv/bin/python scripts/make_samples.py

Writes, for every statement:
  * the PDF, as a bank would issue it (fictional banks, people and figures);
  * ground-truth/<name>.csv: every transaction exactly as printed, the answer
    key for checking extraction;
and one manifest.json with what ingestion should conclude for each file
(status, row count, opening/closing balances, totals, notes).

Deterministic: the same seeds always produce byte-identical figures.
"""

from __future__ import annotations

import csv
import io
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "pipelines")]
os.environ.setdefault("LEDGER_LENS_PROFILE", "local")

from app.dev import sample_statements as ss  # noqa: E402

OUT = ROOT / "samples" / "statements"
TRUTH = OUT / "ground-truth"

LAYOUTS = {
    "kestrel": "Separate Debit and Credit columns, dd/mm/yyyy, Trans Date + Value Date",
    "harbour": "One signed Amount column (negative = debit), yyyy-mm-dd",
    "oakline": "Amount plus a DR/CR flag column, dd-Mon-yyyy",
    "palmgrove": "Withdrawals and Lodgements columns, dd.mm.yyyy, Balance B/F and C/F rows",
    "crestline": "Money Out and Money In columns, dd Mon yyyy",
}


def money(d: Decimal) -> str:
    return f"{d:.2f}"


def write_truth(statement: ss.Statement, name: str) -> None:
    TRUTH.mkdir(parents=True, exist_ok=True)
    balance = statement.opening
    with open(TRUTH / f"{name}.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "narration", "type", "amount_as_printed", "true_amount", "balance_after"])
        for i, line in enumerate(statement.lines):
            balance += line.amount
            printed = statement.misprint[1] if statement.misprint and statement.misprint[0] == i else line.amount
            w.writerow(
                [
                    line.day.isoformat(),
                    line.narration,
                    "credit" if line.amount > 0 else "debit",
                    money(abs(printed)),
                    money(abs(line.amount)),
                    money(balance),
                ]
            )


def entry(statement: ss.Statement, name: str, status: str, *, in_demo_seed: bool, notes: str) -> dict:
    credits = sum((l.amount for l in statement.lines if l.amount > 0), Decimal(0))
    debits = -sum((l.amount for l in statement.lines if l.amount < 0), Decimal(0))
    e = {
        "file": f"{name}.pdf",
        "bank": statement.bank,
        "layout": statement.layout,
        "layout_description": LAYOUTS[statement.layout],
        "account_name": statement.account_name,
        "period": [statement.start.isoformat(), statement.end.isoformat()],
        "rows": len(statement.lines),
        "opening_balance": money(statement.opening),
        "closing_balance": money(statement.closing),
        "total_credits": money(credits),
        "total_debits": money(debits),
        "expected_status": status,
        "in_demo_seed": in_demo_seed,
        "notes": notes,
    }
    if statement.misprint:
        i, printed = statement.misprint
        line = statement.lines[i]
        e["misprint"] = {
            "row": i + 1,
            "date": line.day.isoformat(),
            "narration": line.narration,
            "printed_amount": money(abs(printed)),
            "correct_amount": money(abs(line.amount)),
        }
    return e


def scanned_copy(pdf: bytes) -> bytes:
    """Rasterize every page into an image-only PDF, like a phone scan: no text layer."""

    import pymupdf

    src = pymupdf.open(stream=pdf, filetype="pdf")
    out = pymupdf.open()
    for page in src:
        pix = page.get_pixmap(dpi=110, colorspace=pymupdf.csGRAY)
        new = out.new_page(width=page.rect.width, height=page.rect.height)
        new.insert_image(new.rect, stream=pix.tobytes("png"))
    return out.tobytes(deflate=True)


def letter_pdf() -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Kestrel Bank Plc", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for line in [
        "Dear Customer,",
        "",
        "Thank you for banking with us. Your new debit card has been dispatched to your",
        "registered address and should arrive within five working days.",
        "",
        "Customer Experience Team",
    ]:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []

    plan = [
        ("01-kestrel-salary-apr-sep-2026", ss.kestrel_salary_account(), "reconciled", True,
         "Salary account. Regular salary on the 25th, subscriptions, loan repayments, betting, one returned-cheque fee."),
        ("02-harbour-savings-apr-sep-2026", ss.harbour_savings_account(), "reconciled", True,
         "Savings account with a signed Amount column: debits are negative numbers, no DR/CR label."),
        ("03-oakline-business-jul-sep-2026", ss.oakline_business_account(), "reconciled", True,
         "Business account with a DR/CR flag column. Goes overdrawn once (negative running balance)."),
        ("04-palmgrove-current-jul-sep-2026", ss.palmgrove_current_account(), "reconciled", False,
         "A layout the demo workspace has not seen: the spec is learned on upload."),
        ("05-crestline-household-oct25-sep26", ss.crestline_household_account(), "reconciled", False,
         "Another unseen layout (Money Out / Money In), 12 months, several pages."),
        ("06-kestrel-joint-jul-sep-2026-misprint", ss.kestrel_joint_account_with_misprint(), "needs_review", True,
         "Same layout as 01 (spec reused, no new induction). One amount is misprinted, so the statement is held for review until the row is corrected."),
        ("07-oakline-business-oct24-sep26-large", ss.large_business_account(), "reconciled", False,
         "Two years of daily settlements, ~100 pages: ingestion splits it into several 40-page chunks. Same layout as 03, so the cached spec is reused."),
    ]

    for name, statement, status, seeded, notes in plan:
        pdf = ss.render_pdf(statement)
        (OUT / f"{name}.pdf").write_bytes(pdf)
        write_truth(statement, name)
        e = entry(statement, name, status, in_demo_seed=seeded, notes=notes)
        import pymupdf

        e["pages"] = len(pymupdf.open(stream=pdf, filetype="pdf"))
        manifest.append(e)
        print(f"{name}.pdf  {e['pages']:>3} pages  {e['rows']:>5} rows  -> {status}")

    scanned = scanned_copy(ss.render_pdf(ss.kestrel_salary_account()))
    (OUT / "08-scanned-statement-no-text-layer.pdf").write_bytes(scanned)
    manifest.append(
        {
            "file": "08-scanned-statement-no-text-layer.pdf",
            "expected_status": "failed",
            "in_demo_seed": False,
            "notes": "Statement 01 rasterized into images, like a phone scan. There is no text layer and scanned-page OCR is not enabled, so ingestion fails with a clear reason instead of guessing.",
        }
    )
    (OUT / "09-not-a-statement-letter.pdf").write_bytes(letter_pdf())
    manifest.append(
        {
            "file": "09-not-a-statement-letter.pdf",
            "expected_status": "failed",
            "in_demo_seed": False,
            "notes": "A bank letter with no transaction table. Ingestion fails with 'No transaction table was found'.",
        }
    )
    print("08-scanned-statement-no-text-layer.pdf  -> failed")
    print("09-not-a-statement-letter.pdf           -> failed")

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nWrote {len(manifest)} files to {OUT.relative_to(ROOT)}/ (+ manifest.json, ground-truth/*.csv)")


if __name__ == "__main__":
    main()
