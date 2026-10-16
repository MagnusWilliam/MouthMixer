"""Sampled instruments: a small SFZ player (docs/INSTRUMENTS.md).

The General MIDI soundfont can't sound like a real Rhodes, Fender bass or drum kit. Free sample libraries
(with licences that allow released music) come as SFZ: a text file of regions mapping keys and velocities to
WAV/FLAC recordings. This module reads that format and renders notes in numpy: the region(s) for each key,
velocity and round robin, pitched from the nearest recorded key, with an amplitude envelope, release and
choke groups (an open hi-hat cut by the closed one).

Supported opcodes: sample, default_path, #define/$VAR, #include, key, lokey, hikey, pitch_keycenter, lovel,
hivel, lorand, hirand, seq_length, seq_position, tune, transpose, volume, amplitude, pan, amp_veltrack,
ampeg_attack, ampeg_hold, ampeg_decay, ampeg_sustain, ampeg_release, loop_mode (one_shot), offset, end,
group, off_by, trigger (release triggers are skipped), note names (c4, f#3; c4 = 60). Layers switched by a MIDI
CC (loccN/hiccN) play at the CC's set_ccN default or a value the caller gives; keyswitched articulations
(sw_last) play the sw_default one or the one the caller picks; built-in generators (*sine) and CC-triggered
regions are skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

SR = 44100
NOTE = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}


def note_number(v: str) -> int:
    v = v.strip().lower()
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    m = re.fullmatch(r"([a-g])([#b]?)(-?\d+)", v)
    if not m:
        raise ValueError(f"not a note: {v}")
    n = NOTE[m[1]] + (1 if m[2] == "#" else -1 if m[2] == "b" else 0)
    return n + (int(m[3]) + 1) * 12


@dataclass
class Region:
    sample: Path
    lokey: int = 0
    hikey: int = 127
    center: int = 60
    lovel: int = 1
    hivel: int = 127
    lorand: float = 0.0
    hirand: float = 1.0
    seq_length: int = 1
    seq_position: int = 1
    tune: float = 0.0  # cents
    transpose: int = 0
    volume: float = 0.0  # dB
    amplitude: float = 100.0  # %
    pan: float = 0.0  # -100..100
    veltrack: float = 100.0
    attack: float = 0.0
    hold: float = 0.0
    decay: float = 0.0
    sustain: float = 100.0
    release: float = 0.001
    one_shot: bool = False
    offset: int = 0
    end: int = 0
    group: int = 0
    off_by: int = 0
    cc_ranges: dict = field(default_factory=dict)
    sw: int | None = None


_KEYS = {"lokey", "hikey", "pitch_keycenter", "key"}


def parse(path: Path, cc: dict | None = None, keyswitch: int | None = None) -> list[Region]:
    """Regions of an SFZ file, with <global>/<master>/<group> opcodes inherited. `cc`: CC number -> value for
    CC-switched layers (default: the file's set_ccN, else 0); `keyswitch`: which sw_last articulation (default:
    sw_default, else the lowest)."""
    path = Path(path)
    defines: dict[str, str] = {}

    def read(p: Path) -> str:
        text = p.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"//[^\n]*", "", text)
        out = []
        for line in text.splitlines():
            m = re.match(r"\s*#define\s+(\$\w+)\s+(\S+)", line)
            if m:
                defines[m[1]] = m[2]
                continue
            m = re.match(r'\s*#include\s+"([^"]+)"', line)
            if m:  # relative to the top file (the SFZ spec); older libraries mean the including file
                inc = path.parent / m[1]
                out.append(read(inc if inc.exists() else p.parent / m[1]))
                continue
            out.append(line)
        return "\n".join(out)

    text = read(path)
    for k in sorted(defines, key=len, reverse=True):
        text = text.replace(k, defines[k])
    regions: list[Region] = []
    scopes = {"global": {}, "master": {}, "group": {}, "control": {}}
    current: dict | None = None
    level = None
    default_path = ""
    # Split into headers and opcode=value pairs; values may contain spaces (sample paths) up to the next opcode.
    tokens = re.split(r"(<\w+>)", text)
    for tok in tokens:
        h = re.fullmatch(r"<(\w+)>", tok)
        if h:
            if level == "region" and current is not None:
                regions.append(_region(current, path.parent, default_path))
            level = h[1]
            if level in ("global", "master", "group", "control"):
                if level == "global":
                    scopes["master"], scopes["group"] = {}, {}
                elif level == "master":
                    scopes["group"] = {}
                scopes[level] = {}
                current = scopes[level]
            elif level == "region":
                current = {**scopes["global"], **scopes["master"], **scopes["group"]}
            else:
                current = {}
            continue
        if current is None:
            continue
        for m in re.finditer(r"(\w+)=(.*?)(?=\s+\w+=|\s*$)", tok.strip(), flags=re.S):
            current[m[1]] = m[2].strip()
        if level == "control" and "default_path" in current:
            default_path = current["default_path"].replace("\\", "/")
    if level == "region" and current is not None:
        regions.append(_region(current, path.parent, default_path))
    regions = [r for r in regions if r is not None]
    ccv = {}
    for scope in (scopes["control"], scopes["global"]):
        for k, v in scope.items():
            m = re.fullmatch(r"set_cc(\d+)", k)
            if m:
                try:
                    ccv[int(m[1])] = float(v)
                except ValueError:
                    pass
    ccv.update(cc or {})
    regions = [r for r in regions if all(lo <= ccv.get(n, 0) <= hi for n, (lo, hi) in r.cc_ranges.items())]
    sws = sorted({r.sw for r in regions if r.sw is not None})
    if sws:
        dflt = scopes["control"].get("sw_default") or scopes["global"].get("sw_default")
        pick = keyswitch if keyswitch is not None else (note_number(dflt) if dflt else sws[0])
        regions = [r for r in regions if r.sw is None or r.sw == pick]
    return regions


def _region(o: dict, base: Path, default_path: str) -> Region | None:
    if "sample" not in o or o.get("trigger", "attack") != "attack" or o["sample"].startswith("*") \
            or any(k.startswith(("on_locc", "on_hicc")) for k in o):
        return None
    r = Region(sample=(base / (default_path + o["sample"].replace("\\", "/"))).resolve())
    for k, v in o.items():
        m = re.fullmatch(r"(lo|hi)cc(\d+)", k)
        if m:
            lo, hi = r.cc_ranges.get(int(m[2]), (0.0, 127.0))
            try:
                r.cc_ranges[int(m[2])] = (float(v), hi) if m[1] == "lo" else (lo, float(v))
            except ValueError:
                pass
    if "sw_last" in o:
        try:
            r.sw = note_number(o["sw_last"])
        except (ValueError, KeyError):
            pass
    if "key" in o:
        k = note_number(o["key"])
        r.lokey = r.hikey = r.center = k
    for name, attr in (("lokey", "lokey"), ("hikey", "hikey"), ("pitch_keycenter", "center")):
        if name in o:
            setattr(r, attr, note_number(o[name]))
    if "key" not in o and "pitch_keycenter" not in o:
        r.center = r.lokey if r.lokey == r.hikey else r.center
    for name, attr, cast in (("lovel", "lovel", int), ("hivel", "hivel", int), ("lorand", "lorand", float),
                             ("hirand", "hirand", float), ("seq_length", "seq_length", int),
                             ("seq_position", "seq_position", int), ("tune", "tune", float),
                             ("transpose", "transpose", int), ("volume", "volume", float),
                             ("amplitude", "amplitude", float), ("pan", "pan", float),
                             ("amp_veltrack", "veltrack", float), ("ampeg_attack", "attack", float),
                             ("ampeg_hold", "hold", float), ("ampeg_decay", "decay", float),
                             ("ampeg_sustain", "sustain", float), ("ampeg_release", "release", float),
                             ("offset", "offset", int), ("end", "end", int), ("group", "group", int),
                             ("off_by", "off_by", int)):
        if name in o:
            try:
                setattr(r, attr, cast(float(o[name])) if cast is int else cast(o[name]))
            except ValueError:
                pass
    r.one_shot = o.get("loop_mode", "") == "one_shot"
    return r


_AUDIO: dict[Path, np.ndarray] = {}


def load_sample(p: Path) -> np.ndarray:
    """(2, n) float32 at SR, cached."""
    if p not in _AUDIO:
        import soundfile as sf

        x, sr = sf.read(str(p), dtype="float32", always_2d=True)
        x = x.T
        if x.shape[0] == 1:
            x = np.vstack([x, x])
        x = x[:2]
        if sr != SR:
            from scipy.signal import resample_poly

            g = np.gcd(SR, sr)
            x = resample_poly(x, SR // g, sr // g, axis=1).astype(np.float32)
        _AUDIO[p] = x
    return _AUDIO[p]


class Instrument:
    """A parsed SFZ instrument that renders note lists."""

    def __init__(self, sfz: Path, cc: dict | None = None, keyswitch: int | None = None):
        self.path = Path(sfz)
        self.regions = parse(self.path, cc, keyswitch)
        if not self.regions:
            raise ValueError(f"no playable regions in {sfz}")

    def pick(self, key: int, vel: int, rand: float, seq: dict) -> list[Region]:
        cands = [r for r in self.regions if r.lokey <= key <= r.hikey and r.lovel <= vel <= r.hivel
                 and r.lorand <= rand < max(r.hirand, r.lorand + 1e-9)]
        if not cands:  # outside the mapped velocities: the nearest layer
            cands = [r for r in self.regions if r.lokey <= key <= r.hikey]
        out = []
        for r in cands:
            if r.seq_length > 1:
                k = (key, r.lovel, r.seq_length)
                pos = seq.get(k, 0) % r.seq_length + 1
                if pos != r.seq_position:
                    continue
            out.append(r)
        for r in cands:  # advance round robins once per note per layer
            if r.seq_length > 1:
                k = (key, r.lovel, r.seq_length)
                seq[k] = seq.get(k, 0)
        for k in {(key, r.lovel, r.seq_length) for r in cands if r.seq_length > 1}:
            seq[k] += 1
        return out

    def render(self, notes: list[tuple[float, float, int, int]], total_sec: float, rng=None,
               bend_cents: list[tuple[float, float]] | None = None) -> np.ndarray:
        """notes: (start s, length s, key, velocity). Returns (2, n) float32."""
        rng = rng or np.random.default_rng(0)
        n_total = int(total_sec * SR)
        out = np.zeros((2, n_total), dtype=np.float32)
        seq: dict = {}
        for start, length, key, vel in sorted(notes, key=lambda x: x[0]):
            a = int(start * SR)
            if a >= n_total:
                continue
            for r in self.pick(int(key), int(vel), float(rng.random()), seq):
                x = load_sample(r.sample)
                if r.end:
                    x = x[:, : r.end]
                x = x[:, r.offset:]
                semis = (key + r.transpose - r.center) + r.tune / 100
                ratio = 2 ** (semis / 12)
                rel = max(r.release, 0.002)
                dur = len(x[0]) / ratio / SR if r.one_shot else min(length + rel, len(x[0]) / ratio / SR)
                m = min(int(dur * SR), n_total - a)
                if m <= 8:
                    continue
                pos = np.arange(m) * ratio
                pos = pos[pos < x.shape[1] - 1]
                m = len(pos)
                i0 = pos.astype(np.int64)
                fr = (pos - i0).astype(np.float32)
                seg = x[:, i0] * (1 - fr) + x[:, i0 + 1] * fr
                env = np.ones(m, dtype=np.float32)
                at = int(r.attack * SR)
                if at > 1:
                    env[: min(at, m)] = np.linspace(0, 1, at)[: min(at, m)]
                if r.decay > 0 and r.sustain < 100:
                    d0 = at + int(r.hold * SR)
                    d1 = d0 + int(r.decay * SR)
                    s = r.sustain / 100
                    if d0 < m:
                        env[d0:min(d1, m)] *= np.linspace(1, s, d1 - d0)[: max(0, min(d1, m) - d0)]
                        env[min(d1, m):] *= s
                if not r.one_shot:
                    off = int(length * SR)
                    if off < m:
                        rl = m - off
                        env[off:] *= np.exp(-np.arange(rl) / max(1.0, rel * SR / 6.9))  # -60 dB at release
                vg = 10 ** (r.volume / 20) * r.amplitude / 100
                velc = (vel / 127) ** 2
                vg *= 1 - r.veltrack / 100 + r.veltrack / 100 * velc
                pan = np.clip(r.pan / 100, -1, 1)
                lg, rg = np.cos((pan + 1) * np.pi / 4) * np.sqrt(2), np.sin((pan + 1) * np.pi / 4) * np.sqrt(2)
                seg = seg * env * vg
                out[0, a:a + m] += seg[0] * lg
                out[1, a:a + m] += seg[1] * rg
        return out


def render_kit(inst: Instrument, notes, total_sec: float, rng=None) -> np.ndarray:
    """Drum kits with choke groups: each note rendered into its own voice buffer region, so a later note of
    group G can fade out sounding voices whose off_by is G (the open hi-hat closed by the pedal or closed hat)."""
    rng = rng or np.random.default_rng(0)
    n_total = int(total_sec * SR)
    out = np.zeros((2, n_total), dtype=np.float32)
    seq: dict = {}
    starts_by_group: dict[int, list[int]] = {}
    rendered = []
    for start, length, key, vel in sorted(notes, key=lambda x: x[0]):
        a = int(start * SR)
        if a >= n_total:
            continue
        for r in inst.pick(int(key), int(vel), float(rng.random()), seq):
            x = load_sample(r.sample)[:, r.offset:]
            semis = (key + r.transpose - r.center) + r.tune / 100
            ratio = 2 ** (semis / 12)
            m = min(int(x.shape[1] / ratio), n_total - a)
            pos = np.arange(m) * ratio
            pos = pos[pos < x.shape[1] - 1]
            i0 = pos.astype(np.int64)
            fr = (pos - i0).astype(np.float32)
            seg = x[:, i0] * (1 - fr) + x[:, i0 + 1] * fr
            vg = 10 ** (r.volume / 20) * r.amplitude / 100
            vg *= 1 - r.veltrack / 100 + r.veltrack / 100 * (vel / 127) ** 2
            pan = np.clip(r.pan / 100, -1, 1)
            g2 = np.array([[np.cos((pan + 1) * np.pi / 4)], [np.sin((pan + 1) * np.pi / 4)]]) * np.sqrt(2)
            rendered.append((seg * vg * g2, a, r.off_by))
            if r.group:
                starts_by_group.setdefault(r.group, []).append(a)
    fade = int(0.008 * SR)
    for seg, a, off_by in rendered:
        m = seg.shape[1]
        if off_by and off_by in starts_by_group:
            later = [s for s in starts_by_group[off_by] if s > a]
            if later and later[0] - a < m:
                cut = later[0] - a
                env = np.ones(m, dtype=np.float32)
                f = min(fade, m - cut)
                env[cut:cut + f] = np.linspace(1, 0, f)
                env[cut + f:] = 0
                seg = seg * env
        out[:, a:a + m] += seg
    return out
