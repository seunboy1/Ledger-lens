# Ledger Lens: launch video plan (brag-slim)

**What it is:** a tool that reads bank statements from any bank and answers plain-language questions about them, with the exact rows behind every answer.

**Who it's for:** credit analysts at lenders, who today read statements by hand or trust a chatbot's arithmetic.

**What sets it apart:** answers are computed by the database over rows that already passed a balance check, and every answer cites its rows. An AI model only ever learns a new statement layout; it never reads the statement or does the maths.

**Most impressive true claim:** a misprinted ₦6,800.00 is caught because the statement's own running balance says it should be ₦7,300.00, and the statement is held back until it's fixed.

**Visual hook:** the real Ask screen, a question typing itself, and ₦480,800.00 landing with the rows behind it. Product in use from frame 1.

**Tone:** `default` (punchy, clean), on the app's own palette: cool neutrals, one cobalt accent, Geist.

**Share caption:** "Ask your bank statements anything, and see the exact rows behind every answer."

## Storyboard (30 fps, 642 frames ≈ 21.4 s)

| # | Scene | Time | On screen | Real material used |
|---|---|---|---|---|
| 1 | Hook + reveal | 0.0–6.5s | "Ask your bank statements anything." A question types in, sends, and the answer lands: **₦480,800.00, 18 rows**. The evidence panel slides in. Caption becomes "Every answer shows its rows." | The app's real `MessageView` and `EvidencePanel` components, demo data |
| 2 | Any layout | 6.5–10.4s | "Any bank. Any layout." Three real statement PDFs (Kestrel, Harbour Trust, Oakline), each with one row highlighted, then the same rows as stored: one schema | Page renders of the demo PDFs; the app's evidence-row style |
| 3 | Learned once | 10.4–13.8s | "Learned once. Then plain code." Pipeline strip lights up; 212 rows parsed, 3 layouts learned | Pipeline stages from the architecture doc; demo counts |
| 4 | Proven | 13.8–18.4s | "Every number checked against the balance." Balance proof shows "Off by ₦500.00"; the row is corrected from ₦6,800.00 to ₦7,300.00; the status flips to Reconciled and the check says Matches | The app's real `BalanceProof` and `StatusBadge` |
| 5 | Outro | 18.4–21.4s | Ledger Lens: "Bank statements you can question. Answers you can check." Demo link in the post | Brand mark |

**Poster (frame 0):** scene 1 settled, with answer and evidence on screen.

**Sound:** one original piece at 96 BPM in D major (D, Bm, G, A). Soft pad, bass and a light arpeggio, with the effects tuned to the key and sent through the same reverb: typing ticks, a two-note pluck when the answer lands, soft whooshes on cuts, a low muted tone on "Off by", and a rising D-major chime on "Matches".

**Formats:** 4:5 (1080×1350) for LinkedIn, 9:16 (1080×1920) for Reels and Shorts.

---

# Phone promo (18 s, 9:16): `phone/brag.mp4`

Built from the user's promo template (phone centred on a vivid blue gradient, bold white captions, beats every 3–4 s) with brag-slim's rules applied: hook in the first 2 s, real UI, readable holds, sound written as one piece.

| Time | Beat | Caption | On the phone |
|---|---|---|---|
| 0–2 s | Phone glides in and settles; dashboard loads | – | Overview (sample workspace) |
| 2–6 s | Statements land as notifications; verified-row counter ticks 0 → 120 → 141 → 186; cashflow bars grow | EVERY STATEMENT. VERIFIED. | GTBank, Access Bank, Moniepoint MFB accounts flip to Reconciled |
| 6–9 s | Gentle zoom; dashboard scrolls to income and risk signals | EVERY ACCOUNT, AT A GLANCE. | Salary ₦845,000.00, day 25, 6 months; 1 returned item, 6 loan repayments, 13 betting debits |
| 9–13 s | Push to Ask; question types; answer counts up; rows slide in | ASK IT ANYTHING. | ₦480,800.00 over 18 transactions, with the rows |
| 13–16 s | Push to the review statement; the misprinted row is corrected | EVERY NUMBER, CHECKED. | "Off by ₦500.00" → corrected → Matches, Reconciled |
| 16–18 s | End on the reconciled statement; brand over it; fade out | Ledger Lens: Bank statements you can question. | Reconciled detail |

**Bank names:** the sample workspace's accounts are shown as GTBank, Access Bank and Moniepoint MFB for a Nigerian audience. They are labels on sample data, with no logos or bank-branded documents, and a "Sample data" tag on screen. All figures are the demo's real computed values.

**Sound:** subtle electronic bed at 112 BPM in D major. Notification chimes (each a step higher), soft UI whooshes on screen pushes, typing ticks, a chime on the answer, a low muted note on "Off by", a rising D-major chord on "Matches".
