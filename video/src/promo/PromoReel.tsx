import React from "react";
import { AbsoluteFill, Audio, interpolate, spring, staticFile, useCurrentFrame } from "remotion";
import "../app.css";
import { LensMark } from "../kit";
import { mono, sans } from "../theme";
import { Device, SCREEN_H, SCREEN_W } from "../phone/Device";
import { AskScreen, Dashboard, NOTIFS, ProofScreen, ease, popAmount, type Layer } from "./screens";
import tl from "./timeline.json";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const outCubic = (x: number) => 1 - Math.pow(1 - x, 3);
const inOut = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
const lerp = (f: number, [a, b]: number[], from: number, to: number, e = inOut) => interpolate(f, [a, b], [from, to], { ...clamp, easing: e });

// Phone geometry (stage px)
const SCALE = 1.7;
const BEZEL = 13;
const PHONE_W = (SCREEN_W + BEZEL * 2) * SCALE;
const PHONE_H = (SCREEN_H + BEZEL * 2) * SCALE;
const PHONE_LEFT = (1080 - PHONE_W) / 2;
const PHONE_TOP = 360;
// Hero card centre in stage px, for the push-in
const HERO = { x: 540, y: PHONE_TOP + (BEZEL + 180) * SCALE };

const NIGHT = "#010111";
const STAGE_BG = [
  "radial-gradient(ellipse 85% 42% at 50% 0%, #0a62cf 0%, #0749a8 32%, rgba(1,34,91,0) 72%)",
  "radial-gradient(ellipse 120% 80% at 50% 45%, #01225b 0%, #01204f 55%, #001232 100%)",
].join(", ");

/* ---------------- screens inside the phone ---------------- */

function Screens({ f, layer }: { f: number; layer: Layer }) {
  const toAsk = lerp(f, tl.toAsk, 0, 1, outCubic);
  const toProof = lerp(f, tl.toProof, 0, 1, outCubic);
  const W = SCREEN_W;
  const at = (x: number, child: React.ReactNode) => (
    <div className="bg-bg" style={{ position: "absolute", inset: 0, transform: `translateX(${x}px)` }}>{child}</div>
  );
  return (
    <div className={`font-sans text-ink ${layer === "pop" ? "pop-layer" : ""}`} style={{ position: "absolute", inset: 0, fontSize: 14 }}>
      {toAsk < 1 && at(-W * 0.3 * toAsk, <Dashboard f={f} layer={layer} />)}
      {toAsk > 0 && toProof < 1 && at(W * (1 - toAsk) - W * 0.3 * toProof, <AskScreen f={f} layer={layer} />)}
      {toProof > 0 && at(W * (1 - toProof), <ProofScreen f={f} layer={layer} />)}
    </div>
  );
}

/* ---------------- stage pieces ---------------- */

function Caption({ f, lines, from, to, lower }: { f: number; lines: string[]; from: number; to: number; lower?: boolean }) {
  if (f < from || f >= to) return null;
  const out = interpolate(f, [to - 6, to], [1, 0], clamp);
  let w = 0;
  return (
    <div
      style={{
        position: "absolute",
        left: 76,
        right: 60,
        top: lower ? 1400 : 108,
        color: "#F4F7FF",
        fontWeight: 900,
        fontSize: 80,
        lineHeight: 0.95,
        letterSpacing: "-0.012em",
        textTransform: "uppercase",
        opacity: out,
        textShadow: "0 6px 30px rgba(0,10,40,0.35)",
        zIndex: 20,
      }}
    >
      {lines.map((line, li) => (
        <div key={li}>
          {line.split(" ").map((word, wi) => {
            const p = interpolate(f - from - w++ * 2, [0, 7], [0, 1], { ...clamp, easing: outCubic });
            return (
              <span key={wi} style={{ display: "inline-block", marginRight: "0.22em", opacity: p, transform: `translateY(${(1 - p) * 20}px)` }}>
                {word}
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function Notifications({ f }: { f: number }) {
  const out = ease(f, tl.notifOut, tl.notifOut + 10);
  if (f < tl.notifs[0] || out >= 1) return null;
  const arrived = tl.notifs.filter((t) => f >= t).length;
  return (
    <div style={{ position: "absolute", left: 72, right: 72, top: 96, zIndex: 15, transform: `translateY(${-out * 360}px)`, opacity: 1 - out }}>
      {tl.notifs.map((at, i) => {
        if (f < at) return null;
        const inn = spring({ frame: f - at, fps: 30, config: { damping: 16, mass: 0.7, stiffness: 160 } });
        const depth = arrived - 1 - i; // 0 = newest
        const a = NOTIFS[i];
        return (
          <div
            key={a.bank}
            style={{
              position: "absolute",
              left: 0,
              right: 0,
              top: 0,
              zIndex: 10 - depth,
              transform: `translateY(${(1 - inn) * -220 + depth * 22}px) scale(${1 - depth * 0.05})`,
              opacity: depth > 1 ? 0.0 : 1 - depth * 0.15,
              transformOrigin: "50% 0%",
            }}
          >
            <div
              className="font-sans"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 22,
                background: "#fcfafc",
                borderRadius: 34,
                padding: "22px 26px",
                boxShadow: "0 18px 40px rgba(0,10,40,0.35)",
                color: "#0f1217",
              }}
            >
              <div style={{ width: 68, height: 68, borderRadius: 18, background: "#0f1217", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <LensMark size={50} />
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 20, letterSpacing: "0.06em", color: "#646b77", fontWeight: 600 }}>
                  <span>LEDGER LENS</span>
                  <span style={{ letterSpacing: 0 }}>now</span>
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, marginTop: 2 }}>{a.bank} statement verified</div>
                <div style={{ fontSize: 24, color: "#454c58", marginTop: 1 }}>{a.rows} rows match the running balance</div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function Pill({ f }: { f: number }) {
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 1866, display: "flex", justifyContent: "center", zIndex: 12, opacity: ease(f, tl.wake[0], tl.wake[1] + 6) }}>
      <span style={{ background: "rgba(150,160,180,0.35)", color: "#fff", fontSize: 22, padding: "7px 18px", borderRadius: 999, fontWeight: 500 }}>
        Sample workspace: Meridian Capital
      </span>
    </div>
  );
}

function AppIcon({ size }: { size: number }) {
  return (
    <div style={{ width: size, height: size, borderRadius: size * 0.24, background: "#f7f6fc", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 0 ${size * 0.3}px rgba(150,190,255,0.55), 0 0 ${size * 0.08}px rgba(255,255,255,0.6)` }}>
      <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 24 24" fill="none">
        <circle cx="10.5" cy="10" r="5.6" stroke="#0f1b5c" strokeWidth="2.3" />
        <path d="M5 19h14" stroke="#0f1b5c" strokeOpacity="0.35" strokeWidth="1.8" strokeLinecap="round" />
        <path d="m14.6 14.2 4.2 4.2" stroke="#2b45d4" strokeWidth="2.6" strokeLinecap="round" />
      </svg>
    </div>
  );
}

/* ---------------- shots ---------------- */

function Sting({ f }: { f: number }) {
  const p = ease(f, 0, 9);
  return (
    <AbsoluteFill style={{ background: NIGHT, alignItems: "center", justifyContent: "center" }}>
      <div style={{ opacity: p, transform: `scale(${0.88 + 0.12 * p})` }}>
        <AppIcon size={238} />
      </div>
    </AbsoluteFill>
  );
}

function EndCard({ f }: { f: number }) {
  const s = f - tl.endCut;
  const p = ease(s, 0, 10);
  const line = ease(s, 8, 18);
  return (
    <AbsoluteFill style={{ background: NIGHT, alignItems: "center", justifyContent: "center", color: "#fff" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 34, opacity: p, transform: `scale(${0.9 + 0.1 * p})` }}>
        <AppIcon size={150} />
        <span style={{ fontSize: 92, fontWeight: 800, letterSpacing: "-0.045em" }}>Ledger Lens</span>
      </div>
      <div style={{ marginTop: 34, fontSize: 34, color: "rgba(255,255,255,0.7)", opacity: line, transform: `translateY(${(1 - line) * 12}px)` }}>
        Bank statements you can question.
      </div>
    </AbsoluteFill>
  );
}

function Stage({ f }: { f: number }) {
  // Phone pose
  const rise = lerp(f, tl.rise, 1, 0, outCubic);
  let rotY = lerp(f, tl.rise, -14, -8, outCubic) + lerp(f, tl.settle, 0, 8);
  let rotZ = lerp(f, tl.rise, 6, 3, outCubic) + lerp(f, tl.settle, 0, -3);
  let scale = lerp(f, tl.rise, 0.92, 1, outCubic) + lerp(f, tl.settle, 0, 0.05) - lerp(f, tl.pullBack, 0, 0.05);
  rotY += lerp(f, tl.toAsk, 0, -12) + lerp(f, tl.toProof, 0, 24) + lerp(f, tl.sheet, 0, -12);
  rotZ += lerp(f, tl.toAsk, 0, -3) + lerp(f, tl.toProof, 0, 6) + lerp(f, tl.sheet, 0, -6);
  if (f >= tl.glance.start) rotZ += Math.sin((f - tl.glance.start) / 22) * 0.5; // the faint sway
  scale += lerp(f, [tl.glance.start, tl.glance.end], 0, 0.04, (x) => x) - lerp(f, tl.toAsk, 0, 0.04);

  // Camera push to the hero card and back
  const push = lerp(f, tl.push, 0, 1, (x) => 1 - Math.pow(1 - x, 4)) * (1 - lerp(f, tl.pullBack, 0, 1));
  const camScale = 1 + 0.32 * push;
  const camY = 130 * push;

  // Screen state
  const wake = ease(f, tl.wake[0], tl.wake[1]);
  const heroP = popAmount(f, tl.heroPop[0], tl.heroPop[1], tl.heroPop[1] + 14);
  const blur = Math.min(1, heroP * 1.2) * (f < tl.pullBack[1] ? 1 : 0);

  return (
    <AbsoluteFill style={{ background: STAGE_BG, overflow: "hidden" }}>
      {tl.captions.map((cap) => (
        <Caption key={cap.from} f={f} {...cap} />
      ))}
      <Notifications f={f} />
      <Pill f={f} />

      <div style={{ position: "absolute", inset: 0, perspective: 2200, transform: `translateY(${camY}px) scale(${camScale})`, transformOrigin: `${HERO.x}px ${HERO.y}px` }}>
        <div
          style={{
            position: "absolute",
            left: PHONE_LEFT,
            top: PHONE_TOP,
            width: PHONE_W,
            height: PHONE_H,
            transformOrigin: "50% 50%",
            transform: `translateY(${rise * 1150}px) rotateY(${rotY}deg) rotateZ(${rotZ}deg) scale(${scale})`,
          }}
        >
          <div style={{ transform: `scale(${SCALE})`, transformOrigin: "top left", width: SCREEN_W + BEZEL * 2 }}>
            <Device>
              <div style={{ position: "absolute", inset: 0, background: "#000", opacity: 1 - wake, zIndex: 30 }} />
              {wake > 0 && (
                <div style={{ position: "absolute", inset: 0, filter: blur ? `blur(${10 * blur}px)` : undefined }}>
                  <Screens f={f} layer="base" />
                  <div style={{ position: "absolute", inset: 0, background: `rgba(146,146,150,${0.42 * blur})` }} />
                </div>
              )}
              <div style={{ position: "absolute", inset: 0, background: "#fff", opacity: interpolate(f, [tl.wake[0], tl.wake[0] + 2, tl.wake[1]], [0, 0.35, 0], clamp), zIndex: 31 }} />
            </Device>
            {/* Unclipped pop layer, same layout as the screen */}
            <div style={{ position: "absolute", left: BEZEL, top: BEZEL, width: SCREEN_W, height: SCREEN_H, pointerEvents: "none" }}>
              {wake > 0 && <Screens f={f} layer="pop" />}
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
}

function Scene({ f }: { f: number }) {
  return (
    <AbsoluteFill style={{ ["--font-geist" as string]: sans, ["--font-geist-mono" as string]: mono, fontFamily: sans }}>
      {f < tl.sting[1] ? <Sting f={f} /> : f < tl.endCut ? <Stage f={f} /> : <EndCard f={f} />}
    </AbsoluteFill>
  );
}

export const PROMO_TOTAL = tl.total;

export function PromoReel() {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      {/* Frame 0 is the poster: the strongest settled frame. */}
      <Scene f={f === 0 ? tl.poster : f} />
      <Audio src={staticFile("promo-soundtrack.wav")} />
    </AbsoluteFill>
  );
}
