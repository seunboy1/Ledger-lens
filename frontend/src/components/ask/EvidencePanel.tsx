"use client";

import * as Tabs from "@radix-ui/react-tabs";
import { ShieldCheck } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Evidence } from "@/types/api";

export function EvidencePanel({ evidence }: { evidence: Evidence | null }) {
  if (!evidence) {
    return (
      <div className="flex h-full flex-col px-5 py-5">
        <h2 className="text-[13px] font-medium text-ink-soft">Evidence</h2>
        <p className="mt-auto mb-auto max-w-[30ch] text-[13.5px] leading-relaxed text-muted">
          Ask a question and the rows behind the answer, plus how it was computed, appear here.
        </p>
      </div>
    );
  }

  const shown = evidence.rows.length;

  return (
    <Tabs.Root defaultValue="rows" className="flex h-full flex-col">
      <div className="border-b border-line px-5 pb-3 pt-5">
        <h2 className="text-[15px] font-semibold tracking-tight">{evidence.summary_title}</h2>
        <p className="mt-0.5 text-[13px] text-ink-soft">{evidence.summary_subtitle}</p>
        <Tabs.List aria-label="Evidence views" className="mt-4 flex gap-1">
          {[
            ["rows", "Rows"],
            ["plan", "Query plan"],
          ].map(([value, label]) => (
            <Tabs.Trigger
              key={value}
              value={value}
              className="h-7 rounded-[6px] px-2.5 text-[13px] text-muted transition-colors hover:text-ink data-[state=active]:bg-sunken data-[state=active]:font-medium data-[state=active]:text-ink"
            >
              {label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
      </div>

      <Tabs.Content value="rows" className="min-h-0 flex-1 overflow-y-auto outline-none">
        {shown === 0 ? (
          <p className="px-5 py-6 text-[13.5px] text-muted">No rows matched this question.</p>
        ) : (
          <>
            <table className="w-full border-collapse text-[13px]">
              <caption className="sr-only">Rows behind the answer</caption>
              <thead className="sticky top-0 bg-surface">
                <tr className="text-left text-[12px] text-muted">
                  <th scope="col" className="py-2 pl-5 pr-2 font-normal">Row</th>
                  <th scope="col" className="py-2 pl-2 pr-5 text-right font-normal">Amount</th>
                </tr>
              </thead>
              <tbody>
                {evidence.rows.map((r) => (
                  <tr key={r.id} className={cn("border-t border-line align-top", r.focused && "bg-accent-soft")}>
                    <td className="py-2.5 pl-5 pr-2">
                      <p className="line-clamp-2 leading-snug">{r.description}</p>
                      <p className="mt-0.5 text-[12px] text-muted">
                        {r.date}, {r.bank}
                      </p>
                    </td>
                    <td className="whitespace-nowrap py-2.5 pl-2 pr-5 text-right">
                      <p className={cn("num font-medium", r.type === "credit" ? "text-credit" : "text-debit")}>
                        {r.type === "credit" ? "+" : "−"}
                        {r.amount}
                      </p>
                      <p className="mt-0.5 text-[12px] text-muted">
                        {r.type === "credit" ? "Credit" : "Debit"}
                        {r.raw_label.toLowerCase() !== r.type && (
                          <span title="Label printed on the statement">
                            , printed <span className="num">{r.raw_label}</span>
                          </span>
                        )}
                      </p>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {evidence.total_rows > shown && (
              <p className="border-t border-line px-5 py-3 text-[12.5px] text-muted">
                Showing {shown} of {evidence.total_rows.toLocaleString()} matching rows. Totals include all of them.
              </p>
            )}
          </>
        )}
      </Tabs.Content>

      <Tabs.Content value="plan" className="min-h-0 flex-1 overflow-y-auto px-5 py-5 outline-none">
        <ol className="relative space-y-5 border-l border-line-strong pl-5">
          {evidence.lineage.map((step) => (
            <li key={step.title} className="relative">
              <span className="absolute -left-[25px] top-1.5 h-2 w-2 rounded-full bg-accent" aria-hidden />
              <p className="text-[13.5px] font-medium">{step.title}</p>
              <p className={cn("mt-0.5 break-words text-[12.5px] leading-relaxed text-ink-soft", /[=_]/.test(step.detail) && "num")}>{step.detail}</p>
            </li>
          ))}
        </ol>
      </Tabs.Content>

      <div className="flex gap-2.5 border-t border-line px-5 py-3.5 text-[12.5px] leading-relaxed text-ink-soft">
        <ShieldCheck size={15} strokeWidth={1.75} className="mt-0.5 shrink-0 text-accent-ink" aria-hidden />
        <p>{evidence.isolation_note}</p>
      </div>
    </Tabs.Root>
  );
}
