"""
Soundtrack for the 18s phone promo: subtle electronic bed at 112 BPM in D major,
with notification chimes, UI whooshes and typing ticks tuned to the same key and
placed from src/phone/timeline.json.

    python scripts/phone_soundtrack.py  ->  public/phone-soundtrack.wav
"""

import json
from pathlib import Path

from synth import Mix, hz

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "src/phone/timeline.json").read_text())
ASK = json.loads((ROOT / "src/data/ask.json").read_text())
FPS = TL["fps"]
DUR = TL["total"] / FPS
f = lambda frame: frame / FPS

m = Mix(DUR)
BEAT = 60 / 112
BAR = BEAT * 4
CHORDS = {"D": ["D4", "F#4", "A4"], "Bm": ["B3", "D4", "F#4"], "G": ["G3", "B3", "D4"], "A": ["A3", "C#4", "E4"]}
ROOT_NOTE = {"D": "D2", "Bm": "B1", "G": "G1", "A": "A1"}
prog = ["D", "Bm", "G", "A"]
outro = f(TL["outro"]["start"])

segments, t0, k = [], 0.0, 0
while t0 < outro:
    end = min(t0 + BAR, outro)
    segments.append((t0, end, prog[k % 4]))
    t0, k = end, k + 1
segments.append((outro, DUR + 0.5, "D"))
chord_at = lambda t: next(c for s, e, c in segments if s <= t < e)

# Pad bed, quiet and wide.
for s, e, c in segments:
    sig = m.pad([hz(n) for n in CHORDS[c]], e - s + 0.5)
    m.place(s, sig, -0.4, 0.010, 0.006)
    m.place(s, sig, 0.4, 0.010, 0.006)

# Pulsing synth bass on eighths, entering as the dashboard loads.
groove_in = f(TL["intro"]["load"])
t = 0.0
while t < DUR - 0.8:
    if t >= groove_in - 0.01:
        m.place(t, m.bass(hz(ROOT_NOTE[chord_at(t)]), BEAT / 2), 0, 0.038)
    t += BEAT / 2

# Four-on-the-floor kick + offbeat hats from the first notification to the outro.
for i in range(int(DUR / BEAT) + 1):
    b = i * BEAT
    if f(TL["notifs"]["at"][0]) - 0.05 <= b < outro:
        m.place(b, m.kick(), 0, 0.075)
        m.place(b + BEAT / 2, m.hat(), 0.2, 0.012)

# Light arpeggio over the top (sixteenths, sparse).
t, i = 0.0, 0
pattern = [0, 2, 1, 2]
while t < DUR - 1.0:
    c = CHORDS[chord_at(t)]
    note = c[pattern[i % 4]]
    fr = hz(note[:-1] + str(int(note[-1]) + 1))
    m.place(t, m.pluck(fr, 0.35, 12, 0.22), -0.3 if i % 2 else 0.3, 0.022, 0.02)
    t += BEAT / 2
    i += 1

# --- SFX in key ---
m.place(f(TL["intro"]["start"]) + 0.05, m.whoosh(0.7, 1200), 0, 0.03, 0.02)            # phone glides in
for j, at in enumerate(TL["notifs"]["at"]):                                              # notification chimes
    for kk, note in enumerate([["A5", "D6"], ["B5", "F#6"], ["D6", "A6"]][j]):
        m.place(f(at) + kk * 0.07, m.bell(hz(note), 1.0), 0.15, 0.045, 0.05)
for at in [TL["glance"]["start"], TL["ask"]["start"], TL["proof"]["start"], TL["outro"]["start"]]:
    m.place(f(at) - 0.2, m.whoosh(0.42), 0, 0.022, 0.02)                                  # UI transitions
for at in [TL["glance"]["salary"], TL["glance"]["signals"]]:
    m.place(f(at), m.pluck(hz("F#5"), 0.4, 11), 0, 0.03, 0.03)

a = TL["ask"]
q = ASK["user_message"]["content"].replace("Kestrel", TL["banks"]["kestrel"])
for j, ch in enumerate(q):
    if ch != " ":
        ct = f(a["typeStart"]) + (f(a["typeEnd"]) - f(a["typeStart"])) * j / len(q) + m.rng.uniform(-0.01, 0.01)
        m.place(ct, m.tick(), m.rng.uniform(-0.2, 0.2), 0.018, 0.005)
m.place(f(a["send"]), m.pluck(hz("A5"), 0.4, 11), 0, 0.04, 0.03)
for kk, note in enumerate(["D6", "F#6"]):
    m.place(f(a["answer"]) + kk * 0.08, m.bell(hz(note), 1.1), 0, 0.045, 0.05)
for kk in range(4):
    m.place(f(a["rows"]) + kk * 4 / FPS, m.pluck(hz(["D5", "E5", "F#5", "A5"][kk]), 0.3, 13), 0.1, 0.025, 0.02)

p = TL["proof"]
m.place(f(p["off"]), m.pluck(hz("B2"), 0.6, 6, 0.15), 0, 0.08)
m.place(f(p["off"]) + 0.12, m.pluck(hz("F#2"), 0.6, 6, 0.15), 0, 0.06)
m.place(f(p["fix"]), m.pluck(hz("A5"), 0.4, 11), 0, 0.04, 0.03)
for kk, note in enumerate(["D5", "F#5", "A5", "D6"]):
    m.place(f(p["match"]) + kk * 0.06, m.bell(hz(note), 1.5), (kk - 1.5) * 0.2, 0.04, 0.06)

m.place(outro + 0.1, m.bell(hz("D5"), 2.0), 0, 0.045, 0.06)
m.place(outro + 0.1, m.pad([hz("D4"), hz("F#4"), hz("A4"), hz("D5")], DUR - outro), 0, 0.02, 0.02)

out = ROOT / "public/phone-soundtrack.wav"
m.render(out)
print("wrote", out)
