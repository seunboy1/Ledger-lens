import React from "react";
import { AbsoluteFill, Audio, interpolate, spring, staticFile, useCurrentFrame } from "remotion";
import "../app.css";
import { LensMark } from "../kit";
import { mono, sans } from "../theme";
import { Device, SCREEN_H, SCREEN_W } from "./Device";
import { AskScreen, Dashboard, Notifications, ProofScreen } from "./screens";
import tl from "./timeline.json";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const PHONE_SCALE = 1.62;

/** Caption above the phone: bold, white, words rising in. */
function Caption({ f, at, text, until }: { f: number; at: number; text: string; until?: number }) {
  if (f < at || (until !== undefined && f >= until)) return null;
  const out = until !== undefined ? interpolate(f, [until - 6, until], [1, 0], clamp) : 1;
  return (
    <div
      style={{
        position: "absolute",
        top: 150,
        left: 70,
        right: 70,
        textAlign: "center",
        fontSize: 86,
        fontWeight: 800,
        lineHeight: 1.0,
        letterSpacing: "-0.04em",
        color: "#fff",
        textTransform: "uppercase",
        opacity: out,
      }}
    >
      {text.split(" ").map((w, i) => {
        const p = interpolate(f - at - i * 3, [0, 9], [0, 1], clamp);
        return (
          <span key={i} style={{ display: "inline-block", margin: "0 0.12em", opacity: p, transform: `translateY(${(1 - p) * 24}px)` }}>
            {w}
          </span>
        );
      })}
    </div>
  );
}

/** Horizontal screen push, like navigating inside the app. */
function slide(f: number, at: number) {
  return interpolate(f, [at, at + 14], [0, 1], { ...clamp, easing: (x) => 1 - Math.pow(1 - x, 3) });
}

function Screens({ f }: { f: number }) {
  const toAsk = slide(f, tl.ask.start);
  const toProof = slide(f, tl.proof.start);
  const W = SCREEN_W;
  const layer = (x: number, child: React.ReactNode) => (
    <div style={{ position: "absolute", inset: 0, transform: `translateX(${x}px)` }}>{child}</div>
  );
  return (
    <div className="font-sans text-ink" style={{ position: "absolute", inset: 0, fontSize: 14 }}>
      {toAsk < 1 && layer(-W * 0.35 * toAsk, <Dashboard f={f} />)}
      {toAsk > 0 && toProof < 1 && layer(W * (1 - toAsk) - W * 0.35 * toProof, <AskScreen f={f} />)}
      {toProof > 0 && layer(W * (1 - toProof), <ProofScreen f={f} />)}
      {toAsk < 1 && <Notifications f={f} />}
    </div>
  );
}

function Scene({ f }: { f: number }) {
  const enter = spring({ frame: f - tl.intro.start, fps: 30, config: { damping: 20, mass: 1.1 } });
  const zoomIn = interpolate(f, [tl.glance.start, tl.glance.zoomEnd], [0, 1], clamp);
  const zoomOut = interpolate(f, [tl.ask.start, tl.ask.start + 18], [0, 1], { ...clamp, easing: (x) => 1 - Math.pow(1 - x, 3) });
  const zoom = 1 + 0.06 * zoomIn * (1 - zoomOut);
  const fadeOut = interpolate(f, [tl.outro.fadeStart, tl.total], [1, 0], clamp);
  const deviceH = (SCREEN_H + 26) * PHONE_SCALE;
  const deviceW = (SCREEN_W + 26) * PHONE_SCALE;

  return (
    <AbsoluteFill
      style={{
        ["--font-geist" as string]: sans,
        ["--font-geist-mono" as string]: mono,
        fontFamily: sans,
        background: "linear-gradient(165deg, #2f52ff 0%, #1631d6 38%, #0b1c8f 72%, #071460 100%)",
        overflow: "hidden",
        opacity: fadeOut,
      }}
    >
      {/* electric glow behind the phone */}
      <div
        style={{
          position: "absolute",
          left: 540 - 520,
          top: 1120 - 620,
          width: 1040,
          height: 1240,
          borderRadius: "50%",
          background: "radial-gradient(closest-side, rgba(120,160,255,0.75), rgba(80,120,255,0.25) 55%, transparent)",
          filter: "blur(30px)",
          opacity: 0.85,
        }}
      />

      <Caption f={f} at={tl.notifs.caption} until={tl.glance.start} text="Every statement. Verified." />
      <Caption f={f} at={tl.glance.caption} until={tl.ask.start} text="Every account, at a glance." />
      <Caption f={f} at={tl.ask.caption} until={tl.proof.start} text="Ask it anything." />
      <Caption f={f} at={tl.proof.caption} until={tl.outro.start} text="Every number, checked." />

      {f >= tl.outro.start && (
        <div style={{ position: "absolute", top: 120, left: 0, right: 0, textAlign: "center", color: "#fff" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 22,
              opacity: interpolate(f, [tl.outro.caption, tl.outro.caption + 10], [0, 1], clamp),
              transform: `translateY(${(1 - interpolate(f, [tl.outro.caption, tl.outro.caption + 12], [0, 1], clamp)) * 20}px)`,
            }}
          >
            <LensMark size={88} />
            <span style={{ fontSize: 96, fontWeight: 800, letterSpacing: "-0.045em" }}>Ledger Lens</span>
          </div>
          <div style={{ marginTop: 18, fontSize: 38, opacity: interpolate(f, [tl.outro.caption + 10, tl.outro.caption + 20], [0, 0.9], clamp) }}>
            Bank statements you can question.
          </div>
        </div>
      )}

      <div
        style={{
          position: "absolute",
          left: (1080 - deviceW) / 2,
          top: 440,
          width: deviceW,
          height: deviceH,
          transformOrigin: "50% 70%",
          transform: `translateY(${(1 - enter) * 1500}px) rotate(${(1 - enter) * 6}deg) scale(${zoom})`,
        }}
      >
        <div style={{ transform: `scale(${PHONE_SCALE})`, transformOrigin: "top left" }}>
          <Device>
            <Screens f={f} />
          </Device>
        </div>
      </div>
    </AbsoluteFill>
  );
}

export const PHONE_TOTAL = tl.total;

export function PhoneReel() {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      {/* Frame 0 is the poster: a settled, readable frame for every platform's thumbnail. */}
      <Scene f={f === 0 ? tl.poster : f} />
      <Audio src={staticFile("phone-soundtrack.wav")} />
    </AbsoluteFill>
  );
}
