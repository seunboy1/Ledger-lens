"use client";

import { useEffect, useRef, useState } from "react";
import { monthLabel, naira, nairaCompact } from "@/lib/format";
import type { MonthRow } from "@/types/api";

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return { ref, width };
}

function niceMax(v: number) {
  if (v <= 0) return 1;
  const pow = 10 ** Math.floor(Math.log10(v));
  const n = v / pow;
  const step = n <= 1 ? 1 : n <= 2 ? 2 : n <= 2.5 ? 2.5 : n <= 5 ? 5 : 10;
  return step * pow;
}

const PAD = { top: 12, right: 8, bottom: 26, left: 52 };

function Tooltip({ x, width, children }: { x: number; width: number; children: React.ReactNode }) {
  const left = Math.min(Math.max(x - 90, 0), Math.max(width - 180, 0));
  return (
    <div
      role="status"
      className="pointer-events-none absolute top-0 z-10 w-[180px] rounded-[var(--radius-ctl)] border border-line bg-surface px-3 py-2 text-[12.5px] shadow-[var(--shadow-pop)]"
      style={{ left }}
    >
      {children}
    </div>
  );
}

/** Grouped bars: money in vs money out per month. One axis, shared scale. */
export function CashflowChart({ months, height = 220 }: { months: MonthRow[]; height?: number }) {
  const { ref, width } = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  const max = niceMax(Math.max(...months.map((m) => Math.max(m.inflow, m.outflow)), 1));
  const innerW = Math.max(width - PAD.left - PAD.right, 0);
  const innerH = height - PAD.top - PAD.bottom;
  const band = months.length ? innerW / months.length : 0;
  const barW = Math.max(Math.min(band * 0.28, 22), 4);
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH;
  const ticks = [0, 0.5, 1].map((f) => f * max);
  const peak = months.reduce((best, m, i) => (m.inflow > (months[best]?.inflow ?? -1) ? i : best), 0);

  return (
    <div ref={ref} className="relative" onMouseLeave={() => setHover(null)}>
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label="Monthly money in and money out, grouped bars">
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--chart-grid)" />
              <text x={PAD.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="num" fontSize={11} fill="var(--muted)">
                {nairaCompact(t)}
              </text>
            </g>
          ))}
          {months.map((m, i) => {
            const cx = PAD.left + band * i + band / 2;
            const bars = [
              { v: m.inflow, color: "var(--chart-in)", x: cx - barW - 1 },
              { v: m.outflow, color: "var(--chart-out)", x: cx + 1 },
            ];
            return (
              <g key={m.month} opacity={hover === null || hover === i ? 1 : 0.45}>
                {bars.map((b, j) => {
                  const top = y(b.v);
                  const h = PAD.top + innerH - top;
                  const r = Math.min(4, h);
                  return (
                    <path
                      key={j}
                      d={`M${b.x},${PAD.top + innerH} V${top + r} Q${b.x},${top} ${b.x + r},${top} H${b.x + barW - r} Q${b.x + barW},${top} ${b.x + barW},${top + r} V${PAD.top + innerH} Z`}
                      fill={b.color}
                    />
                  );
                })}
                {i === peak && hover === null && (
                  <text x={cx - barW / 2 - 1} y={y(m.inflow) - 6} textAnchor="middle" className="num" fontSize={11} fill="var(--ink-soft)">
                    {nairaCompact(m.inflow)}
                  </text>
                )}
                <text x={cx} y={height - 8} textAnchor="middle" fontSize={11.5} fill="var(--muted)">
                  {monthLabel(m.month)}
                </text>
                <rect
                  x={PAD.left + band * i}
                  y={PAD.top}
                  width={band}
                  height={innerH}
                  fill="transparent"
                  onMouseEnter={() => setHover(i)}
                  onFocus={() => setHover(i)}
                  onBlur={() => setHover(null)}
                  tabIndex={0}
                  aria-label={`${monthLabel(m.month)}: in ${naira(m.inflow)}, out ${naira(m.outflow)}`}
                />
              </g>
            );
          })}
        </svg>
      )}
      {hover !== null && months[hover] && (
        <Tooltip x={PAD.left + band * hover + band / 2} width={width}>
          <p className="font-medium">{monthLabel(months[hover].month)} {months[hover].month.slice(0, 4)}</p>
          <p className="mt-1 flex justify-between gap-3">
            <span className="flex items-center gap-1.5 text-ink-soft"><Swatch color="var(--chart-in)" /> In</span>
            <span className="num">{naira(months[hover].inflow)}</span>
          </p>
          <p className="flex justify-between gap-3">
            <span className="flex items-center gap-1.5 text-ink-soft"><Swatch color="var(--chart-out)" /> Out</span>
            <span className="num">{naira(months[hover].outflow)}</span>
          </p>
          <p className="mt-1 flex justify-between gap-3 border-t border-line pt-1">
            <span className="text-ink-soft">Net</span>
            <span className="num">{naira(months[hover].net, { signed: true })}</span>
          </p>
        </Tooltip>
      )}
    </div>
  );
}

/** Month-end balance across all accounts. Single series, so no legend box. */
export function BalanceChart({ months, height = 180 }: { months: MonthRow[]; height?: number }) {
  const { ref, width } = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);

  const values = months.map((m) => m.closing_balance);
  const max = niceMax(Math.max(...values, 1));
  const innerW = Math.max(width - PAD.left - PAD.right, 0);
  const innerH = height - PAD.top - PAD.bottom;
  const step = months.length > 1 ? innerW / (months.length - 1) : 0;
  const x = (i: number) => PAD.left + step * i;
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH;
  const path = values.map((v, i) => `${i ? "L" : "M"}${x(i)},${y(v)}`).join(" ");
  const last = values.length - 1;

  return (
    <div ref={ref} className="relative" onMouseLeave={() => setHover(null)}>
      {width > 0 && months.length > 0 && (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label="Month-end balance across all accounts"
          onMouseMove={(e) => {
            const rect = e.currentTarget.getBoundingClientRect();
            const i = Math.round((e.clientX - rect.left - PAD.left) / (step || 1));
            setHover(Math.min(Math.max(i, 0), last));
          }}
        >
          {[0, 0.5, 1].map((f) => (
            <g key={f}>
              <line x1={PAD.left} x2={width - PAD.right} y1={y(f * max)} y2={y(f * max)} stroke="var(--chart-grid)" />
              <text x={PAD.left - 8} y={y(f * max)} dy="0.32em" textAnchor="end" className="num" fontSize={11} fill="var(--muted)">
                {nairaCompact(f * max)}
              </text>
            </g>
          ))}
          {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={PAD.top} y2={PAD.top + innerH} stroke="var(--border-strong)" />}
          <path d={path} fill="none" stroke="var(--chart-line)" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
          {values.map((v, i) => (
            <circle
              key={i}
              cx={x(i)}
              cy={y(v)}
              r={hover === i || (hover === null && i === last) ? 4.5 : 0}
              fill="var(--chart-line)"
              stroke="var(--surface)"
              strokeWidth={2}
            />
          ))}
          {hover === null && last >= 0 && (
            <text x={x(last)} y={y(values[last]) - 10} textAnchor="end" className="num" fontSize={11} fill="var(--ink-soft)">
              {nairaCompact(values[last])}
            </text>
          )}
          {months.map((m, i) => (
            <text key={m.month} x={x(i)} y={height - 8} textAnchor={i === 0 ? "start" : i === last ? "end" : "middle"} fontSize={11.5} fill="var(--muted)">
              {monthLabel(m.month)}
            </text>
          ))}
        </svg>
      )}
      {hover !== null && months[hover] && (
        <Tooltip x={x(hover)} width={width}>
          <p className="font-medium">
            End of {monthLabel(months[hover].month)} {months[hover].month.slice(0, 4)}
          </p>
          <p className="num mt-1">{naira(months[hover].closing_balance)}</p>
        </Tooltip>
      )}
    </div>
  );
}

export function Swatch({ color }: { color: string }) {
  return <span className="inline-block h-2.5 w-2.5 rounded-[3px]" style={{ background: color }} aria-hidden />;
}
