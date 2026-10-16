"""Instrument profiles of a reference song from its six stems (Demucs htdemucs_6s: drums, bass, guitar, piano,
vocals, other): how loud each part sits against the mix and when it plays (the arrangement map), how busy it
is and where its notes fall in the bar, its register and how many notes sound at once, how long its notes
are, how bright and how wide it is. Plus pictures: a stems-over-time map and a spectrogram per stem.

`python -m mouthmixer profile <analysis folder>` reads <song>/stems6/*.wav (and the analysis.json the
analyser wrote) and writes <song>/profile.json, profile.md and img/. Like the analyser, it measures
tendencies (levels, densities, registers, rhythm positions), never a melody to copy.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .analyse import HOP, SR, _db, band_shares, beat_grid, groove, load, lufs

STEMS6 = ("drums", "bass", "guitar", "piano", "vocals", "other")


def _blocks(bar_t: np.ndarray, size: int = 4) -> list[tuple[float, float]]:
    """(start, end) seconds of every `size`-bar block."""
    idx = list(range(0, len(bar_t) - 1, size))
    return [(float(bar_t[i]), float(bar_t[min(i + size, len(bar_t) - 1)])) for i in idx]


def timeline(stem: np.ndarray, mix: np.ndarray, blocks) -> list[float | None]:
    """The stem's level against the mix (dB of RMS) per block; None where the stem is silent (under -45 dB
    against the mix, or digital silence)."""
    out = []
    for a, b in blocks:
        s, m = stem[:, int(a * SR):int(b * SR)], mix[:, int(a * SR):int(b * SR)]
        if s.shape[1] < SR // 4:
            out.append(None)
            continue
        d = _db(float(np.sqrt(np.mean(s ** 2)))) - _db(float(np.sqrt(np.mean(m ** 2))) + 1e-9)
        out.append(round(d, 1) if d > -45 else None)
    return out


def rhythm(onsets: np.ndarray, bar_t: np.ndarray) -> dict:
    """Onsets per bar and the share of onsets on each of the 16 steps of a bar (busy or sparse, on the beat
    or pushed)."""
    hist = np.zeros(16)
    per_bar = []
    for a, b in zip(bar_t[:-1], bar_t[1:]):
        o = onsets[(onsets >= a - 0.03) & (onsets < b - 0.03)]
        per_bar.append(len(o))
        for t in o:
            hist[min(15, int(round((t - a) / (b - a) * 16)) % 16)] += 1
    busy = [n for n in per_bar if n > 0]
    return {"onsets_per_active_bar": round(float(np.median(busy)), 1) if busy else 0.0,
            "step_share": [round(float(v), 3) for v in hist / max(1.0, hist.sum())]}


def pitch_profile(mono: np.ndarray, lo_midi: int = 24, hi_midi: int = 108) -> dict:
    """Register and polyphony from a constant-Q spectrogram. The register is the strongest note of every loud
    frame (10th/50th/90th percentile MIDI); the notes at once are the peaks within 15 dB of it that are not
    one of a lower peak's first overtones (an octave, a twelfth, two octaves, a major third above that)."""
    import librosa

    C = np.abs(librosa.cqt(mono, sr=SR, hop_length=HOP * 2, fmin=librosa.midi_to_hz(lo_midi),
                           n_bins=hi_midi - lo_midi, bins_per_octave=12))
    db = librosa.amplitude_to_db(C, ref=np.max)
    loud = db.max(axis=0) > -35
    top, counts, pcs = [], [], np.zeros(12)
    for f in np.flatnonzero(loud):
        col = db[:, f]
        peak = (col > col.max() - 15) & (col >= np.r_[-200, col[:-1]]) & (col >= np.r_[col[1:], -200])
        idx = []
        for i in np.flatnonzero(peak):
            if not any(j in idx for j in (i - 12, i - 19, i - 24, i - 28)):
                idx.append(i)
        top.append(lo_midi + int(np.argmax(col)))
        counts.append(len(idx))
        for i in idx:
            pcs[(lo_midi + i) % 12] += 1
    if not top:
        return {}
    return {"midi_p10_p50_p90": [int(np.percentile(top, q)) for q in (10, 50, 90)],
            "notes_at_once": round(float(np.mean(counts)), 2),
            "pitch_class_share": [round(float(v), 3) for v in pcs / max(1.0, pcs.sum())]}


def note_length(mono: np.ndarray, onsets: np.ndarray, beat_s: float) -> float | None:
    """Median note length in beats: from each onset until the level falls 12 dB under that note's peak (or
    the next onset)."""
    if len(onsets) < 4:
        return None
    hop = 256
    env = np.sqrt(np.convolve(mono ** 2, np.ones(hop) / hop, mode="same")[::hop]) + 1e-9
    fps = SR / hop
    lengths = []
    for i, t in enumerate(onsets):
        a = int(t * fps)
        b = int(onsets[i + 1] * fps) if i + 1 < len(onsets) else min(len(env), a + int(4 * beat_s * fps))
        seg = env[a:b]
        if len(seg) < 2:
            continue
        pk = int(np.argmax(seg[: max(2, len(seg) // 3)]))
        under = np.flatnonzero(20 * np.log10(seg[pk:] / seg[pk]) < -12)
        lengths.append(((under[0] + pk) if len(under) else len(seg)) / fps / beat_s)
    return round(float(np.median(lengths)), 2) if lengths else None


def stem_profile(name: str, stem: np.ndarray, mix: np.ndarray, beats: np.ndarray, bar_t: np.ndarray) -> dict:
    import librosa

    mono = stem.mean(axis=0)
    whole_mix, whole = lufs(mix), lufs(stem)
    blocks = _blocks(bar_t)
    tl = timeline(stem, mix, blocks)
    env = librosa.onset.onset_strength(y=mono, sr=SR, hop_length=HOP)
    onsets = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, units="time", backtrack=False)
    beat_s = float(np.median(np.diff(beats))) if len(beats) > 2 else 0.5
    active = [v for v in tl if v is not None]
    out = {
        "lu_vs_mix": None if whole is None or whole_mix is None else round(whole - whole_mix, 1),
        "active_share": round(len(active) / max(1, len(tl)), 2),
        "timeline_db_per_4_bars": tl,
        "rhythm": rhythm(onsets, bar_t),
        "groove": groove(onsets, beats),
        "note_length_beats": note_length(mono, onsets, beat_s),
        "bands_db": band_shares(mono),
        "centroid_hz": int(np.median(librosa.feature.spectral_centroid(y=mono, sr=SR, hop_length=HOP * 4))),
        "width_side_vs_mid_db": round(_db(float(np.std((stem[0] - stem[1]) / 2))) - _db(float(np.std(mono))), 1),
    }
    if name not in ("drums",):
        out["pitch"] = pitch_profile(mono)
    return out


def arrangement_image(stems: dict[str, np.ndarray], mix: np.ndarray, bar_t: np.ndarray, path: Path, title: str) -> None:
    """Stems over time: one row per stem, each bar's level against the mix (darker = louder)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = list(stems)
    blocks = _blocks(bar_t, 1)
    grid = np.array([[v if v is not None else -45 for v in timeline(stems[n], mix, blocks)] for n in names])
    fig, ax = plt.subplots(figsize=(14, 0.5 * len(names) + 1.2))
    ax.imshow(grid, aspect="auto", cmap="magma", vmin=-35, vmax=0, interpolation="nearest")
    ax.set_yticks(range(len(names)), names)
    ax.set_xticks(range(0, len(blocks), 4), [str(i) for i in range(0, len(blocks), 4)])
    ax.set_xlabel("bar")
    ax.set_title(title + " (each bar: stem level against the mix, -35..0 dB)")
    fig.tight_layout()
    fig.savefig(path, dpi=90)
    plt.close(fig)


def spectrogram_image(x: np.ndarray, a: float, b: float, path: Path, title: str) -> None:
    """A log-frequency spectrogram (30 Hz-16 kHz) of seconds a..b."""
    import librosa
    import librosa.display
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    seg = x.mean(axis=0)[int(a * SR):int(b * SR)]
    S = librosa.amplitude_to_db(np.abs(librosa.stft(seg, n_fft=4096, hop_length=HOP)), ref=np.max)
    fig, ax = plt.subplots(figsize=(12, 4))
    librosa.display.specshow(S, sr=SR, hop_length=HOP, x_axis="time", y_axis="log", ax=ax, vmin=-80, vmax=0, cmap="magma")
    ax.set_ylim(30, 16000)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)


def profile(song_dir: Path, mix_path: Path, images: bool = True) -> dict:
    """Profile every stem in <song_dir>/stems6 against the mix; writes profile.json, profile.md and img/."""
    mix = load(mix_path)
    stems = {}
    for n in STEMS6:
        p = song_dir / "stems6" / f"{n}.wav"
        if p.exists():
            s = load(p)
            k = min(s.shape[1], mix.shape[1])
            stems[n] = np.pad(s[:, :k], ((0, 0), (0, mix.shape[1] - k)))
    g = beat_grid(mix.mean(axis=0))
    beats = g["beats"]
    a_json = song_dir / "analysis.json"
    phase = json.loads(a_json.read_text())["downbeat_phase"] if a_json.exists() else 0
    bar_t = np.r_[beats[phase::4], mix.shape[1] / SR]
    out = {"file": mix_path.name, "bpm": g["bpm"], "bars": len(bar_t) - 1,
           "stems": {n: stem_profile(n, s, mix, beats, bar_t) for n, s in stems.items()}}
    if images and stems:
        img = song_dir / "img"
        img.mkdir(exist_ok=True)
        arrangement_image(stems, mix, bar_t, img / "arrangement.png", mix_path.stem)
        # the loudest 8 bars: where everything plays
        lv = [lufs(mix[:, int(a * SR):int(b * SR)]) or -99 for a, b in _blocks(bar_t, 8)]
        a, b = _blocks(bar_t, 8)[int(np.argmax(lv))]
        out["loudest_8_bars_s"] = [round(a, 1), round(b, 1)]
        spectrogram_image(mix, a, b, img / "mix.png", f"{mix_path.stem}: mix, {a:.0f}-{b:.0f} s")
        for n, s in stems.items():
            spectrogram_image(s, a, b, img / f"{n}.png", f"{mix_path.stem}: {n}, {a:.0f}-{b:.0f} s")
    (song_dir / "profile.json").write_text(json.dumps(out, indent=1, default=float))
    (song_dir / "profile.md").write_text(profile_md(out), encoding="utf-8")
    return out


NOTE = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def _name(m: int) -> str:
    return f"{NOTE[m % 12]}{m // 12 - 1}"


def profile_md(r: dict) -> str:
    lines = [f"# {r['file']}: instrument profile", "", f"{r['bpm']} BPM, {r['bars']} bars.", "",
             "| Stem | LU vs mix | Plays | Onsets/bar | Note length (beats) | Register (p10-p50-p90) | Notes at once | "
             "Centroid Hz | Width dB |", "|---|---|---|---|---|---|---|---|---|"]
    for n, s in r["stems"].items():
        p = s.get("pitch") or {}
        reg = "-".join(_name(m) for m in p["midi_p10_p50_p90"]) if p.get("midi_p10_p50_p90") else ""
        lines.append(f"| {n} | {s['lu_vs_mix']} | {s['active_share'] * 100:.0f}% | {s['rhythm']['onsets_per_active_bar']} | "
                     f"{s['note_length_beats']} | {reg} | {p.get('notes_at_once', '')} | {s['centroid_hz']} | "
                     f"{s['width_side_vs_mid_db']} |")
    lines += ["", "Level per 4 bars against the mix (dB; blank = silent):", ""]
    for n, s in r["stems"].items():
        lines.append(f"- {n}: " + " ".join("." if v is None else f"{v:.0f}" for v in s["timeline_db_per_4_bars"]))
    lines += ["", "Where onsets fall in the bar (16 steps, % of onsets):", ""]
    for n, s in r["stems"].items():
        lines.append(f"- {n}: " + " ".join(f"{v * 100:.0f}" for v in s["rhythm"]["step_share"]))
    return "\n".join(lines) + "\n"
