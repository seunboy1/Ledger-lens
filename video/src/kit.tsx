import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { c, mono, sans } from "./theme";

/** 0 → 1 spring that starts at `delay` frames. */
export function useEnter(delay = 0, damping = 200) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping, mass: 0.9 } });
}

/** Fade the whole scene out over its last frames. */
export function useSceneFade(duration: number, out = 8) {
  const frame = useCurrentFrame();
  return interpolate(frame, [0, 6, duration - out, duration], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
}

export function useTall() {
  const { height, width } = useVideoConfig();
  return height / width > 1.5;
}

export function Stage({ children, opacity = 1 }: { children: React.ReactNode; opacity?: number }) {
  return (
    <div
      style={{
        // Feed the app's components the same font variables next/font sets.
        ["--font-geist" as string]: sans,
        ["--font-geist-mono" as string]: mono,
        position: "absolute",
        inset: 0,
        background: `radial-gradient(120% 70% at 50% -10%, ${c.stageGlow}, transparent 60%), ${c.stage}`,
        fontFamily: sans,
        color: c.white,
        opacity,
        overflow: "hidden",
      }}
    >
      {children}
    </div>
  );
}

/** Big punchy caption, like a reel title card. Words rise in one by one. */
export function Caption({ text, delay = 0, top, size = 82, accentWords = [] }: { text: string; delay?: number; top: number; size?: number; accentWords?: string[] }) {
  const frame = useCurrentFrame();
  const words = text.split(" ");
  return (
    <div style={{ position: "absolute", top, left: 72, right: 72, fontSize: size, fontWeight: 800, letterSpacing: "-0.035em", lineHeight: 1.02, textTransform: "uppercase" }}>
      {words.map((w, i) => {
        const p = interpolate(frame - delay - i * 3, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });
        const accent = accentWords.includes(w.replace(/[.,]/g, ""));
        return (
          <span key={i} style={{ display: "inline-block", marginRight: "0.24em", opacity: p, transform: `translateY(${(1 - p) * 26}px)`, color: accent ? "#8fa0ff" : c.white }}>
            {w}
          </span>
        );
      })}
    </div>
  );
}

export function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div
      style={{
        background: c.surface,
        color: c.ink,
        borderRadius: 28,
        border: `1px solid ${c.border}`,
        boxShadow: "0 2px 6px rgba(0,0,0,0.25), 0 40px 90px rgba(0,0,0,0.45)",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

export function Mono({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <span style={{ fontFamily: mono, fontVariantNumeric: "tabular-nums", letterSpacing: "-0.01em", ...style }}>{children}</span>;
}

export function naira(v: number) {
  return `₦${v.toLocaleString("en-NG", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function LensMark({ size = 64 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <rect x="1" y="1" width="22" height="22" rx="6" fill={c.white} />
      <path d="M6 16.5h12" stroke={c.stage} strokeOpacity="0.45" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="11" cy="10.5" r="4" stroke={c.stage} strokeWidth="1.75" />
      <path d="m14 13.5 3 3" stroke={c.accent} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

/** Renders real app UI at its native CSS size, scaled up crisply for video. */
export function AppScale({ scale, width, children, style }: { scale: number; width: number; children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ position: "absolute", ...style }}>
      <div className="font-sans text-ink" style={{ width, transform: `scale(${scale})`, transformOrigin: "top left", fontSize: 14 }}>
        {children}
      </div>
    </div>
  );
}

export function useLayout() {
  const tall = useTall();
  return {
    tall,
    captionTop: tall ? 250 : 90,
    captionSize: tall ? 82 : 66,
    contentTop: tall ? 560 : 300,
    scale: tall ? 1.9 : 1.55,
  };
}
