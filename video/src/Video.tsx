import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame } from "remotion";
import "./app.css";
import { Ask } from "./scenes/Ask";
import { Formats } from "./scenes/Formats";
import { Outro } from "./scenes/Outro";
import { Pipeline } from "./scenes/Pipeline";
import { Proof } from "./scenes/Proof";
import { c } from "./theme";
import tl from "./timeline.json";

const SCENES = [
  { key: "ask", C: Ask },
  { key: "formats", C: Formats },
  { key: "pipeline", C: Pipeline },
  { key: "proof", C: Proof },
  { key: "outro", C: Outro },
] as const;

export const TOTAL_FRAMES = tl.total;

function Scenes() {
  return (
    <>
      {SCENES.map(({ key, C }) => {
        const [from, to] = tl.scenes[key];
        return (
          <Sequence key={key} from={from} durationInFrames={to - from}>
            <C />
          </Sequence>
        );
      })}
    </>
  );
}

export function LedgerLensVideo() {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: c.stage }}>
      {/* Frame 0 is the poster (a settled frame), so every platform's thumbnail shows it. */}
      {frame === 0 ? (
        <Sequence from={-tl.poster}>
          <Scenes />
        </Sequence>
      ) : (
        <Scenes />
      )}
      <Audio src={staticFile("soundtrack.wav")} />
    </AbsoluteFill>
  );
}
