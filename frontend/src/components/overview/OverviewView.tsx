"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight, Briefcase } from "lucide-react";
import { BalanceChart, CashflowChart, Swatch } from "@/components/overview/Charts";
import { ErrorState, SkeletonRows } from "@/components/States";
import { useApi } from "@/hooks/useApi";
import { monthLabel, naira, shortDate } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { Overview, Workspace } from "@/types/api";

const SIGNALS: { key: keyof Overview["signals"]; label: string; ask: string; risk: string }[] = [
  {
    key: "returned_items",
    label: "Returned or bounced items",
    ask: "Show any bounced or returned items",
    risk: "A returned cheque or failed debit points to cash shortfalls.",
  },
  {
    key: "other_lender_repayments",
    label: "Repayments to other lenders",
    ask: "Any loan repayments to other lenders?",
    risk: "Existing obligations that reduce capacity to repay.",
  },
  {
    key: "betting",
    label: "Betting and gambling",
    ask: "How much betting spend is there?",
    risk: "Discretionary spend that lenders often cap.",
  },
];

export function OverviewView() {
  const ws = useApi<Workspace>("/workspace");
  const ov = useApi<Overview>("/analytics/overview");
  const [table, setTable] = useState(false);

  const error = ws.error ?? ov.error;
  if (error) {
    return (
      <Page>
        <ErrorState message={error.message} onRetry={() => void Promise.all([ws.refresh(), ov.refresh()])} />
      </Page>
    );
  }
  if (!ws.data || !ov.data) {
    return (
      <Page>
        <div className="skeleton h-7 w-48" />
        <div className="skeleton mt-3 h-4 w-96 max-w-full" />
        <div className="mt-10">
          <SkeletonRows rows={6} />
        </div>
      </Page>
    );
  }

  const w = ws.data;
  const o = ov.data;
  const pendingReview = w.documents.needs_review ?? 0;
  const processing = (w.documents.processing ?? 0) + (w.documents.uploaded ?? 0);
  const first = w.banks.map((b) => b.from).sort()[0];
  const lastDate = w.banks.map((b) => b.to).sort().at(-1);

  if (!o.months.length) {
    return (
      <Page>
        <h1 className="text-[24px] font-semibold tracking-tight">Overview</h1>
        <div className="mt-10 max-w-[52ch]">
          <p className="text-[15px] font-medium">No verified statements yet</p>
          <p className="mt-1 text-[14px] leading-relaxed text-ink-soft">
            {processing
              ? `${processing} statement${processing > 1 ? "s are" : " is"} still being extracted. This page fills in once they reconcile.`
              : "Upload a bank statement and the cashflow, balances and risk signals appear here once it reconciles."}
          </p>
          <Link href="/statements" className="mt-4 inline-flex items-center gap-1 text-[14px] font-medium text-accent-ink hover:underline">
            Go to Statements <ArrowUpRight size={14} />
          </Link>
        </div>
      </Page>
    );
  }

  const kpis = [
    { label: "Average monthly inflow", value: naira(o.kpis.avg_monthly_inflow), tone: "text-credit" },
    { label: "Average monthly outflow", value: naira(o.kpis.avg_monthly_outflow), tone: "text-debit" },
    { label: "Balance, latest month end", value: naira(o.kpis.closing_balance), tone: "" },
    { label: "Lowest running balance", value: naira(o.kpis.min_balance), tone: "" },
  ];

  return (
    <Page>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[24px] font-semibold tracking-tight">Overview</h1>
          <p className="mt-1 text-[14px] text-ink-soft">
            {w.banks.length} banks, {shortDate(first)} to {shortDate(lastDate)}, {w.verified_transactions.toLocaleString()} verified transactions
          </p>
        </div>
        {(pendingReview > 0 || processing > 0) && (
          <Link href="/statements" className="text-[13.5px] text-warn hover:underline">
            {pendingReview > 0 && `${pendingReview} statement${pendingReview > 1 ? "s" : ""} awaiting review`}
            {pendingReview > 0 && processing > 0 && ", "}
            {processing > 0 && `${processing} processing`}. Not included below.
          </Link>
        )}
      </div>

      <dl className="mt-8 grid grid-cols-1 gap-y-5 border-y border-line py-5 sm:grid-cols-2 xl:grid-cols-4 xl:divide-x xl:divide-line">
        {kpis.map((k, i) => (
          <div key={k.label} className={cn("min-w-0 pr-4", i > 0 && "xl:pl-6")}>
            <dt className="text-[12.5px] text-muted">{k.label}</dt>
            <dd className={cn("num mt-1 whitespace-nowrap text-[20px] font-medium tracking-tight", k.tone)}>{k.value}</dd>
          </div>
        ))}
      </dl>

      <div className="mt-10 grid gap-10 xl:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <section aria-labelledby="cash-h">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="cash-h" className="text-[14px] font-semibold">Money in and out, by month</h2>
            <div className="flex items-center gap-4 text-[12.5px] text-ink-soft">
              <span className="flex items-center gap-1.5"><Swatch color="var(--chart-in)" /> In</span>
              <span className="flex items-center gap-1.5"><Swatch color="var(--chart-out)" /> Out</span>
              <button type="button" onClick={() => setTable((t) => !t)} className="text-accent-ink hover:underline" aria-pressed={table}>
                {table ? "Show chart" : "Show table"}
              </button>
            </div>
          </div>
          <div className="mt-4">
            {table ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[480px] border-collapse text-[13px]">
                  <caption className="sr-only">Monthly money in, money out, net and month-end balance</caption>
                  <thead>
                    <tr className="text-left text-[12.5px] text-muted">
                      {["Month", "In", "Out", "Net", "Month-end balance"].map((h, i) => (
                        <th key={h} scope="col" className={cn("py-2 font-normal", i > 0 && "text-right")}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {o.months.map((m) => (
                      <tr key={m.month} className="border-t border-line">
                        <td className="py-2">{monthLabel(m.month)} {m.month.slice(0, 4)}</td>
                        <td className="num py-2 text-right text-credit">{naira(m.inflow)}</td>
                        <td className="num py-2 text-right text-debit">{naira(m.outflow)}</td>
                        <td className="num py-2 text-right">{naira(m.net, { signed: true })}</td>
                        <td className="num py-2 text-right">{naira(m.closing_balance)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <CashflowChart months={o.months} />
            )}
          </div>
        </section>

        <section aria-labelledby="income-h" className="xl:border-l xl:border-line xl:pl-8">
          <h2 id="income-h" className="text-[14px] font-semibold">Income</h2>
          {o.salary ? (
            <div className="mt-4">
              <div className="flex items-start gap-3">
                <Briefcase size={18} strokeWidth={1.5} className="mt-0.5 shrink-0 text-credit" aria-hidden />
                <div>
                  <p className="text-[14px] font-medium">Regular salary detected</p>
                  <p className="mt-0.5 text-[13.5px] text-ink-soft">{o.salary.narration}</p>
                </div>
              </div>
              <dl className="mt-5 grid grid-cols-2 gap-x-6 gap-y-4 text-[13.5px]">
                <div>
                  <dt className="text-muted">Average amount</dt>
                  <dd className="num mt-0.5 text-[17px] font-medium text-credit">{naira(o.salary.average_amount)}</dd>
                </div>
                <div>
                  <dt className="text-muted">Usually paid</dt>
                  <dd className="mt-0.5 text-[17px] font-medium">Day {o.salary.typical_day}</dd>
                </div>
                <div>
                  <dt className="text-muted">Consistency</dt>
                  <dd className="mt-0.5">{o.salary.months} consecutive months</dd>
                </div>
                <div>
                  <dt className="text-muted">Account</dt>
                  <dd className="mt-0.5">{o.salary.bank}</dd>
                </div>
              </dl>
              <Link href={`/ask?q=${encodeURIComponent("Show salary credits")}`} className="mt-5 inline-flex items-center gap-1 text-[13.5px] text-accent-ink hover:underline">
                See the salary rows <ArrowUpRight size={13} />
              </Link>
            </div>
          ) : (
            <p className="mt-4 text-[13.5px] text-ink-soft">No recurring salary-like credit found across three or more months.</p>
          )}
        </section>

        <section aria-labelledby="bal-h">
          <h2 id="bal-h" className="text-[14px] font-semibold">Month-end balance, all accounts</h2>
          <div className="mt-4">
            <BalanceChart months={o.months} />
          </div>
        </section>

        <section aria-labelledby="risk-h" className="xl:border-l xl:border-line xl:pl-8">
          <h2 id="risk-h" className="text-[14px] font-semibold">Risk signals</h2>
          <ul className="mt-3">
            {SIGNALS.map((s) => {
              const sig = o.signals[s.key];
              const hit = sig.count > 0;
              return (
                <li key={s.key} className="border-t border-line py-3.5 first:border-t-0">
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="text-[13.5px] font-medium">{s.label}</p>
                    <p className={cn("num shrink-0 text-[13.5px]", hit ? "text-warn" : "text-muted")}>
                      {hit ? `${sig.count}x, ${naira(sig.total)}` : "None"}
                    </p>
                  </div>
                  <p className="mt-0.5 text-[12.5px] leading-relaxed text-muted">{s.risk}</p>
                  {hit && (
                    <Link href={`/ask?q=${encodeURIComponent(s.ask)}`} className="mt-1.5 inline-flex items-center gap-1 text-[12.5px] text-accent-ink hover:underline">
                      View rows <ArrowUpRight size={12} />
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      </div>

      <section aria-labelledby="cp-h" className="mt-12">
        <h2 id="cp-h" className="text-[14px] font-semibold">Where the money goes</h2>
        <p className="mt-0.5 text-[13px] text-muted">Largest debit counterparties, share of all debits</p>
        <ul className="mt-4 grid gap-x-10 gap-y-3 md:grid-cols-2">
          {o.counterparties.map((c) => (
            <li key={c.name} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1">
              <span className="truncate text-[13.5px]" title={c.name}>{c.name}</span>
              <span className="num text-[13px] text-ink-soft">{naira(c.total)}</span>
              <span className="col-span-2 flex items-center gap-2">
                <span className="h-1.5 rounded-full bg-ink-soft" style={{ width: `${Math.max(c.share * 100, 1.5)}%` }} aria-hidden />
                <span className="num text-[12px] text-muted">{(c.share * 100).toFixed(1)}%</span>
              </span>
            </li>
          ))}
        </ul>
      </section>
    </Page>
  );
}

function Page({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-[1180px] px-5 py-8 md:px-8">{children}</div>;
}
