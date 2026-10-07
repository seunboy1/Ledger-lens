import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { StatusBadge } from "@/components/StatusBadge";
import { BalanceProof } from "@/components/statements/BalanceProof";
import type { DocumentDetail } from "@/types/api";
import doc from "../data/review-statement.json";
import tl from "../timeline.json";
import { AppScale, Caption, Stage, naira, useEnter, useLayout, useSceneFade } from "../kit";

const [S0, S1] = tl.scenes.proof;
const t = tl.proof;
const before = doc.proof as DocumentDetail["proof"];
const row = doc.failing_rows[0];
// What the printed running balance says the amount must be.
const previous = (row.expected_balance as number) + row.amount; // debit: expected = previous - amount
const implied = Math.abs((row.balance_after as number) - previous);
const delta = implied - row.amount;

export function Proof() {
  const frame = useCurrentFrame();
  const { tall, captionTop, captionSize, contentTop, scale } = useLayout();
  const opacity = useSceneFade(S1 - S0, 10);
  const fix = interpolate(frame, [t.fix, t.fix + 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const matched = frame >= t.match;
  const debits = before.total_debits + delta * fix;
  const proof: DocumentDetail["proof"] = {
    ...before,
    total_debits: debits,
    closing_computed: (before.opening ?? 0) + before.total_credits - debits,
    rows_verified: matched ? before.rows_total : before.rows_verified,
    document_check_ok: matched,
  };
  const card = useEnter(4);
  const rowIn = useEnter(t.off + 10);
  const shake = !matched && frame > t.off + 24 && frame < t.fix - 6 ? Math.sin(frame * 1.7) * 3 : 0;

  return (
    <Stage opacity={opacity}>
      <Caption text="Every number checked against the balance." top={captionTop} size={captionSize} accentWords={["checked"]} />

      <AppScale scale={scale} width={500} style={{ left: tall ? 65 : 92, top: contentTop + (tall ? 60 : 40), opacity: card, transform: `translateY(${(1 - card) * 24}px)` }}>
        <div className="rounded-[16px] bg-bg p-4 shadow-[0_30px_80px_rgba(0,0,0,0.45)]">
          <div className="mb-3 flex items-start justify-between gap-3 px-1">
            <div>
              <p className="text-[17px] font-semibold tracking-tight">{doc.bank_name}</p>
              <p className="text-[12.5px] text-ink-soft">{doc.filename}</p>
            </div>
            <StatusBadge status={matched ? "reconciled" : "needs_review"} className="text-[13px]" />
          </div>
          <BalanceProof proof={proof} />
          <div
            className={`mt-3 rounded-[var(--radius-panel)] border-2 bg-surface px-4 py-3 ${matched ? "border-credit" : "border-error"}`}
            style={{ opacity: rowIn, transform: `translateX(${shake}px)` }}
          >
            <p className="text-[13.5px] font-medium">{row.description}</p>
            <p className="num text-[12px] text-muted">05 Aug 2026, page {row.page_number}</p>
            <div className="mt-2 grid grid-cols-3 gap-3 text-[12.5px]">
              <div>
                <p className="text-muted">{fix > 0.5 ? "Corrected amount" : "Extracted amount"}</p>
                <p className={`num mt-0.5 text-[15px] font-medium ${fix > 0.5 ? "text-credit" : "text-error"}`}>{naira(row.amount + delta * fix)}</p>
              </div>
              <div>
                <p className="text-muted">Printed balance</p>
                <p className="num mt-0.5 text-[15px]">{naira(row.balance_after as number)}</p>
              </div>
              <div>
                <p className="text-muted">Balance implies</p>
                <p className="num mt-0.5 text-[15px] font-medium text-accent-ink">{naira(implied)}</p>
              </div>
            </div>
          </div>
        </div>
      </AppScale>
    </Stage>
  );
}
