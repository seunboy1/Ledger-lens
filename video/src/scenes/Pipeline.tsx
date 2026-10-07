import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import tl from "../timeline.json";
import { Caption, Mono, Stage, useEnter, useLayout, useSceneFade } from "../kit";
import { c } from "../theme";

const [S0, S1] = tl.scenes.pipeline;
const t = tl.pipeline;

const STEPS = [
  { name: "Upload", note: "PDF straight to storage" },
  { name: "Fingerprint", note: "Hash of the header row" },
  { name: "Learn layout", note: "Only for a layout never seen" },
  { name: "Parse", note: "Plain code, no model" },
  { name: "Reconcile", note: "Every row vs. the running balance" },
];

export function Pipeline() {
  const frame = useCurrentFrame();
  const { tall, captionTop, captionSize, contentTop } = useLayout();
  const opacity = useSceneFade(S1 - S0);
  const rowH = tall ? 150 : 112;
  const lit = t.nodes.filter((n) => frame >= n).length;
  const rail = interpolate(frame, [t.nodes[0], t.nodes[4]], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const rows = Math.round(interpolate(frame, [t.counterStart, t.counterEnd], [0, 212], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  const stats = useEnter(t.counterStart);

  return (
    <Stage opacity={opacity}>
      <Caption text="Learned once. Then plain code." top={captionTop} size={captionSize} accentWords={["once", "code"]} />
      <div style={{ position: "absolute", left: 110, top: contentTop + 28, width: 4, height: rowH * 4, background: "rgba(244,245,247,0.14)", borderRadius: 2 }} />
      <div style={{ position: "absolute", left: 110, top: contentTop + 28, width: 4, height: rowH * 4 * rail, background: "#7b8ffa", borderRadius: 2 }} />
      {STEPS.map((s, i) => {
        const on = i < lit;
        const p = interpolate(frame, [t.nodes[i], t.nodes[i] + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <div key={s.name} style={{ position: "absolute", left: 90, right: 72, top: contentTop + i * rowH, display: "flex", gap: 40 }}>
            <div
              style={{
                width: 44,
                height: 44,
                marginTop: 6,
                borderRadius: 999,
                flexShrink: 0,
                background: on ? "#7b8ffa" : c.stage,
                border: `4px solid ${on ? "#7b8ffa" : "rgba(244,245,247,0.25)"}`,
                boxShadow: on ? `0 0 0 ${10 * p}px rgba(123,143,250,0.18)` : "none",
              }}
            />
            <div style={{ opacity: 0.35 + p * 0.65 }}>
              <div style={{ fontSize: tall ? 50 : 44, fontWeight: 700, letterSpacing: "-0.03em" }}>{s.name}</div>
              <div style={{ fontSize: tall ? 30 : 27, color: c.dim, marginTop: 2 }}>{s.note}</div>
            </div>
          </div>
        );
      })}
      <div
        style={{
          position: "absolute",
          left: 72,
          right: 72,
          top: contentTop + rowH * 5 + (tall ? 40 : 30),
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 24,
          opacity: stats,
          transform: `translateY(${(1 - stats) * 24}px)`,
        }}
      >
        {[
          { label: "Rows parsed by code", value: rows.toLocaleString() },
          { label: "Bank layouts learned", value: "3" },
        ].map((st) => (
          <div key={st.label} style={{ background: "rgba(244,245,247,0.06)", border: "1px solid rgba(244,245,247,0.12)", borderRadius: 24, padding: "22px 28px" }}>
            <div style={{ fontSize: 26, color: c.dim }}>{st.label}</div>
            <Mono style={{ display: "block", fontSize: 60, fontWeight: 500, marginTop: 4 }}>{st.value}</Mono>
          </div>
        ))}
      </div>
    </Stage>
  );
}
