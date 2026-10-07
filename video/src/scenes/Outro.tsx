import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import tl from "../timeline.json";
import { LensMark, Stage, useEnter, useLayout } from "../kit";
import { c } from "../theme";

const t = tl.outro;

export function Outro() {
  const frame = useCurrentFrame();
  const { tall } = useLayout();
  const mark = useEnter(t.mark, 14);
  const fade = (d: number) => interpolate(frame, [d, d + 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <Stage>
      <div style={{ position: "absolute", left: 72, right: 72, top: tall ? 660 : 380, display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>
        <div style={{ transform: `scale(${mark})` }}>
          <LensMark size={140} />
        </div>
        <div style={{ marginTop: 40, fontSize: 104, fontWeight: 800, letterSpacing: "-0.045em", opacity: fade(t.name) }}>Ledger Lens</div>
        <div style={{ marginTop: 24, fontSize: 42, lineHeight: 1.3, color: c.dim, opacity: fade(t.line) }}>
          Bank statements you can question.
          <br />
          <span style={{ color: c.white }}>Answers you can check.</span>
        </div>
        <div style={{ marginTop: 64, fontSize: 30, color: "rgba(244,245,247,0.55)", opacity: fade(t.line + 14) }}>
          Demo link in the post. Built by Oluwaseun Adeyo.
        </div>
      </div>
    </Stage>
  );
}
