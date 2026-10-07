"""
Original soundtrack for the Ledger Lens launch video, synthesized from scratch.

One piece in D major at 96 BPM (D, Bm, G, A). The sound effects are tuned to
the same key, placed from src/timeline.json so they land on the on-screen
events, and share the music's reverb so they sit inside the track rather than
on top of it.

    python scripts/soundtrack.py   ->  public/soundtrack.wav
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "src/timeline.json").read_text())
ASK = json.loads((ROOT / "src/data/ask.json").read_text())

SR = 44100
FPS = TL["fps"]
DUR = TL["total"] / FPS
N = int(DUR * SR) + SR // 2
BEAT = 60 / 96
BAR = BEAT * 4
rng = np.random.default_rng(7)


def f(frame: float) -> float:
    return frame / FPS


def scene(name: str) -> float:
    return f(TL["scenes"][name][0])


def hz(note: str) -> float:
    names = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}
    name, octave = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((names[name] + 12 * (octave + 1) - 69) / 12)


dry = np.zeros((N, 2))
send = np.zeros((N, 2))  # reverb bus


def place(buf: np.ndarray, start: float, sig: np.ndarray, pan: float = 0.0, gain: float = 1.0) -> None:
    i = int(start * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    left, right = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
    buf[i : i + len(sig), 0] += sig * left
    buf[i : i + len(sig), 1] += sig * right


def lowpass(x: np.ndarray, cutoff: float) -> np.ndarray:
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # short signals only
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def pluck(freq: float, length: float = 0.9, decay: float = 7.0, bright: float = 0.35) -> np.ndarray:
    t = np.arange(int(length * SR)) / SR
    sig = sum((bright**k) * np.sin(2 * np.pi * freq * (k + 1) * t) for k in range(5))
    env = np.exp(-t * decay) * np.minimum(1, t / 0.004)
    return sig * env


def bell(freq: float, length: float = 1.6) -> np.ndarray:
    t = np.arange(int(length * SR)) / SR
    partials = [(1.0, 1.0, 3.2), (2.0, 0.35, 5.0), (2.76, 0.18, 7.0), (5.4, 0.06, 10.0)]
    sig = sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * d) for r, a, d in partials)
    return sig * np.minimum(1, t / 0.003)


def noise_burst(length: float, decay: float, hp: int = 2) -> np.ndarray:
    n = rng.standard_normal(int(length * SR))
    for _ in range(hp):
        n = np.diff(n, prepend=0)  # crude high-pass: keeps it airy, not hissy
    t = np.arange(len(n)) / SR
    return n * np.exp(-t * decay)


def whoosh(length: float = 0.55) -> np.ndarray:
    n = rng.standard_normal(int(length * SR))
    t = np.arange(len(n)) / SR
    env = np.sin(np.pi * np.clip(t / length, 0, 1)) ** 2
    return lowpass(n, 1400) * env


# --- harmony ------------------------------------------------------------------
CHORDS = {
    "D": ["D4", "F#4", "A4"],
    "Bm": ["B3", "D4", "F#4"],
    "G": ["G3", "B3", "D4"],
    "A": ["A3", "C#4", "E4"],
}
ROOTS = {"D": "D2", "Bm": "B1", "G": "G1", "A": "A1"}
progression = ["D", "Bm", "G", "A"]
outro = scene("outro")
segments = []
t0 = 0.0
k = 0
while t0 < outro:
    end = min(t0 + BAR, outro)
    segments.append((t0, end, progression[k % 4]))
    t0, k = end, k + 1
segments.append((outro, DUR + 0.4, "D"))

# Pad: soft detuned additive voices, slow attack, overlapping release.
for start, end, chord in segments:
    length = end - start + 0.6
    t = np.arange(int(length * SR)) / SR
    env = np.minimum(1, t / 0.35) * np.clip((length - t) / 0.6, 0, 1)
    for note in CHORDS[chord]:
        for detune, pan in ((-0.0025, -0.5), (0.0025, 0.5)):
            fr = hz(note) * (1 + detune)
            v = sum((0.55**h) * np.sin(2 * np.pi * fr * (h + 1) * t) for h in range(5))
            place(dry, start, v * env, pan, 0.022)
            place(send, start, v * env, pan, 0.012)

# Arpeggio: eighth notes over the chord, alternating sides.
pattern = [0, 1, 2, 1, 0, 2, 1, 2]
step = BEAT / 2
t = 0.0
i = 0
while t < DUR - 1.2:
    chord = next(c for s, e, c in segments if s <= t < e)
    notes = CHORDS[chord] + [CHORDS[chord][0][:-1] + str(int(CHORDS[chord][0][-1]) + 1)]
    note = notes[pattern[i % 8]]
    fr = hz(note[:-1] + str(int(note[-1]) + 1))  # an octave up, sparkly but soft
    sig = pluck(fr, 0.5, 9.0, 0.25)
    pan = -0.35 if i % 2 else 0.35
    place(dry, t, sig, pan, 0.03)
    place(send, t, sig, pan, 0.03)
    t += step
    i += 1

# Bass: enters when the answer lands.
bass_in = f(TL["ask"]["answer"])
for start, end, chord in segments:
    for b in np.arange(start, end, BEAT * 2):
        if b < bass_in - 0.05:
            continue
        length = min(BEAT * 2, DUR - b)
        tt = np.arange(int(length * SR)) / SR
        fr = hz(ROOTS[chord])
        sig = (np.sin(2 * np.pi * fr * tt) + 0.3 * np.sin(2 * np.pi * 2 * fr * tt)) * np.exp(-tt * 2.2) * np.minimum(1, tt / 0.01)
        place(dry, b, sig, 0, 0.075)

# Soft kick and hat from the first highlight until the outro.
groove_start, groove_end = scene("formats"), outro
for n in range(int(DUR / BEAT) + 1):
    b = n * BEAT
    if groove_start - 0.01 <= b < groove_end:
        tt = np.arange(int(0.3 * SR)) / SR
        sweep = 45 + 75 * np.exp(-tt * 30)
        kick = np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.exp(-tt * 13)
        place(dry, b, kick, 0, 0.13)
        place(dry, b + BEAT / 2, noise_burst(0.04, 90), 0.15, 0.012)

# --- sound effects, in key ----------------------------------------------------
q = ASK["user_message"]["content"]
a = TL["ask"]
for j in range(len(q)):
    if q[j] == " ":
        continue
    ct = f(a["typeStart"]) + (f(a["typeEnd"]) - f(a["typeStart"])) * j / len(q)
    ct += rng.uniform(-0.012, 0.012)
    place(dry, ct, noise_burst(0.012, 400, hp=2), rng.uniform(-0.2, 0.2), 0.02)
    place(send, ct, noise_burst(0.012, 400, hp=2), 0, 0.006)

place(dry, f(a["send"]), pluck(hz("A5"), 0.5, 10), 0.1, 0.05)
place(send, f(a["send"]), pluck(hz("A5"), 0.5, 10), 0.1, 0.04)
for k2, note in enumerate(["D6", "F#6"]):
    st = f(a["answer"]) + k2 * 0.08
    place(dry, st, bell(hz(note), 1.2), 0, 0.05)
    place(send, st, bell(hz(note), 1.2), 0, 0.05)

for when in [f(a["evidence"]), scene("formats"), scene("pipeline"), scene("proof"), scene("outro")]:
    w = whoosh(0.5)
    place(dry, when - 0.28, w, 0, 0.02)
    place(send, when - 0.28, w, 0, 0.02)

fm = TL["formats"]
for k2, note in enumerate(["D5", "F#5", "A5"]):
    st = scene("formats") + f(fm["cards"][k2])
    place(dry, st, pluck(hz(note), 0.6, 9), (k2 - 1) * 0.3, 0.045)
    place(send, st, pluck(hz(note), 0.6, 9), 0, 0.03)
place(dry, scene("formats") + f(fm["stored"]), bell(hz("D6"), 1.2), 0, 0.045)
place(send, scene("formats") + f(fm["stored"]), bell(hz("D6"), 1.2), 0, 0.05)

for k2, note in enumerate(["D5", "E5", "F#5", "A5", "B5"]):
    st = scene("pipeline") + f(TL["pipeline"]["nodes"][k2])
    place(dry, st, pluck(hz(note), 0.5, 10), -0.2 + k2 * 0.1, 0.04)
    place(send, st, pluck(hz(note), 0.5, 10), 0, 0.03)

pr = TL["proof"]
off = scene("proof") + f(pr["off"])
place(dry, off, pluck(hz("B2"), 0.7, 6, 0.15), 0, 0.09)  # a low, muted "not quite"
place(dry, off + 0.12, pluck(hz("F#2"), 0.7, 6, 0.15), 0, 0.07)
place(dry, scene("proof") + f(pr["fix"]), pluck(hz("A5"), 0.5, 10), 0, 0.045)
for k2, note in enumerate(["D5", "F#5", "A5", "D6"]):
    st = scene("proof") + f(pr["match"]) + k2 * 0.07
    place(dry, st, bell(hz(note), 1.6), (k2 - 1.5) * 0.2, 0.045)
    place(send, st, bell(hz(note), 1.6), 0, 0.06)

place(dry, outro + f(TL["outro"]["mark"]), bell(hz("D5"), 2.2), 0, 0.05)
place(send, outro + f(TL["outro"]["mark"]), bell(hz("D5"), 2.2), 0, 0.06)

# --- shared room --------------------------------------------------------------
ir_len = int(1.6 * SR)
tt = np.arange(ir_len) / SR
ir = np.stack([rng.standard_normal(ir_len), rng.standard_normal(ir_len)], axis=1) * np.exp(-tt / 0.42)[:, None]
ir[: int(0.012 * SR)] = 0  # small pre-delay
ir /= np.sqrt((ir**2).sum(axis=0))
size = 1 << int(np.ceil(np.log2(N + ir_len)))
wet = np.stack([np.fft.irfft(np.fft.rfft(send[:, ch], size) * np.fft.rfft(ir[:, ch], size), size)[:N] for ch in range(2)], axis=1)
mix = dry + wet * 0.55

# --- master -------------------------------------------------------------------
mix = mix[: int(DUR * SR)]
mix = np.tanh(mix * 1.6) / np.tanh(1.6)  # gentle glue, no hard clipping
mix /= np.max(np.abs(mix)) / 0.89
n = len(mix)
fade_in = np.minimum(1, np.arange(n) / (0.03 * SR))
fade_out = np.clip((n - np.arange(n)) / (1.5 * SR), 0, 1)
mix *= (fade_in * fade_out)[:, None]

out = ROOT / "public/soundtrack.wav"
pcm = (mix * 32767).astype("<i2")
with wave.open(str(out), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f"wrote {out} ({n / SR:.2f}s)")
