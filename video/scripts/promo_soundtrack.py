"""
Soundtrack for the promo (brag-output/promo/PROMPT.md, "Sound").

Modelled on the reference's measured profile: near silence under the sting and
the phone rise with a riser, a hard drop with an impact on the push-in, then a
bright, punchy ~150 BPM half-time beat (16th hats, clap on 3, 808 sub, detuned
stabs), a cut on the end card with a bell tail. Every effect is in key and
placed from src/promo/timeline.json.
"""

import json
from pathlib import Path

from synth import Mix, hz

ROOT = Path(__file__).resolve().parent.parent
TL = json.loads((ROOT / "src/promo/timeline.json").read_text())
ASK = json.loads((ROOT / "src/data/ask.json").read_text())
FPS = TL["fps"]
f = lambda frame: frame / FPS
DUR = TL["total"] / FPS
m = Mix(DUR, seed=11)

BPM = 150
BEAT = 60 / BPM
BAR = BEAT * 4
DROP = f(TL["push"][0])
END = f(TL["endCut"])
CHORDS = {"Bm": ["B3", "D4", "F#4"], "G": ["G3", "B3", "D4"], "D": ["D4", "F#4", "A4"], "A": ["A3", "C#4", "E4"]}
ROOTS = {"Bm": "B1", "G": "G1", "D": "D2", "A": "A1"}
PROG = ["Bm", "G", "D", "A"]
chord_at = lambda t: PROG[int(max(0, t - DROP) // BAR) % 4]
up = lambda n: n[:-1] + str(int(n[-1]) + 1)

# --- intro: shimmer under the sting, riser through the phone rise ---
m.place(0.0, m.bell(hz("F#6"), 1.2), 0, 0.02, 0.05)
m.place(0.05, m.pad([hz("B4"), hz("F#5")], 1.0, attack=0.2, release=0.4), 0, 0.006, 0.01)
r0 = f(TL["rise"][0])
m.place(r0, m.riser(DROP - r0), 0, 0.05, 0.03)
m.place(DROP, m.impact(), 0, 0.11, 0.06)

# --- the beat (DROP → END) ---
t = DROP
step = BEAT / 4  # 16ths
i = 0
while t < END - 0.01:
    pos = i % 16  # position in the bar
    c = chord_at(t)
    # hats: every 16th, accents on 8ths, a little open hat on the last 16th
    vel = 0.022 if pos % 2 else 0.032
    m.place(t, m.hat(0.07 if pos == 14 else 0.035), 0.25 if pos % 2 else -0.15, vel)
    # kick: beat 1 and the "a" of 2 (trap-style)
    if pos in (0, 7, 10):
        m.place(t, m.kick(), 0, 0.075)
        m.place(t, m.sub808(hz(ROOTS[c]), BEAT * 1.6), 0, 0.04)
    # clap on 3 (half-time)
    if pos == 8:
        m.place(t, m.clap(), 0, 0.07, 0.05)
    # bright detuned stabs on the off-beats
    if pos in (2, 6, 11, 14):
        m.place(t, m.stab([hz(up(n)) for n in CHORDS[c]], 0.16), -0.3 if pos % 4 else 0.3, 0.016, 0.014)
    t += step
    i += 1

# a soft pad underneath for body
t = DROP
while t < END:
    c = chord_at(t)
    m.place(t, m.pad([hz(n) for n in CHORDS[c]], min(BAR, END - t) + 0.2), 0, 0.007, 0.006)
    t += BAR

# --- SFX in key ---
for j, at in enumerate(TL["notifs"]):
    for k, note in enumerate([["F#5", "B5"], ["A5", "D6"], ["B5", "F#6"]][j]):
        m.place(f(at) + k * 0.07, m.bell(hz(note), 0.9), 0.2, 0.05, 0.05)
for at in [TL["pullBack"][0], TL["toAsk"][0], TL["toProof"][0], TL["sheet"][0]]:
    m.place(f(at) - 0.15, m.whoosh(0.42, 1800), 0, 0.03, 0.02)
a = TL["ask"]
q = ASK["user_message"]["content"].replace("Kestrel", TL["banks"]["kestrel"])
for j, ch in enumerate(q):
    if ch != " ":
        ct = f(a["typeStart"]) + (f(a["typeEnd"]) - f(a["typeStart"])) * j / len(q) + m.rng.uniform(-0.01, 0.01)
        m.place(ct, m.tick(), m.rng.uniform(-0.2, 0.2), 0.02, 0.005)
m.place(f(a["send"]), m.pluck(hz("A5"), 0.35, 12), 0, 0.04, 0.03)
for k, note in enumerate(["D6", "F#6"]):
    m.place(f(a["answer"]) + k * 0.08, m.bell(hz(note), 1.0), 0, 0.05, 0.05)
for at in a["pops"] + [TL["proof"]["pop"]]:
    m.place(f(at), m.popsfx(), 0, 0.05, 0.03)
p = TL["proof"]
m.place(f(p["off"]), m.pluck(hz("B2"), 0.6, 6, 0.15), 0, 0.09)
m.place(f(p["fix"]), m.pluck(hz("A5"), 0.35, 12), 0, 0.04, 0.03)
for k, note in enumerate(["D5", "F#5", "A5", "D6"]):
    m.place(f(p["match"]) + k * 0.06, m.bell(hz(note), 1.4), (k - 1.5) * 0.2, 0.045, 0.06)

# --- the cut: one bell with a tail under the end card ---
m.place(END, m.bell(hz("B5"), 1.2), 0, 0.06, 0.10)
m.place(END, m.bell(hz("F#6"), 1.2), 0, 0.03, 0.08)

out = ROOT / "public/promo-soundtrack.wav"
m.render(out, wet=0.45, room=0.38, fade_out=0.6, drive=2.4, limit_db=-9)
print("wrote", out)
