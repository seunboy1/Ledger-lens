# Sample data for ingestion

Nine PDFs that exercise every path through ingestion: five bank layouts, layout learning and reuse, a multi-chunk statement, a statement held for review, and two files that must fail cleanly. All banks, people and figures are fictional.

| File | Layout | Pages | Rows | Expected | What it tests |
|---|---|---:|---:|---|---|
| `01-kestrel-salary-apr-sep-2026.pdf` | Debit / Credit columns, dd/mm/yyyy | 3 | 120 | reconciled | Salary on the 25th, subscriptions, loan repayments, betting, a returned-cheque fee |
| `02-harbour-savings-apr-sep-2026.pdf` | One signed Amount column, yyyy-mm-dd | 1 | 21 | reconciled | Debits as negative numbers with no DR/CR label |
| `03-oakline-business-jul-sep-2026.pdf` | Amount + DR/CR flag, dd-Mon-yyyy | 1 | 45 | reconciled | Flag column; the account goes overdrawn once |
| `04-palmgrove-current-jul-sep-2026.pdf` | Withdrawals / Lodgements, dd.mm.yyyy | 1 | 23 | reconciled | A new layout, learned on upload; Balance B/F and C/F rows |
| `05-crestline-household-oct25-sep26.pdf` | Money Out / Money In, dd Mon yyyy | 3 | 120 | reconciled | Another new layout, 12 months |
| `06-kestrel-joint-jul-sep-2026-misprint.pdf` | same as 01 | 1 | 26 | needs_review | Spec reused (no new induction); one misprinted amount (₦6,800.00 should be ₦7,300.00) is flagged |
| `07-oakline-business-oct24-sep26-large.pdf` | same as 03 | 73 | 3,840 | reconciled | Two 40-page chunks processed separately, gap-checked and merged; cached spec reused |
| `08-scanned-statement-no-text-layer.pdf` | image only | 3 | 0 | failed | No text layer; OCR is not enabled, so it fails with a clear reason |
| `09-not-a-statement-letter.pdf` | none | 1 | 0 | failed | No transaction table |

`manifest.json` has the expected outcome for each file: status, row count, opening and closing balances, total credits and debits, and the misprint details. `ground-truth/*.csv` lists every transaction exactly as printed (the answer key for checking extraction row by row).

## Use them

**In the app:** open Statements and drop any of the PDFs on the upload area.

**Through the API, checked against the manifest:**

```bash
pipelines/.venv/bin/python scripts/dev_api.py                    # API on :8000
pipelines/.venv/bin/python scripts/upload_samples.py             # uploads 04, 05, 07, 08, 09 (01, 02, 03, 06 are already in the demo seed)
pipelines/.venv/bin/python scripts/upload_samples.py 07          # one file, by prefix
```

To test against a clean, throwaway database instead of the demo one:

```bash
pipelines/.venv/bin/python scripts/dev_api.py --port 8010 --data-dir /tmp/ledgerlens-sandbox
LEDGER_LENS_API=http://localhost:8010 pipelines/.venv/bin/python scripts/upload_samples.py --all
```

Each line reports PASS or FAIL with the status, rows, chunk count and whether the layout spec was learned or reused. The script exits non-zero if anything differs from the manifest. The last full run matched 9 of 9.

## Regenerate

```bash
pipelines/.venv/bin/python scripts/make_samples.py
```

The output is deterministic: fixed seeds produce the same transactions every time. The generators live in `backend/app/dev/sample_statements.py`.
