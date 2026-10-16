"""Synthesised instruments that sample libraries rarely cover well (docs/INSTRUMENTS.md):

- a tonewheel organ (Hammond-style): nine drawbars of sine "wheels", key click, second/third-harmonic
  percussion, chorus-vibrato, a two-rotor Leslie (horn and drum: amplitude and pitch wobble, stereo) and drive.
  Persona 5 uses NI Vintage Organs' "C3 Jazz" and rock organ presets (Atlus sound sheet).
- an analog-style synth: detuned saw/square stacks through a resonant low-pass with a filter envelope, for
  leads, pads, stabs and the Persona 3 style synth lines.

All render (start s, length s, key, velocity) note lists to (2, n) float32 at 44.1 kHz.
"""

from __future__ import annotations

import numpy as np

SR = 44100
# Drawbar footages as harmonics of the played note: 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5', 1 1/3', 1'.
HARM = [0.5, 1.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0]
ORGANS = {
    "jazz": {"drawbars": "888000000", "perc": 3, "click": 0.35, "drive": 0.15, "leslie": "slow"},
    "gospel": {"drawbars": "888800000", "perc": 0, "click": 0.3, "drive": 0.25, "leslie": "fast"},
    "rock": {"drawbars": "888888888", "perc": 0, "click": 0.4, "drive": 0.55, "leslie": "fast"},
    "soft": {"drawbars": "806000000", "perc": 0, "click": 0.15, "drive": 0.05, "leslie": "slow"},
}


def _hz(key: float) -> float:
    return 440.0 * 2 ** ((key - 69) / 12)


def organ(notes, total_sec: float, preset: str = "jazz", rng=None) -> np.ndarray:
    p = ORGANS[preset]
    rng = rng or np.random.default_rng(0)
    n = int(total_sec * SR)
    dry = np.zeros(n, dtype=np.float64)
    levels = [int(c) / 8 for c in p["drawbars"]]
    for start, length, key, vel in notes:
        a = int(start * SR)
        if a >= n:
            continue
        m = min(int((length + 0.02) * SR), n - a)
        t = np.arange(m) / SR
        f = _hz(key)
        x = np.zeros(m)
        for h, lv in zip(HARM, levels):
            if lv and f * h < 16000:
                x += lv * np.sin(2 * np.pi * f * h * t + rng.uniform(0, 2 * np.pi))  # wheels are free-running
        if p["perc"]:
            x += 0.9 * np.sin(2 * np.pi * f * p["perc"] * t) * np.exp(-t / 0.2)
        env = np.ones(m)
        k = min(int(0.004 * SR), m)
        env[:k] = np.linspace(0, 1, k)
        r = min(int(0.02 * SR), m)
        env[-r:] *= np.linspace(1, 0, r)
        if p["click"]:
            c = min(int(0.006 * SR), m)
            x[:c] += p["click"] * rng.normal(0, 1, c) * np.linspace(1, 0, c)
        dry[a:a + m] += x * env * (0.55 + 0.45 * vel / 127) / max(1.0, sum(levels))
    # chorus-vibrato (C3): a little pitch wobble mixed with the dry signal
    dry = 0.6 * dry + 0.4 * _vary_delay(dry, 0.0006, 6.8)
    if p["drive"]:
        g = 1 + 6 * p["drive"]
        dry = np.tanh(g * dry) / np.tanh(g)
    return (0.5 * leslie(dry, p["leslie"])).astype(np.float32)


def _vary_delay(x: np.ndarray, depth_s: float, rate_hz: float, phase: float = 0.0) -> np.ndarray:
    t = np.arange(len(x))
    d = depth_s * SR * (1 + np.sin(2 * np.pi * rate_hz * t / SR + phase)) / 2 + 2
    pos = np.clip(t - d, 0, len(x) - 1)
    i0 = pos.astype(np.int64)
    fr = pos - i0
    return x[i0] * (1 - fr) + x[np.minimum(i0 + 1, len(x) - 1)] * fr


def leslie(x: np.ndarray, speed: str = "slow") -> np.ndarray:
    """Rotary speaker: the signal split at 800 Hz into horn (fast) and drum (slower), each with a pitch
    wobble (Doppler) and amplitude wobble, left and right a quarter turn apart."""
    from scipy.signal import butter, sosfilt

    horn_hz, drum_hz = (6.7, 5.9) if speed == "fast" else (0.8, 0.7)
    lo = sosfilt(butter(2, 800, "low", fs=SR, output="sos"), x)
    hi = x - lo
    out = []
    for ph in (0.0, np.pi / 2):
        t = np.arange(len(x)) / SR
        h = _vary_delay(hi, 0.0004, horn_hz, ph) * (1 - 0.35 * (1 + np.sin(2 * np.pi * horn_hz * t + ph)) / 2)
        d = _vary_delay(lo, 0.0002, drum_hz, ph) * (1 - 0.15 * (1 + np.sin(2 * np.pi * drum_hz * t + ph)) / 2)
        out.append(h + d)
    return np.stack(out)


SYNTHS = {
    # waves: list of (shape, detune cents, octave, level); cutoff in Hz, env_amt in octaves, adsr in s/level
    "saw_lead": {"waves": [("saw", -7, 0, 1.0), ("saw", 7, 0, 1.0), ("square", 0, -1, 0.4)], "cutoff": 1800,
                 "res": 0.25, "env_amt": 2.0, "adsr": (0.005, 0.25, 0.7, 0.15), "glide": 0.04, "vib": 12},
    "super_pad": {"waves": [("saw", c, 0, 1.0) for c in (-18, -9, 0, 9, 18)], "cutoff": 2200, "res": 0.1,
                  "env_amt": 0.5, "adsr": (0.35, 0.6, 0.8, 0.8), "glide": 0.0, "vib": 0},
    "brass_stab": {"waves": [("saw", -6, 0, 1.0), ("saw", 6, 0, 1.0)], "cutoff": 900, "res": 0.15,
                   "env_amt": 3.0, "adsr": (0.01, 0.18, 0.5, 0.12), "glide": 0.0, "vib": 0},
    "sub_bass": {"waves": [("sine", 0, 0, 1.0), ("square", 0, 0, 0.25)], "cutoff": 500, "res": 0.0,
                 "env_amt": 0.5, "adsr": (0.003, 0.2, 0.85, 0.06), "glide": 0.0, "vib": 0},
    "pluck": {"waves": [("square", -5, 0, 1.0), ("saw", 5, 0, 0.6)], "cutoff": 700, "res": 0.3,
              "env_amt": 3.5, "adsr": (0.002, 0.22, 0.0, 0.15), "glide": 0.0, "vib": 0},
    # The sound sheet's Persona synths (PERSONA_PRODUCTION section 10): Virus "Acid" (Burn My Dread), a Virus lead
    # (School Days' JamMini) and bass, Xpand's "Percy FM Bass" (A Way of Life), Absynth's "FM Pad" (Moon Reload).
    "acid": {"waves": [("saw", 0, 0, 1.0)], "cutoff": 380, "res": 0.78, "env_amt": 3.6,
             "adsr": (0.002, 0.16, 0.55, 0.04), "glide": 0.06, "vib": 0, "drive": 3.0},
    "virus_lead": {"waves": [("saw", c, 0, 1.0) for c in (-14, -6, 0, 6, 14)] + [("square", 0, -1, 0.35)],
                   "cutoff": 3200, "res": 0.18, "env_amt": 1.2, "adsr": (0.004, 0.3, 0.8, 0.18), "glide": 0.035,
                   "vib": 14, "wide": True},
    "virus_bass": {"waves": [("saw", -4, 0, 1.0), ("square", 4, 0, 0.6), ("sine", 0, -1, 0.3)], "cutoff": 420, "res": 0.3,
                   "env_amt": 2.6, "adsr": (0.002, 0.14, 0.45, 0.05), "glide": 0.0, "vib": 0, "drive": 1.5},
    "fm_bass": {"fm": (1.0, 4.5, 0.10, 0.9), "adsr": (0.002, 0.35, 0.55, 0.06), "glide": 0.0, "vib": 0},
    "fm_pad": {"fm": (2.0, 1.4, 1.2, 0.5), "detune": 9, "adsr": (0.45, 0.9, 0.8, 1.1), "glide": 0.0, "vib": 6,
               "wide": True},
}


def _wave(shape: str, f: np.ndarray) -> np.ndarray:
    """Band-limited-ish oscillators (PolyBLEP saw/square) from a per-sample frequency curve."""
    ph = np.cumsum(f / SR) % 1.0
    dt = np.clip(f / SR, 1e-6, 0.5)
    if shape == "sine":
        return np.sin(2 * np.pi * ph)

    def blep(t):
        out = np.zeros_like(t)
        a = t < dt
        x = t[a] / dt[a]
        out[a] = x + x - x * x - 1
        b = t > 1 - dt
        x = (t[b] - 1) / dt[b]
        out[b] = x * x + x + x + 1
        return out

    saw = 2 * ph - 1 - blep(ph)
    if shape == "saw":
        return saw
    ph2 = (ph + 0.5) % 1.0
    saw2 = 2 * ph2 - 1 - blep(ph2)
    return 0.5 * (saw - saw2)


def _svf_lowpass(x: np.ndarray, cutoff: np.ndarray, res: float) -> np.ndarray:
    """State-variable low-pass with a per-sample cutoff (Chamberlin), 2x oversampled for stability."""
    f = 2 * np.sin(np.pi * np.clip(cutoff, 20, SR / 6) / (2 * SR))
    q = 1.0 - 0.9 * res
    lp = bp = 0.0
    out = np.empty_like(x)
    xs = x.tolist()
    fs = f.tolist()
    for i, v in enumerate(xs):
        fi = fs[i]
        for _ in range(2):
            hp = v - lp - q * bp
            bp += fi * hp
            lp += fi * bp
        out[i] = lp
    return out


def synth(notes, total_sec: float, preset: str = "saw_lead", rng=None) -> np.ndarray:
    p = SYNTHS[preset]
    rng = rng or np.random.default_rng(0)
    n = int(total_sec * SR)
    out = np.zeros(n)
    a_s, d_s, s_l, r_s = p["adsr"]
    prev_f = None
    for start, length, key, vel in sorted(notes, key=lambda x: x[0]):
        a = int(start * SR)
        if a >= n:
            continue
        m = min(int((length + r_s) * SR), n - a)
        t = np.arange(m) / SR
        f_target = _hz(key)
        f = np.full(m, f_target)
        if p["glide"] and prev_f:
            g = min(m, int(p["glide"] * SR))
            f[:g] = prev_f * (f_target / prev_f) ** np.linspace(0, 1, g)
        if p["vib"]:
            f *= 2 ** (p["vib"] / 1200 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.3) / 0.3, 0, 1))
        prev_f = f_target
        if p.get("fm"):  # two-operator FM: the modulator's depth falls from i0 to i1 over `decay` seconds
            ratio, i0, decay, i1 = p["fm"]
            idx = i1 + (i0 - i1) * np.exp(-t / decay) * (0.5 + 0.5 * vel / 127)
            x = 0
            for dc in ((0,) if not p.get("detune") else (-p["detune"], p["detune"])):
                ph = np.cumsum(f * 2 ** (dc / 1200) / SR)
                x = x + np.sin(2 * np.pi * ph + idx * np.sin(2 * np.pi * ratio * ph))
            env = np.where(t < a_s, t / max(a_s, 1e-4),
                           np.where(t < a_s + d_s, 1 - (1 - s_l) * (t - a_s) / max(d_s, 1e-4), s_l))
            env = np.where(t > length, env * np.exp(-(t - length) / max(r_s / 4, 1e-3)), env)
            out[a:a + m] += x * env * (0.4 + 0.6 * vel / 127)
            continue
        x = sum(lv * _wave(sh, f * 2 ** (oc + dc / 1200)) for sh, dc, oc, lv in p["waves"])
        env = np.where(t < a_s, t / max(a_s, 1e-4),
                       np.where(t < a_s + d_s, 1 - (1 - s_l) * (t - a_s) / max(d_s, 1e-4), s_l))
        off = length
        env = np.where(t > off, env * np.exp(-(t - off) / max(r_s / 4, 1e-3)), env)
        fenv = np.where(t < a_s + d_s, np.clip(1 - (t - a_s) / max(d_s, 1e-4), 0, 1), 0)
        cutoff = p["cutoff"] * 2 ** (p["env_amt"] * fenv) * (0.6 + 0.4 * vel / 127)
        x = _svf_lowpass(x, cutoff, p["res"])
        if p.get("drive"):  # the acid squelch and the Virus bass bite
            x = np.tanh(p["drive"] * x) / np.tanh(p["drive"])
        out[a:a + m] += x * env * (0.4 + 0.6 * vel / 127)
    pk = np.abs(out).max() or 1.0
    out = out / pk * 0.5
    # a touch of stereo: 7 ms Haas copy on the right at -4 dB for pads, dead centre otherwise
    if preset == "super_pad" or p.get("wide"):
        d = int(0.007 * SR)
        return np.stack([out, np.r_[np.zeros(d), out[:-d]] * 0.63 + out * 0.37]).astype(np.float32)
    return np.stack([out, out]).astype(np.float32)


# --------------------------------------------------------------------------------------------------
# Chip voices (the NES/SNES-style colours Toby Fox mixes with real instruments; docs/PERSONA_PRODUCTION.md §7)
# --------------------------------------------------------------------------------------------------
CHIPS = {"pulse": 0.25, "square": 0.5, "thin": 0.125, "triangle": None}


def chip(notes, total_sec: float, voice: str = "pulse", rng=None) -> np.ndarray:
    """A chip voice: naive (aliasing on purpose) pulse waves with a duty cycle, or a 4-bit stepped triangle;
    a short decay to a sustain, a little delayed vibrato on long notes, no filter."""
    n = int(total_sec * SR)
    out = np.zeros(n)
    duty = CHIPS[voice]
    for start, length, key, vel in notes:
        a = int(start * SR)
        if a >= n:
            continue
        m = min(int((length + 0.03) * SR), n - a)
        t = np.arange(m) / SR
        f = _hz(key) * 2 ** (0.18 / 12 * np.sin(2 * np.pi * 6 * t) * np.clip((t - 0.25) / 0.2, 0, 1))
        ph = np.cumsum(f / SR) % 1.0
        if duty is None:
            tri = 1 - 4 * np.abs(ph - 0.5)
            x = np.round(tri * 7.5) / 7.5  # 16 steps, like the NES triangle
        else:
            x = np.where(ph < duty, 1.0, -1.0)
        env = np.minimum(1.0, 0.55 + 0.45 * np.exp(-t / 0.08))
        off = int(length * SR)
        if off < m:
            env[off:] *= np.linspace(1, 0, m - off)
        out[a:a + m] += x * env * (0.3 + 0.7 * vel / 127) * 0.22
    return np.stack([out, out]).astype(np.float32)


def chip_drums(notes, total_sec: float, rng=None) -> np.ndarray:
    """A chip kit on GM drum notes: kick = a fast-falling triangle, snare = noise burst + tone, hats = short
    high noise (the NES noise channel)."""
    rng = rng or np.random.default_rng(0)
    n = int(total_sec * SR)
    out = np.zeros(n)
    for start, length, key, vel in notes:
        a = int(start * SR)
        if a >= n:
            continue
        g = 0.3 + 0.7 * vel / 127
        if key in (35, 36):
            m = min(int(0.16 * SR), n - a)
            t = np.arange(m) / SR
            f = 50 + 180 * np.exp(-t * 45)
            ph = np.cumsum(f / SR) % 1
            x = (1 - 4 * np.abs(ph - 0.5)) * np.exp(-t * 14)
        elif key in (38, 40, 37):
            m = min(int(0.18 * SR), n - a)
            t = np.arange(m) / SR
            x = (rng.choice([-1.0, 1.0], m) * 0.7 + 0.3 * np.sign(np.sin(2 * np.pi * 190 * t))) * np.exp(-t * 18)
        else:
            m = min(int((0.25 if key == 46 else 0.04) * SR), n - a)
            t = np.arange(m) / SR
            x = rng.choice([-1.0, 1.0], m) * np.exp(-t * (8 if key == 46 else 60)) * 0.5
            x = np.repeat(x[::3], 3)[:m]  # the noise channel's coarse sample rate
        out[a:a + m] += x * g * 0.35
    return np.stack([out, out]).astype(np.float32)
