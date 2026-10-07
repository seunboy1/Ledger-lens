import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { EvidencePanel } from "@/components/ask/EvidencePanel";
import { MessageView } from "@/components/ask/MessageView";
import type { Message } from "@/types/api";
import data from "../data/ask.json";
import tl from "../timeline.json";
import { AppScale, Caption, Stage, naira, useEnter, useLayout, useSceneFade } from "../kit";

const [S0, S1] = tl.scenes.ask;
const t = tl.ask;
const user = data.user_message as unknown as Message;
const answer = data.assistant_message as unknown as Message;
const TOTAL = 480800;

export function Ask() {
  const frame = useCurrentFrame();
  const { tall, captionTop, captionSize, contentTop, scale } = useLayout();
  const opacity = useSceneFade(S1 - S0);
  const q = user.content;
  const typed = Math.floor(interpolate(frame, [t.typeStart, t.typeEnd], [0, q.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const sent = frame >= t.send;
  const answerIn = useEnter(t.answer);
  const evidenceIn = useEnter(t.evidence, 18);
  const count = interpolate(frame, [t.answer + 4, t.countEnd], [0, TOTAL], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const live: Message = {
    ...answer,
    kpis: answer.kpis.map((k) => (k.label === "Debits" ? { ...k, value: naira(Math.round(count)) } : k)),
  };
  const swapped = frame >= t.caption2;

  return (
    <Stage opacity={opacity}>
      {!swapped && <Caption text="Ask your bank statements anything." top={captionTop} size={captionSize} accentWords={["anything"]} />}
      {swapped && <Caption text="Every answer shows its rows." top={captionTop} size={captionSize} accentWords={["rows"]} />}

      <AppScale scale={scale} width={500} style={{ left: tall ? 65 : 92, top: contentTop }}>
        <div className="overflow-hidden rounded-[16px] border border-line bg-bg shadow-[0_30px_80px_rgba(0,0,0,0.45)]">
          <div className="flex h-12 items-center border-b border-line bg-bg px-5">
            <span className="truncate text-[15px] font-semibold tracking-tight">{sent ? "How much did I spend at Kestrel in July" : "Ask about your statements"}</span>
          </div>
          <div className="flex flex-col gap-6 px-5 py-5" style={{ minHeight: 300 }}>
            {sent && <MessageView message={user} />}
            {frame >= t.answer && (
              <div style={{ opacity: answerIn, transform: `translateY(${(1 - answerIn) * 10}px)` }}>
                <MessageView message={live} selected={frame >= t.evidence} onShowEvidence={() => {}} onFeedback={() => {}} />
              </div>
            )}
          </div>
          <div className="border-t border-line bg-bg px-4 pb-4 pt-3">
            <div className={`flex items-end gap-2 rounded-[var(--radius-panel)] border bg-surface p-2 pl-3.5 ${sent ? "border-line-strong" : "border-accent"}`}>
              <span className={`flex-1 py-1.5 text-[14.5px] leading-6 ${typed && !sent ? "text-ink" : "text-muted"}`}>
                {!sent && typed ? q.slice(0, typed) : "Ask about totals, balances, merchants or patterns"}
                {!sent && <span style={{ opacity: Math.floor(frame / 8) % 2 ? 0 : 1 }} className="text-accent">|</span>}
              </span>
              <span className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-ctl)] bg-ink text-bg" style={{ opacity: typed && !sent ? 1 : 0.3 }}>
                ↑
              </span>
            </div>
          </div>
        </div>
      </AppScale>

      {frame >= t.evidence && (
        <AppScale
          scale={scale}
          width={380}
          style={{
            left: tall ? 330 : 440,
            top: contentTop + (tall ? 440 : 372),
            opacity: evidenceIn,
            transform: `translateX(${(1 - evidenceIn) * 260}px)`,
          }}
        >
          <div className="overflow-hidden rounded-[16px] border-2 border-accent bg-surface shadow-[0_30px_80px_rgba(0,0,0,0.5)]" style={{ height: tall ? 410 : 370 }}>
            <EvidencePanel evidence={answer.evidence} />
          </div>
        </AppScale>
      )}
    </Stage>
  );
}
