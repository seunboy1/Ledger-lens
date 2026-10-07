import React from "react";
import { interpolate, spring } from "remotion";
import { MessageView } from "@/components/ask/MessageView";
import { StatusBadge } from "@/components/StatusBadge";
import { BalanceProof } from "@/components/statements/BalanceProof";
import type { DocumentDetail, Message } from "@/types/api";
import ask from "../data/ask.json";
import overview from "../data/overview.json";
import doc from "../data/review-statement.json";
import { LensMark, naira } from "../kit";
import tl from "./timeline.json";
import { StatusBar } from "./Device";

// Sample workspace, shown with Nigerian bank names. Figures are the demo's own.
const B = tl.banks;
const relabel = (s: string) => s.replace(/Kestrel Bank/g, B.kestrel).replace(/Kestrel/g, B.kestrel);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = (f: number, from: number, len = 12) => interpolate(f, [from, from + len], [0, 1], clamp);
const pop = (f: number, at: number) => spring({ frame: f - at, fps: 30, config: { damping: 18, mass: 0.7 } });
const num = (v: string | number) => Number(v);

const ACCOUNTS = [
  { bank: B.kestrel, kind: "Salary", mask: "4471", rows: 120 },
  { bank: B.harbour, kind: "Savings", mask: "8830", rows: 21 },
  { bank: B.oakline, kind: "Business", mask: "2296", rows: 45 },
];

function Header({ title, sub }: { title: string; sub?: React.ReactNode }) {
  return (
    <div className="px-5 pb-3 pt-1">
      <p className="text-[28px] font-semibold leading-tight tracking-tight">{title}</p>
      {sub && <div className="mt-1 flex items-center gap-2 text-[14px] text-ink-soft">{sub}</div>}
    </div>
  );
}

function SampleChip() {
  return <span className="rounded-full bg-sunken px-2 py-0.5 text-[11.5px] font-medium text-muted">Sample data</span>;
}

/* ---------------- Dashboard ---------------- */

export function Dashboard({ f }: { f: number }) {
  const n = tl.notifs.at;
  const counts = [0, 120, 141, 186];
  const stepIdx = n.filter((t) => f >= t).length;
  const from = counts[Math.max(0, stepIdx - 1)];
  const to = counts[stepIdx];
  const rows = Math.round(stepIdx ? from + (to - from) * ease(f, n[stepIdx - 1], 10) : 0);
  const grow = ease(f, n[0], 70);
  const months = overview.months.map((m) => ({ ...m, inflow: num(m.inflow), outflow: num(m.outflow) }));
  const max = Math.max(...months.map((m) => Math.max(m.inflow, m.outflow)));
  const load = ease(f, tl.intro.load, 10);
  const scroll = interpolate(f, [tl.glance.salary - 8, tl.glance.salary + 14], [0, -262], clamp);
  const k = overview.kpis;

  return (
    <div style={{ opacity: load }}>
      <StatusBar />
      <div style={{ transform: `translateY(${scroll}px)` }}>
        <Header
          title="Overview"
          sub={
            <>
              Meridian Capital <SampleChip />
            </>
          }
        />
        <div className="mx-4 rounded-[18px] bg-ink px-5 py-4 text-bg">
          <p className="text-[13px] opacity-70">Verified transactions</p>
          <div className="flex items-baseline justify-between">
            <p className="num text-[40px] font-medium leading-tight">{rows}</p>
            <p className="text-[13px] opacity-70">{stepIdx} of 3 accounts reconciled</p>
          </div>
        </div>

        <div className="mx-4 mt-3 rounded-[18px] border border-line bg-surface px-4 pb-3 pt-3.5">
          <div className="flex items-center justify-between text-[13px]">
            <span className="font-medium">Money in and out</span>
            <span className="flex gap-3 text-muted">
              <span className="flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-[2px]" style={{ background: "var(--chart-in)" }} /> In</span>
              <span className="flex items-center gap-1"><i className="inline-block h-2 w-2 rounded-[2px]" style={{ background: "var(--chart-out)" }} /> Out</span>
            </span>
          </div>
          <div className="mt-3 flex h-[96px] items-end justify-between px-1">
            {months.map((m, i) => {
              const g = interpolate(grow, [i * 0.08, i * 0.08 + 0.5], [0, 1], clamp);
              return (
                <div key={m.month} className="flex flex-col items-center gap-1">
                  <div className="flex items-end gap-[3px]">
                    <div className="w-[14px] rounded-t-[4px]" style={{ height: (m.inflow / max) * 86 * g, background: "var(--chart-in)" }} />
                    <div className="w-[14px] rounded-t-[4px]" style={{ height: (m.outflow / max) * 86 * g, background: "var(--chart-out)" }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-1 flex justify-between px-1 text-[11px] text-muted">
            {["Apr", "May", "Jun", "Jul", "Aug", "Sep"].map((m) => (
              <span key={m} className="w-[31px] text-center">{m}</span>
            ))}
          </div>
        </div>

        <div className="mx-4 mt-3 grid grid-cols-2 gap-3">
          {[
            { label: "Avg monthly in", value: naira(num(k.avg_monthly_inflow)), cls: "text-credit" },
            { label: "Avg monthly out", value: naira(num(k.avg_monthly_outflow)), cls: "text-debit" },
          ].map((x, i) => (
            <div key={x.label} className="rounded-[16px] border border-line bg-surface px-3.5 py-3" style={{ opacity: ease(f, n[2] + 10 + i * 4) }}>
              <p className="text-[12px] text-muted">{x.label}</p>
              <p className={`num mt-0.5 text-[16px] font-medium ${x.cls}`}>{x.value}</p>
            </div>
          ))}
        </div>

        <p className="mx-5 mb-2 mt-4 text-[13px] font-medium text-ink-soft">Accounts</p>
        <div className="mx-4 overflow-hidden rounded-[16px] border border-line bg-surface">
          {ACCOUNTS.map((a, i) => (
            <div key={a.bank} className="flex items-center justify-between border-t border-line px-4 py-3 first:border-t-0">
              <div>
                <p className="text-[15px] font-medium">{a.bank}</p>
                <p className="num text-[12px] text-muted">
                  {a.kind} ••{a.mask}
                </p>
              </div>
              {f >= n[i] ? <StatusBadge status="reconciled" /> : <StatusBadge status="processing" />}
            </div>
          ))}
        </div>

        {/* Revealed by the "at a glance" scroll */}
        <div className="mx-4 mt-4 rounded-[18px] border border-line bg-surface px-4 py-3.5" style={{ opacity: ease(f, tl.glance.salary), transform: `translateY(${(1 - ease(f, tl.glance.salary)) * 14}px)` }}>
          <p className="text-[13px] font-medium text-ink-soft">Income</p>
          <p className="mt-1 text-[16px] font-semibold">Regular salary detected</p>
          <div className="mt-2 flex justify-between text-[13px]">
            <span className="num font-medium text-credit">{naira(num(overview.salary.average_amount))}</span>
            <span className="text-ink-soft">Day {overview.salary.typical_day}</span>
            <span className="text-ink-soft">{overview.salary.months} months</span>
          </div>
        </div>
        <div className="mx-4 mt-3 flex flex-wrap gap-2">
          {[
            `${overview.signals.returned_items.count} returned item`,
            `${overview.signals.other_lender_repayments.count} loan repayments`,
            `${overview.signals.betting.count} betting debits`,
          ].map((label, i) => (
            <span
              key={label}
              className="rounded-full bg-warn-soft px-3 py-1.5 text-[13px] font-medium text-warn"
              style={{ opacity: ease(f, tl.glance.signals + i * 5, 8), transform: `scale(${0.9 + 0.1 * ease(f, tl.glance.signals + i * 5, 8)})` }}
            >
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export function Notifications({ f }: { f: number }) {
  return (
    <>
      {tl.notifs.at.map((at, i) => {
        const a = ACCOUNTS[i];
        const inn = pop(f, at);
        const out = ease(f, at + 26, 8);
        if (f < at - 1 || out >= 1) return null;
        return (
          <div
            key={a.bank}
            className="absolute left-3 right-3 flex items-center gap-3 rounded-[22px] bg-surface/95 px-3.5 py-3 shadow-[0_12px_30px_rgba(10,20,60,0.25)]"
            style={{ top: 50, zIndex: 40, transform: `translateY(${(1 - inn) * -120 - out * 140}px)` }}
          >
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[11px] bg-bg">
              <LensMark size={30} />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex justify-between text-[13.5px]">
                <span className="font-semibold">{a.bank} statement verified</span>
                <span className="text-muted">now</span>
              </div>
              <p className="text-[13px] text-ink-soft">{a.rows} rows match the running balance</p>
            </div>
          </div>
        );
      })}
    </>
  );
}

/* ---------------- Ask ---------------- */

const user = { ...(ask.user_message as unknown as Message), content: relabel(ask.user_message.content) };
const answer = ask.assistant_message as unknown as Message;

export function AskScreen({ f }: { f: number }) {
  const t = tl.ask;
  const q = user.content;
  const typed = Math.floor(interpolate(f, [t.typeStart, t.typeEnd], [0, q.length], clamp));
  const sent = f >= t.send;
  const count = interpolate(f, [t.answer + 2, t.countEnd], [0, 480800], clamp);
  const live: Message = {
    ...answer,
    content: relabel(answer.content).replace(" This excludes 1 statement that is still processing or awaiting review.", ""),
    source_summary: relabel(answer.source_summary ?? ""),
    kpis: answer.kpis.map((k) => (k.label === "Debits" ? { ...k, value: naira(Math.round(count)) } : k)),
  };
  const rows = (answer.evidence?.rows ?? []).slice(0, 4);

  return (
    <div className="flex h-full flex-col">
      <StatusBar />
      <div className="flex min-h-0 flex-1 flex-col" style={{ zoom: 1.15 }}>
      <Header title="Ask" sub={<SampleChip />} />
      <div className="flex flex-1 flex-col gap-5 overflow-hidden px-5 pt-2">
        {sent && <MessageView message={user} />}
        {f >= t.answer && (
          <div style={{ opacity: ease(f, t.answer, 8), transform: `translateY(${(1 - ease(f, t.answer, 10)) * 10}px)` }}>
            <MessageView message={live} selected={f >= t.rows} onShowEvidence={() => {}} />
          </div>
        )}
        {f >= t.rows && (
          <div className="overflow-hidden rounded-[16px] border-2 border-accent bg-surface">
            {rows.map((r, i) => (
              <div
                key={r.id}
                className="flex items-start justify-between gap-3 border-t border-line px-3.5 py-2.5 first:border-t-0"
                style={{ opacity: ease(f, t.rows + i * 4, 6), transform: `translateX(${(1 - ease(f, t.rows + i * 4, 8)) * 30}px)` }}
              >
                <div className="min-w-0">
                  <p className="truncate text-[13px]">{r.description}</p>
                  <p className="text-[11.5px] text-muted">
                    {r.date}, {relabel(r.bank)}
                  </p>
                </div>
                <p className="num shrink-0 text-[13px] font-medium text-debit">−{r.amount}</p>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="px-4 pb-8 pt-3">
        <div className={`flex items-center gap-2 rounded-[16px] border bg-surface p-2 pl-4 ${sent ? "border-line-strong" : "border-accent"}`}>
          <span className={`flex-1 truncate text-[15px] ${typed && !sent ? "text-ink" : "text-muted"}`}>
            {!sent && typed ? q.slice(0, typed) : "Ask about your statements"}
            {!sent && <span className="text-accent" style={{ opacity: Math.floor(f / 8) % 2 ? 0 : 1 }}>|</span>}
          </span>
          <span className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-ink text-[16px] text-bg">↑</span>
        </div>
      </div>
      </div>
    </div>
  );
}

/* ---------------- Proof ---------------- */

const before = doc.proof as DocumentDetail["proof"];
const row = doc.failing_rows[0];
const previous = (row.expected_balance as number) + row.amount;
const implied = Math.abs((row.balance_after as number) - previous);
const delta = implied - row.amount;

export function ProofScreen({ f }: { f: number }) {
  const t = tl.proof;
  const fix = ease(f, t.fix, 8);
  const matched = f >= t.match;
  const debits = before.total_debits + delta * fix;
  const proof: DocumentDetail["proof"] = {
    ...before,
    total_debits: debits,
    closing_computed: (before.opening ?? 0) + before.total_credits - debits,
    rows_verified: matched ? before.rows_total : before.rows_verified,
    document_check_ok: f >= t.off ? matched : null,
  };
  const shake = !matched && f > t.off + 8 && f < t.fix - 4 ? Math.sin(f * 1.7) * 3 : 0;

  return (
    <div className="flex h-full flex-col">
      <StatusBar />
      <div style={{ zoom: 1.15 }}>
      <div className="flex items-start justify-between gap-2 px-5 pb-3 pt-1">
        <div>
          <p className="text-[24px] font-semibold leading-tight tracking-tight">{B.kestrel} Joint</p>
          <p className="num text-[12.5px] text-muted">Current ••0052, Jul to Sep 2026</p>
        </div>
        <StatusBadge status={matched ? "reconciled" : "needs_review"} />
      </div>
      <div className="px-4">
        <BalanceProof proof={proof} />
        <div
          className={`mt-3 rounded-[16px] border-2 bg-surface px-4 py-3 ${matched ? "border-credit" : "border-error"}`}
          style={{ opacity: ease(f, t.off, 8), transform: `translateX(${shake}px)` }}
        >
          <p className="text-[13.5px] font-medium">{row.description}</p>
          <p className="num text-[12px] text-muted">05 Aug 2026, page {row.page_number}</p>
          <div className="mt-2 grid grid-cols-2 gap-3 text-[12.5px]">
            <div>
              <p className="text-muted">{fix > 0.5 ? "Corrected amount" : "Extracted amount"}</p>
              <p className={`num mt-0.5 text-[16px] font-medium ${fix > 0.5 ? "text-credit" : "text-error"}`}>{naira(row.amount + delta * fix)}</p>
            </div>
            <div>
              <p className="text-muted">Balance implies</p>
              <p className="num mt-0.5 text-[16px] font-medium text-accent-ink">{naira(implied)}</p>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}
