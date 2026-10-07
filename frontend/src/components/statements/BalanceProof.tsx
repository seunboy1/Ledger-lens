import { Check, X } from "lucide-react";
import { naira } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { DocumentDetail } from "@/types/api";

/** opening + credits − debits = computed closing, checked against the printed closing balance. */
export function BalanceProof({ proof: p, className }: { proof: DocumentDetail["proof"]; className?: string }) {
  return (
    <section aria-labelledby="proof-h" className={cn("rounded-[var(--radius-panel)] border border-line bg-surface", className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-line px-5 py-3.5">
        <h2 id="proof-h" className="text-[14px] font-semibold">Balance proof</h2>
        <p className="num text-[13px] text-ink-soft">
          {p.rows_verified.toLocaleString()} of {p.rows_total.toLocaleString()} rows reconcile
        </p>
      </div>
      <div className="flex flex-wrap items-end gap-x-6 gap-y-5 px-5 py-5">
        <Term label="Opening balance" value={naira(p.opening)} />
        <Term label="Credits" value={naira(p.total_credits)} op="+" tone="text-credit" />
        <Term label="Debits" value={naira(p.total_debits)} op="−" tone="text-debit" />
        <Term label="Computed closing" value={naira(p.closing_computed)} op="=" />
        <div className="basis-full border-t border-line pt-4 2xl:ml-auto 2xl:basis-auto 2xl:border-t-0 2xl:pt-0">
          <p className="text-[12.5px] text-muted">Printed closing balance</p>
          <p className="mt-0.5 flex items-center gap-2">
            <span className="num text-[18px] font-medium">{naira(p.closing_printed)}</span>
            {p.document_check_ok === true && (
              <span className="inline-flex items-center gap-1 text-[13px] text-credit">
                <Check size={14} aria-hidden /> Matches
              </span>
            )}
            {p.document_check_ok === false && (
              <span className="inline-flex items-center gap-1 text-[13px] text-error">
                <X size={14} aria-hidden /> Off by {naira(Math.abs((p.closing_computed ?? 0) - (p.closing_printed ?? 0)))}
              </span>
            )}
          </p>
        </div>
      </div>
    </section>
  );
}

function Term({ label, value, op, tone }: { label: string; value: string; op?: string; tone?: string }) {
  return (
    <div className="flex items-end gap-3">
      {op && <span className="num pb-0.5 text-[18px] text-muted" aria-hidden>{op}</span>}
      <div>
        <p className="text-[12.5px] text-muted">{label}</p>
        <p className={cn("num mt-0.5 text-[18px] font-medium", tone)}>{value}</p>
      </div>
    </div>
  );
}
