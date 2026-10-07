"use client";

import { Database, Rows3, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Message, Tone } from "@/types/api";

const toneText: Record<Tone, string> = {
  credit: "text-credit",
  debit: "text-debit",
  neutral: "text-ink",
};

export function MessageView({
  message,
  selected,
  onShowEvidence,
  onFeedback,
}: {
  message: Message;
  selected?: boolean;
  onShowEvidence?: () => void;
  onFeedback?: (helpful: boolean) => void;
}) {
  if (message.role === "user") {
    return (
      <div className="rise-in flex justify-end">
        <p className="max-w-[80%] rounded-[var(--radius-panel)] bg-sunken px-4 py-2.5 text-[14.5px] leading-relaxed">{message.content}</p>
      </div>
    );
  }

  const isSql = message.route_kind === "sql";
  const RouteIcon = isSql ? Database : Sparkles;
  const rows = message.evidence?.rows.length ?? 0;

  return (
    <article className="rise-in">
      {message.route_kind && (
        <p className="mb-2 flex items-center gap-1.5 text-[12.5px] text-muted">
          <RouteIcon size={13} strokeWidth={1.75} aria-hidden />
          {message.engine === "agent"
            ? `Answered by the agent, figures from ${isSql ? "SQL aggregation" : "semantic search"}`
            : isSql
              ? "Answered with SQL aggregation"
              : "Answered with semantic search"}
        </p>
      )}
      <p className="max-w-[68ch] text-[15px] leading-[1.65]">{message.content}</p>

      {message.kpis.length > 0 && (
        <dl className="mt-4 flex flex-wrap gap-x-8 gap-y-3 border-t border-line pt-4">
          {message.kpis.map((k) => (
            <div key={k.label} className="min-w-[110px]">
              <dt className="text-[12.5px] text-muted">{k.label}</dt>
              <dd className={cn("num mt-0.5 text-[18px] font-medium", toneText[k.tone])}>{k.value}</dd>
            </div>
          ))}
        </dl>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {rows > 0 && onShowEvidence && (
          <button
            type="button"
            onClick={onShowEvidence}
            aria-pressed={selected}
            className={cn(
              "inline-flex min-h-8 items-center gap-2 rounded-[var(--radius-ctl)] border px-3 py-1.5 text-left text-[13px] leading-snug transition-colors",
              selected ? "border-accent bg-accent-soft text-accent-ink" : "border-line-strong text-ink-soft hover:border-accent hover:text-accent-ink",
            )}
          >
            <Rows3 size={14} strokeWidth={1.75} className="shrink-0" aria-hidden />
            {message.source_summary ?? `${rows} rows`}
          </button>
        )}
        {onFeedback && (
          <div className="ml-auto flex gap-1">
            {([true, false] as const).map((helpful) => {
              const Icon = helpful ? ThumbsUp : ThumbsDown;
              const on = message.is_helpful === helpful;
              return (
                <button
                  key={String(helpful)}
                  type="button"
                  onClick={() => onFeedback(helpful)}
                  aria-label={helpful ? "Helpful" : "Not helpful"}
                  aria-pressed={on}
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-[var(--radius-ctl)] text-muted transition-colors hover:bg-sunken hover:text-ink active:scale-95",
                    on && "bg-sunken text-ink",
                  )}
                >
                  <Icon size={14} strokeWidth={1.75} />
                </button>
              );
            })}
          </div>
        )}
      </div>
    </article>
  );
}
