"""Small synthesis kit shared by the soundtrack scripts: tuned voices, a shared room, a gentle master."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 44100
NOTES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def hz(note: str) -> float:
    name, octave = note[:-1], int(note[-1])
    return 440.0 * 2 ** ((NOTES[name] + 12 * (octave + 1) - 69) / 12)


def limit(x: np.ndarray, ceiling_db: float, lookahead: float = 0.005, release: float = 0.08) -> np.ndarray:
    """Look-ahead peak limiter: gain rides down ahead of peaks, recovers smoothly."""

    ceiling = 10 ** (ceiling_db / 20) * np.max(np.abs(x))
    peak = np.max(np.abs(x), axis=1)
    want = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    la = int(lookahead * SR)
    # minimum over the look-ahead window so gain is already down when the peak arrives
    padded = np.concatenate([want, np.ones(la)])
    ahead = np.min(np.lib.stride_tricks.sliding_window_view(padded, la + 1), axis=1)[: len(want)]
    rel = np.exp(-1 / (release * SR))
    gain = np.empty_like(ahead)
    g = 1.0
    for i, w in enumerate(ahead):
        g = w if w < g else w + (g - w) * rel
        gain[i] = g
    return x * gain[:, None]


class Mix:
    def __init__(self, seconds: float, seed: int = 7):
        self.seconds = seconds
        self.n = int(seconds * SR) + SR
        self.dry = np.zeros((self.n, 2))
        self.send = np.zeros((self.n, 2))
        self.rng = np.random.default_rng(seed)

    def place(self, start: float, sig: np.ndarray, pan: float = 0.0, gain: float = 1.0, verb: float = 0.0) -> None:
        i = int(max(start, 0) * SR)
        if i >= self.n:
            return
        sig = sig[: self.n - i]
        lft, rgt = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
        for buf, g in ((self.dry, gain), (self.send, verb)):
            if g:
                buf[i : i + len(sig), 0] += sig * lft * g
                buf[i : i + len(sig), 1] += sig * rgt * g

    # --- voices ---
    @staticmethod
    def t(length: float) -> np.ndarray:
        return np.arange(int(length * SR)) / SR

    def pluck(self, freq: float, length: float = 0.6, decay: float = 9.0, bright: float = 0.3) -> np.ndarray:
        t = self.t(length)
        return sum((bright**k) * np.sin(2 * np.pi * freq * (k + 1) * t) for k in range(5)) * np.exp(-t * decay) * np.minimum(1, t / 0.004)

    def bell(self, freq: float, length: float = 1.4) -> np.ndarray:
        t = self.t(length)
        parts = [(1.0, 1.0, 3.4), (2.0, 0.32, 5.0), (2.76, 0.16, 7.5), (5.4, 0.05, 11.0)]
        return sum(a * np.sin(2 * np.pi * freq * r * t) * np.exp(-t * d) for r, a, d in parts) * np.minimum(1, t / 0.003)

    def pad(self, freqs: list[float], length: float, attack: float = 0.3, release: float = 0.5) -> np.ndarray:
        t = self.t(length)
        env = np.minimum(1, t / attack) * np.clip((length - t) / release, 0, 1)
        return sum(sum((0.5**h) * np.sin(2 * np.pi * fr * (h + 1) * t) for h in range(4)) for fr in freqs) * env

    def bass(self, freq: float, length: float) -> np.ndarray:
        t = self.t(length)
        return (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * 2 * freq * t)) * np.exp(-t * 5) * np.minimum(1, t / 0.006)

    def kick(self) -> np.ndarray:
        t = self.t(0.28)
        sweep = 46 + 80 * np.exp(-t * 32)
        return np.sin(2 * np.pi * np.cumsum(sweep) / SR) * np.exp(-t * 14)

    def hat(self, length: float = 0.035) -> np.ndarray:
        n = np.diff(np.diff(self.rng.standard_normal(int(length * SR)), prepend=0), prepend=0)
        return n * np.exp(-self.t(length) * 110)

    def tick(self) -> np.ndarray:
        n = np.diff(np.diff(self.rng.standard_normal(int(0.012 * SR)), prepend=0), prepend=0)
        return n * np.exp(-self.t(0.012) * 400)

    def whoosh(self, length: float = 0.5, cutoff: float = 1600) -> np.ndarray:
        n = self.rng.standard_normal(int(length * SR))
        a = np.exp(-2 * np.pi * cutoff / SR)
        y = np.empty_like(n)
        acc = 0.0
        for i, v in enumerate(n):
            acc = (1 - a) * v + a * acc
            y[i] = acc
        return y * np.sin(np.pi * np.clip(self.t(length) / length, 0, 1)) ** 2

    # --- render ---
    def render(self, path: Path, wet: float = 0.5, room: float = 0.42, fade_out: float = 1.4, drive: float = 1.6, limit_db: float | None = None) -> None:
        ir_len = int(1.5 * SR)
        tt = self.t(1.5)
        ir = self.rng.standard_normal((ir_len, 2)) * np.exp(-tt / room)[:, None]
        ir[: int(0.012 * SR)] = 0
        ir /= np.sqrt((ir**2).sum(axis=0))
        size = 1 << int(np.ceil(np.log2(self.n + ir_len)))
        reverb = np.stack(
            [np.fft.irfft(np.fft.rfft(self.send[:, c], size) * np.fft.rfft(ir[:, c], size), size)[: self.n] for c in range(2)],
            axis=1,
        )
        mix = (self.dry + reverb * wet)[: int(self.seconds * SR)]
        mix = np.tanh(mix * drive) / np.tanh(drive)
        if limit_db is not None:
            mix = limit(mix, limit_db)
        mix /= np.max(np.abs(mix)) / 0.89
        n = len(mix)
        env = np.minimum(1, np.arange(n) / (0.02 * SR)) * np.clip((n - np.arange(n)) / (fade_out * SR), 0, 1)
        mix *= env[:, None]
        with wave.open(str(path), "wb") as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes((mix * 32767).astype("<i2").tobytes())

    def saw(self, freq: float, length: float, harmonics: int = 14) -> np.ndarray:
        t = self.t(length)
        return sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, harmonics + 1) if freq * k < 12000)

    def stab(self, freqs: list[float], length: float = 0.18) -> np.ndarray:
        """Bright detuned saw chord with a fast pluck envelope."""
        t = self.t(length)
        env = np.exp(-t * 14) * np.minimum(1, t / 0.003)
        return sum(self.saw(fr * d, length) for fr in freqs for d in (0.996, 1.004)) * env

    def clap(self) -> np.ndarray:
        n = np.diff(self.rng.standard_normal(int(0.16 * SR)), prepend=0)
        t = self.t(0.16)
        env = np.exp(-t * 28) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 300) * (t < 0.035)
        return n * env

    def sub808(self, freq: float, length: float) -> np.ndarray:
        t = self.t(length)
        glide = freq * (1 + 0.6 * np.exp(-t * 40))
        return np.sin(2 * np.pi * np.cumsum(glide) / SR) * np.exp(-t * 2.4) * np.minimum(1, t / 0.004)

    def riser(self, length: float) -> np.ndarray:
        t = self.t(length)
        n = self.rng.standard_normal(len(t))
        # brighten over time: blend low-passed into raw noise
        a = 0.97
        lp = np.empty_like(n)
        acc = 0.0
        for i, v in enumerate(n):
            acc = (1 - a) * v + a * acc
            lp[i] = acc
        x = t / length
        tone = np.sin(2 * np.pi * np.cumsum(200 + 1400 * x**2) / SR) * 0.25
        return (lp * (1 - x) * 3 + n * x * 0.6 + tone) * (x**2)

    def impact(self) -> np.ndarray:
        t = self.t(1.6)
        boom = np.sin(2 * np.pi * np.cumsum(38 + 60 * np.exp(-t * 18)) / SR) * np.exp(-t * 3.0)
        crash = np.diff(self.rng.standard_normal(len(t)), prepend=0) * np.exp(-t * 5)
        return boom + 0.25 * crash

    def popsfx(self) -> np.ndarray:
        t = self.t(0.12)
        return np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 25) + 300) / SR) * np.exp(-t * 35)
