/**
 * Phone screens for the promo, rendered in two layers with identical layout:
 *  - "base": the real screen, clipped by the phone, can blur and dim;
 *  - "pop":  unclipped; everything is invisible except elements marked `pop`,
 *            which lift out (scale, slide, shadow) from exactly where they sit.
 */
import React from "react";
import { interpolate, spring } from "remotion";
import { MessageView } from "@/components/ask/MessageView";
import { StatusBadge } from "@/components/StatusBadge";
import { BalanceProof } from "@/components/statements/BalanceProof";
import type { DocumentDetail, Message } from "@/types/api";
import ask from "../data/ask.json";
import overview from "../data/overview.json";
import doc from "../data/review-statement.json";
import { naira } from "../kit";
import { StatusBar } from "../phone/Device";
import tl from "./timeline.json";

export type Layer = "base" | "pop";
const B = tl.banks;
const relabel = (s: string) => s.replace(/Kestrel Bank/g, B.kestrel).replace(/Kestrel/g, B.kestrel);
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const outCubic = (x: number) => 1 - Math.pow(1 - x, 3);
export const ease = (f: number, a: number, b: number) => interpolate(f, [a, b], [0, 1], { ...clamp, easing: outCubic });
const num = (v: string | number) => Number(v);

/** 0 → 1 → 0 pop envelope: spring out at `at`, ease back over [back0, back1]. */
export function popAmount(f: number, at: number, back0: number, back1: number) {
  const up = spring({ frame: f - at, fps: 30, config: { damping: 14, mass: 0.8, stiffness: 140 } });
  return Math.max(0, up * (1 - ease(f, back0, back1)));
}

function Pop({
  layer,
  p,
  x = 0,
  scale = 1.15,
  rot = 0,
  children,
  className = "",
  style,
}: {
  layer: Layer;
  p: number;
  x?: number;
  scale?: number;
  rot?: number;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}) {
  const active = p > 0.001;
  if (layer === "base") {
    return (
      <div className={className} style={{ ...style, opacity: active ? 0 : (style?.opacity ?? 1) }}>
        {children}
      </div>
    );
  }
  return (
    <div
      className={`pop ${className}`}
      style={{
        ...style,
        opacity: active ? 1 : 0,
        position: "relative",
        zIndex: 5,
        transform: `translateX(${x * p}px) scale(${1 + (scale - 1) * p}) rotate(${rot * p}deg)`,
        boxShadow: `0 ${30 * p}px ${60 * p}px rgba(0,10,40,${0.35 * p}), 0 ${8 * p}px ${18 * p}px rgba(0,10,40,${0.2 * p})`,
      }}
    >
      {children}
    </div>
  );
}

function Header({ title, sub }: { title: string; sub?: React.ReactNode }) {
  return (
    <div className="px-5 pb-3 pt-1">
      <p className="text-[28px] font-semibold leading-tight tracking-tight">{title}</p>
      {sub && <div className="mt-1 flex items-center gap-2 text-[14px] text-ink-soft">{sub}</div>}
    </div>
  );
}

const ACCOUNTS = [
  { bank: B.kestrel, kind: "Salary", mask: "4471", rows: 120 },
  { bank: B.harbour, kind: "Savings", mask: "8830", rows: 21 },
  { bank: B.oakline, kind: "Business", mask: "2296", rows: 45 },
];
export const NOTIFS = ACCOUNTS;

/* ---------------- Dashboard ---------------- */

export function Dashboard({ f, layer }: { f: number; layer: Layer }) {
  const n = tl.notifs;
  const counts = [0, 120, 141, 186];
  const step = n.filter((t) => f >= t).length;
  const from = counts[Math.max(0, step - 1)];
  const to = counts[step];
  const rows = Math.round(step ? from + (to - from) * ease(f, n[step - 1], n[step - 1] + 10) : 0);
  const grow = ease(f, n[0], n[0] + 70);
  const months = overview.months.map((m) => ({ ...m, inflow: num(m.inflow), outflow: num(m.outflow) }));
  const max = Math.max(...months.map((m) => Math.max(m.inflow, m.outflow)));
  const scroll = interpolate(f, tl.glance.scroll, [0, -262], { ...clamp, easing: outCubic });
  const k = overview.kpis;
  const heroP = popAmount(f, tl.heroPop[0], tl.heroPop[1], tl.heroPop[1] + 14);

  return (
    <div>
      <StatusBar />
      <div style={{ transform: `translateY(${scroll}px)` }}>
        <Header title="Overview" sub={<>Meridian Capital</>} />
        <Pop layer={layer} p={heroP} scale={1.12} rot={-3} className="mx-4 rounded-[18px]">
          <div className="rounded-[18px] px-5 py-4 text-white" style={{ background: "linear-gradient(135deg, #1b2a8f, #0f1b5c)" }}>
            <div className="flex items-center justify-between text-[13px]">
              <span className="opacity-75">Verified transactions</span>
              <span className="rounded-full bg-white/15 px-2 py-0.5 text-[11.5px]">3 banks</span>
            </div>
            <div className="mt-1 flex items-baseline justify-between">
              <p className="num text-[40px] font-medium leading-tight">{rows}</p>
              <p className="text-[13px] opacity-75">{step} of 3 accounts reconciled</p>
            </div>
          </div>
        </Pop>

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
                <div key={m.month} className="flex items-end gap-[3px]">
                  <div className="w-[14px] rounded-t-[4px]" style={{ height: (m.inflow / max) * 86 * g, background: "var(--chart-in)" }} />
                  <div className="w-[14px] rounded-t-[4px]" style={{ height: (m.outflow / max) * 86 * g, background: "var(--chart-out)" }} />
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
          ].map((x) => (
            <div key={x.label} className="rounded-[16px] border border-line bg-surface px-3.5 py-3">
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
              <StatusBadge status={f >= n[i] ? "reconciled" : "processing"} />
            </div>
          ))}
        </div>

        <div className="mx-4 mt-4 rounded-[18px] border border-line bg-surface px-4 py-3.5">
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
          ].map((label) => (
            <span key={label} className="rounded-full bg-warn-soft px-3 py-1.5 text-[13px] font-medium text-warn">
              {label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ---------------- Ask ---------------- */

const user = { ...(ask.user_message as unknown as Message), content: relabel(ask.user_message.content) };
const answer = ask.assistant_message as unknown as Message;
const ROW_OFFSETS = [-80, 64, -64];

export function AskScreen({ f, layer }: { f: number; layer: Layer }) {
  const t = tl.ask;
  const q = user.content;
  const typed = Math.floor(interpolate(f, [t.typeStart, t.typeEnd], [0, q.length], clamp));
  const sent = f >= t.send;
  const count = interpolate(f, [t.answer + 2, t.countEnd], [0, 480800], { ...clamp, easing: outCubic });
  const live: Message = {
    ...answer,
    content: relabel(answer.content).replace(" This excludes 1 statement that is still processing or awaiting review.", ""),
    source_summary: "18 verified rows",
    kpis: answer.kpis.map((k) => (k.label === "Debits" ? { ...k, value: naira(Math.round(count)) } : k)),
  };
  const rows = (answer.evidence?.rows ?? []).slice(0, 3);

  return (
    <div className="flex h-full flex-col">
      <StatusBar />
      <div className="flex min-h-0 flex-1 flex-col" style={{ zoom: 1.15 }}>
        <Header title="Ask" />
        <div className="flex flex-1 flex-col gap-5 px-5 pt-1">
          {sent && <MessageView message={user} />}
          {f >= t.answer && (
            <div style={{ opacity: ease(f, t.answer, t.answer + 8), transform: `translateY(${(1 - ease(f, t.answer, t.answer + 10)) * 10}px)` }}>
              <MessageView message={live} selected={f >= t.rows} onShowEvidence={() => {}} />
            </div>
          )}
          {f >= t.rows && (
            <div className="flex flex-col gap-2">
              {rows.map((r, i) => {
                const p = popAmount(f, t.pops[i], t.popBack[0] + i * 3, t.popBack[1] + i * 3);
                return (
                  <Pop
                    key={r.id}
                    layer={layer}
                    p={p}
                    x={ROW_OFFSETS[i]}
                    className="rounded-[14px]"
                    style={{ opacity: ease(f, t.rows + i * 3, t.rows + i * 3 + 6) }}
                  >
                    <div className="flex items-center justify-between gap-3 rounded-[14px] border border-line bg-surface px-3.5 py-2.5">
                      <div className="min-w-0">
                        <p className="truncate text-[13px] font-medium">{r.description}</p>
                        <p className="text-[11.5px] text-muted">
                          {r.date}, {relabel(r.bank)}
                        </p>
                      </div>
                      <p className="num shrink-0 text-[13px] font-medium text-debit">−{r.amount}</p>
                    </div>
                  </Pop>
                );
              })}
            </div>
          )}
        </div>
        <div className="px-4 pb-7 pt-3">
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

export function ProofScreen({ f, layer }: { f: number; layer: Layer }) {
  const t = tl.proof;
  const fix = ease(f, t.fix, t.fix + 8);
  const matched = f >= t.match;
  const debits = before.total_debits + delta * fix;
  const proof: DocumentDetail["proof"] = {
    ...before,
    total_debits: debits,
    closing_computed: (before.opening ?? 0) + before.total_credits - debits,
    rows_verified: matched ? before.rows_total : before.rows_verified,
    document_check_ok: f >= t.off ? matched : null,
  };
  const p = popAmount(f, t.pop, t.popBack[0], t.popBack[1]);
  const sheet = ease(f, tl.sheet[0], tl.sheet[1]);

  return (
    <div className="relative flex h-full flex-col">
      <StatusBar />
      <div style={{ zoom: 1.15 }}>
        <div className="flex items-start justify-between gap-2 px-5 pb-3 pt-1">
          <div>
            <p className="text-[24px] font-semibold leading-tight tracking-tight">{B.kestrel} Joint</p>
            <p className="num text-[12.5px] text-muted">Current ••0052</p>
          </div>
          <StatusBadge status={matched ? "reconciled" : "needs_review"} />
        </div>
        <div className="px-4">
          <BalanceProof proof={proof} />
          <Pop layer={layer} p={p} x={-48} scale={1.12} className="mt-3 rounded-[16px]" style={{ opacity: ease(f, t.off, t.off + 8) }}>
            <div className={`rounded-[16px] border-2 bg-surface px-4 py-3 ${matched ? "border-credit" : "border-error"}`}>
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
          </Pop>
        </div>
      </div>

      {layer === "base" && sheet > 0 && (
        <>
          <div className="absolute inset-0" style={{ background: `rgba(15,18,23,${0.32 * sheet})` }} />
          <div
            className="absolute inset-x-0 bottom-0 rounded-t-[26px] bg-surface px-5 pb-9 pt-3 shadow-[0_-10px_40px_rgba(0,10,40,0.25)]"
            style={{ transform: `translateY(${(1 - sheet) * 460}px)` }}
          >
            <div className="mx-auto h-[5px] w-10 rounded-full bg-line-strong" />
            <div className="mt-4 flex items-center justify-between">
              <p className="text-[21px] font-semibold tracking-tight">Statement reconciled</p>
              <StatusBadge status="reconciled" />
            </div>
            <p className="mt-1 text-[13.5px] text-ink-soft">
              {B.kestrel} Joint ••0052
            </p>
            <div className="mt-4 divide-y divide-line rounded-[16px] border border-line">
              {[
                ["Rows matching the balance", `${before.rows_total} of ${before.rows_total}`],
                ["Closing balance", naira(before.closing_printed ?? 0)],
                ["Corrected by reviewer", "1 row"],
              ].map(([k, v]) => (
                <div key={k} className="flex items-center justify-between px-4 py-3 text-[14px]">
                  <span className="text-ink-soft">{k}</span>
                  <span className="num font-medium">{v}</span>
                </div>
              ))}
            </div>
            <p className="mt-3 text-[13.5px] text-credit">Now counts in every answer.</p>
            <div className="mt-4 flex h-12 items-center justify-center rounded-[14px] bg-accent text-[15px] font-semibold text-on-accent">View rows</div>
          </div>
        </>
      )}
    </div>
  );
}
