import React from "react";
import { Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import statements from "../data/statements.json";
import tl from "../timeline.json";
import { AppScale, Caption, Stage, naira, useEnter, useLayout, useSceneFade } from "../kit";
import { c } from "../theme";

const [S0, S1] = tl.scenes.formats;
const t = tl.formats;
const RAW_LABEL: Record<string, string> = { kestrel: "Debit column", harbour: "negative Amount", oakline: "DR" };

export function Formats() {
  const frame = useCurrentFrame();
  const { tall, captionTop, captionSize, contentTop, scale } = useLayout();
  const opacity = useSceneFade(S1 - S0);
  const width = 936;
  const left = (1080 - width) / 2;
  const stored = useEnter(t.stored, 18);
  const dim = interpolate(frame, [t.stored - 6, t.stored + 6], [1, 0.45], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const label = tall ? 50 : 42;
  let y = contentTop;
  const cards = statements.map((s, i) => {
    const h = (s.height / s.width) * width;
    const top = y;
    y += label + h + (tall ? 44 : 26);
    return { s, i, h, top };
  });

  return (
    <Stage opacity={opacity}>
      <Caption text="Any bank. Any layout." top={captionTop} size={captionSize} accentWords={["Any", "layout"]} />
      {cards.map(({ s, i, h, top }) => {
        const p = useEnter(t.cards[i]);
        const mark = interpolate(frame, [t.cards[i] + 10, t.cards[i] + 18], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const k = width / s.width;
        return (
          <React.Fragment key={s.key}>
          <div
            style={{
              position: "absolute",
              left,
              top,
              fontSize: tall ? 32 : 28,
              fontWeight: 600,
              color: c.white,
              opacity: p * dim,
              transform: `translateY(${(1 - p) * 40}px)`,
            }}
          >
            {s.bank}
          </div>
          <div
            style={{
              position: "absolute",
              left,
              top: top + label,
              width,
              height: h,
              borderRadius: 14,
              overflow: "hidden",
              background: "#fff",
              opacity: p * dim,
              transform: `translateY(${(1 - p) * 40}px)`,
              boxShadow: "0 20px 60px rgba(0,0,0,0.45)",
            }}
          >
            <Img src={staticFile(s.image)} style={{ width, height: h, display: "block" }} />
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                top: s.highlight.y * k,
                height: s.highlight.h * k,
                background: "rgba(43,69,212,0.14)",
                outline: "3px solid #2b45d4",
                opacity: mark,
              }}
            />
          </div>
          </React.Fragment>
        );
      })}

      <AppScale
        scale={scale}
        width={tall ? 492 : 604}
        style={{ left: 72, top: y + (tall ? 10 : 0), opacity: stored, transform: `translateY(${(1 - stored) * 30}px)` }}
      >
        <div className="rounded-[16px] border border-line bg-surface shadow-[0_30px_80px_rgba(0,0,0,0.5)]">
          <p className="border-b border-line px-4 py-2.5 text-[13px] font-medium text-ink-soft">Stored as one schema</p>
          {statements.map((s) => (
            <div key={s.key} className="flex items-start justify-between gap-3 border-t border-line px-4 py-2.5 first-of-type:border-t-0">
              <div className="min-w-0">
                <p className="truncate text-[13px]">{s.row.description}</p>
                <p className="text-[12px] text-muted">
                  {s.row.date}, {s.bank}
                </p>
              </div>
              <div className="shrink-0 text-right">
                <p className="num text-[13px] font-medium text-debit">−{naira(s.row.amount)}</p>
                <p className="text-[12px] text-muted">
                  Debit, printed <span className="num">{RAW_LABEL[s.key]}</span>
                </p>
              </div>
            </div>
          ))}
        </div>
      </AppScale>
    </Stage>
  );
}
