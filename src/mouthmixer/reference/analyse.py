"""Analyse a reference song: tempo and beat grid, downbeats, key, chords, sections, loudness and tone per
section, groove feel, density over time; with stems (vocals, drums, bass, other) also the level of each
stem per section, the vocal's range and tone, the bassline's movement and the drum pattern.

`python -m mouthmixer analyse <file or folder> [--stems]` writes analysis.json and summary.md per song to
<library>/analysis/<song>/. Numbers about tendencies only (docs/REFERENCE_ANALYSIS.md): nothing here stores
a melody or riff to copy. Values are measurements by simple, documented methods; the "?" labels (intro?,
chorus?) are guesses.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

SR = 44100
HOP = 512
STEM_NAMES = ("vocals", "drums", "bass", "other", "piano", "guitar")
BANDS = [("sub", 20, 60), ("bass", 60, 250), ("low_mid", 250, 500), ("mid", 500, 2000), ("presence", 2000, 6000),
         ("air", 6000, 16000)]
QUALITIES = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10],
             "dim": [0, 3, 6], "sus4": [0, 5, 7]}
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
ROMAN = ["I", "bII", "II", "bIII", "III", "IV", "#IV", "V", "bVI", "VI", "bVII", "VII"]


# --------------------------------------------------------------------------------------------------
# Loading and small helpers
# --------------------------------------------------------------------------------------------------

def load(path: Path) -> np.ndarray:
    """Stereo float32 (2, n) at SR."""
    import librosa

    y, _ = librosa.load(str(path), sr=SR, mono=False)
    y = np.atleast_2d(y).astype(np.float32)
    return np.vstack([y, y]) if y.shape[0] == 1 else y[:2]


def _db(x: float) -> float:
    return float(20 * np.log10(max(x, 1e-12)))


def lufs(x: np.ndarray) -> float | None:
    """Integrated loudness (BS.1770) of a (2, n) or (n,) signal; None when too short or silent."""
    import pyloudnorm as pyln

    if x.shape[-1] < int(0.5 * SR):
        return None
    v = pyln.Meter(SR).integrated_loudness(x.T if x.ndim == 2 else x)
    return round(float(v), 1) if np.isfinite(v) and v > -70 else None


def band_shares(mono: np.ndarray) -> dict:
    """Each band's share of the energy, in dB (0 = all of it)."""
    from scipy.signal import welch

    if len(mono) < 4096:
        return {}
    f, p = welch(mono, SR, nperseg=4096)
    tot = p[(f >= 20) & (f < 16000)].sum() + 1e-20
    return {name: round(10 * np.log10(p[(f >= lo) & (f < hi)].sum() / tot + 1e-12), 1) for name, lo, hi in BANDS}


def slug(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-") or "song"


# --------------------------------------------------------------------------------------------------
# Rhythm: tempo, beats, downbeats, feel
# --------------------------------------------------------------------------------------------------

def beat_grid(mono: np.ndarray) -> dict:
    """Tempo and beat times (librosa's dynamic-programming beat tracker on a median onset envelope)."""
    import librosa

    env = librosa.onset.onset_strength(y=mono, sr=SR, hop_length=HOP, aggregate=np.median)
    _, frames = librosa.beat.beat_track(onset_envelope=env, sr=SR, hop_length=HOP, tightness=100, trim=False)
    times = librosa.frames_to_time(frames, sr=SR, hop_length=HOP)
    ibi = np.diff(times)
    bpm = 60.0 / float(np.median(ibi)) if len(ibi) else 0.0
    if len(ibi):
        # Quiet intros and outros: the tracker can leave them without beats; carry the grid through them.
        step, end = float(np.median(ibi)), len(mono) / SR
        before = np.arange(times[0] - step, -step / 2, -step)[::-1]
        after = np.arange(times[-1] + step, end - step / 2, step)
        times = np.r_[before[before >= 0], times, after]
        ibi = np.diff(times)
    return {"bpm": round(bpm, 1), "beats": times, "tempo_drift_pct": round(float(np.std(ibi) / np.mean(ibi) * 100), 2)
            if len(ibi) > 4 else None, "onset_env": env}


def downbeat_phase(mono: np.ndarray, beats: np.ndarray, beat_chroma: np.ndarray) -> int:
    """Which beat of every four starts a bar: the phase where the kick (lows under 150 Hz) and the chord
    changes land most."""
    import librosa

    if len(beats) < 8:
        return 0
    mel = librosa.feature.melspectrogram(y=mono, sr=SR, hop_length=HOP, n_mels=32, fmax=150)
    low = librosa.onset.onset_strength(S=librosa.power_to_db(mel), sr=SR, hop_length=HOP)
    bf = np.clip(librosa.time_to_frames(beats, sr=SR, hop_length=HOP), 0, len(low) - 1)
    kick = np.array([low[max(0, f - 2):f + 3].max() for f in bf])
    change = np.r_[0, np.linalg.norm(np.diff(beat_chroma, axis=1), axis=0)] if beat_chroma.shape[1] == len(beats) else np.zeros(len(beats))
    z = lambda v: (v - v.mean()) / (v.std() + 1e-9)  # noqa: E731
    s = z(kick) + z(change)
    return int(np.argmax([s[k::4].mean() for k in range(4)]))


def groove(onsets: np.ndarray, beats: np.ndarray) -> dict:
    """Where onsets fall inside the beat: the off-beat 8th's position (0.50 straight, ~0.67 swung) and
    the share of onsets on 16th off-beats (busy funk/pop) and of onsets far from any 16th (loose/human)."""
    if len(beats) < 4 or not len(onsets):
        return {}
    i = np.searchsorted(beats, onsets) - 1
    ok = (i >= 0) & (i < len(beats) - 1)
    ph = (onsets[ok] - beats[i[ok]]) / (beats[i[ok] + 1] - beats[i[ok]])
    mid = ph[(ph > 0.35) & (ph < 0.8)]
    six = np.abs(ph * 4 - np.round(ph * 4))
    return {"offbeat_8th_position": round(float(np.median(mid)), 3) if len(mid) > 8 else None,
            "on_16th_offbeats": round(float(np.mean((np.round(ph * 4) % 2 == 1) & (six < 0.15))), 3),
            "off_grid": round(float(np.mean(six > 0.2)), 3)}


# --------------------------------------------------------------------------------------------------
# Harmony: key and chords
# --------------------------------------------------------------------------------------------------

def chord_templates() -> tuple[list[str], np.ndarray]:
    names, rows = [], []
    for root in range(12):
        for q, ints in QUALITIES.items():
            v = np.zeros(12)
            for k, iv in enumerate(ints):
                v[(root + iv) % 12] = 1.0 if k < 3 else 0.7
            names.append(f"{root}:{q}")
            rows.append(v / np.linalg.norm(v))
    return names, np.array(rows)


def roman(root: int, q: str, tonic: int) -> str:
    r = ROMAN[(root - tonic) % 12]
    base = r.lower() if q in ("m", "m7", "dim") else r
    return base + {"": "", "m": "", "7": "7", "maj7": "maj7", "m7": "7", "dim": "°", "sus4": "sus4"}[q]


def chords(beat_chroma: np.ndarray, tonic: int, per: int = 2) -> list[dict]:
    """A chord every `per` beats by template matching (triads, 7ths, dim, sus4); repeats merged.
    Approximate: inversions and extensions are read as the nearest of these."""
    names, T = chord_templates()
    out: list[dict] = []
    n = beat_chroma.shape[1]
    for b in range(0, n - per + 1, per):
        c = beat_chroma[:, b:b + per].mean(axis=1)
        if c.sum() <= 1e-6:
            continue
        s = T @ (c / (np.linalg.norm(c) + 1e-9))
        k = int(np.argmax(s))
        root, q = names[k].split(":")
        root = int(root)
        name = NAMES[root] + q
        if out and out[-1]["name"] == name and out[-1]["beat"] + out[-1]["beats"] == b:
            out[-1]["beats"] += per
        else:
            out.append({"beat": b, "beats": per, "name": name, "roman": roman(root, q, tonic),
                        "fit": round(float(s[k]), 2)})
    return out


def harmony_stats(ch: list[dict], bpm: float) -> dict:
    if not ch:
        return {}
    lens = np.array([c["beats"] for c in ch])
    from collections import Counter

    numerals = Counter()
    for c in ch:
        numerals[c["roman"]] += c["beats"]
    total = sum(numerals.values())
    moves = Counter(f"{a['roman']}→{b['roman']}" for a, b in zip(ch, ch[1:]))
    return {"beats_per_chord_median": float(np.median(lens)), "chords_per_minute": round(len(ch) / (lens.sum() * 60 / bpm) * 60, 1),
            "share_by_numeral": {k: round(v / total, 3) for k, v in numerals.most_common(10)},
            "sevenths_share": round(sum(c["beats"] for c in ch if "7" in c["roman"]) / total, 3),
            "common_moves": dict(moves.most_common(8))}


# --------------------------------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------------------------------

def bar_features(mono: np.ndarray, beats: np.ndarray, phase: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per bar: (bar start times, chroma+timbre features, rms dB)."""
    import librosa

    starts = beats[phase::4]
    bf = librosa.time_to_frames(starts, sr=SR, hop_length=HOP)
    chroma = librosa.feature.chroma_cqt(y=mono, sr=SR, hop_length=HOP)
    mfcc = librosa.feature.mfcc(y=mono, sr=SR, hop_length=HOP, n_mfcc=13)
    rms = librosa.feature.rms(y=mono, hop_length=HOP)[0]
    bounds = np.r_[bf, chroma.shape[1]]
    feats, levels = [], []
    for a, b in zip(bounds[:-1], bounds[1:]):
        b = max(b, a + 1)
        c = chroma[:, a:b].mean(axis=1)
        m = mfcc[1:, a:b].mean(axis=1)
        feats.append(np.r_[c / (np.linalg.norm(c) + 1e-9), m / (np.linalg.norm(m) + 1e-9)])
        levels.append(_db(float(np.sqrt(np.mean(rms[a:b] ** 2)))))
    return starts, np.array(feats), np.array(levels)


def sections(feats: np.ndarray, levels: np.ndarray, min_bars: int = 4) -> list[dict]:
    """Section boundaries from a novelty curve (checkerboard kernel on the bar self-similarity matrix,
    4 bars each side), preferring boundaries on 4-bar lines; segments labelled A, B, C... by similarity."""
    n = len(feats)
    if n < 2 * min_bars:
        return [{"bar": 0, "bars": n, "label": "A"}]
    f = feats - feats.mean(axis=0)
    f = f / (np.linalg.norm(f, axis=1, keepdims=True) + 1e-9)
    S = f @ f.T
    k = 4
    nov = np.zeros(n)
    for i in range(k, n - k + 1):
        a, b = S[i - k:i, i - k:i], S[i:i + k, i:i + k]
        x = S[i - k:i, i:i + k]
        nov[i] = (a.mean() + b.mean()) / 2 - x.mean()
    lev = np.r_[0, np.abs(np.diff(levels))]
    score = nov / (nov.max() + 1e-9) + 0.5 * lev / (lev.max() + 1e-9)
    score = score + 0.15 * (np.arange(n) % 4 == 0)  # phrases usually change on 4-bar lines
    cut = [0]
    for i in np.argsort(-score):
        if score[i] < 0.45:
            break
        if all(abs(i - c) >= min_bars for c in cut) and n - i >= min_bars:
            cut.append(int(i))
    cut = sorted(cut) + [n]
    segs = [{"bar": a, "bars": b - a} for a, b in zip(cut[:-1], cut[1:])]
    protos: list[np.ndarray] = []
    for s in segs:
        v = feats[s["bar"]:s["bar"] + s["bars"]].mean(axis=0)
        v = v / (np.linalg.norm(v) + 1e-9)
        sims = [float(v @ p) for p in protos]
        if sims and max(sims) > 0.985:
            s["label"] = chr(65 + int(np.argmax(sims)))
        else:
            protos.append(v)
            s["label"] = chr(65 + len(protos) - 1) if len(protos) <= 26 else "Z"
    return segs


def guess_names(secs: list[dict]) -> None:
    """'intro?', 'chorus?', 'outro?' from position, loudness and repetition (guesses, marked with ?)."""
    if not secs:
        return
    loud = [s.get("lufs") or -60 for s in secs]
    from collections import Counter

    count = Counter(s["label"] for s in secs)
    rep_loud = sorted({s["label"] for s in secs if count[s["label"]] > 1},
                      key=lambda lab: -np.mean([l for s, l in zip(secs, loud) if s["label"] == lab]))
    chorus = rep_loud[0] if rep_loud else None
    for i, s in enumerate(secs):
        s["guess"] = ("chorus?" if s["label"] == chorus else
                      "intro?" if i == 0 and loud[0] < np.median(loud) else
                      "outro?" if i == len(secs) - 1 and loud[-1] < np.median(loud) else
                      "verse?" if count[s["label"]] > 1 else "")


# --------------------------------------------------------------------------------------------------
# Stems
# --------------------------------------------------------------------------------------------------

def find_stems(folder: Path) -> dict[str, Path]:
    """Stems already separated (by `separate`, or by any tool such as UVR, saved as vocals.wav etc.)."""
    return {n: folder / f"{n}.wav" for n in STEM_NAMES if (folder / f"{n}.wav").exists()}


def separate(path: Path, folder: Path, model: str = "htdemucs") -> dict[str, Path]:
    """Split a song into stems with Demucs (MIT licence; optional install: pip install demucs)."""
    try:
        import torch
        from demucs.apply import apply_model
        from demucs.pretrained import get_model
    except ImportError as e:
        raise RuntimeError("stem separation needs Demucs: pip install demucs (it brings PyTorch, ~250 MB), or put "
                           f"vocals.wav, drums.wav, bass.wav, other.wav from another tool into {folder}") from e
    import soundfile as sf

    m = get_model(model)
    m.eval()
    x = load(path)
    import librosa

    x = np.stack([librosa.resample(c, orig_sr=SR, target_sr=m.samplerate) for c in x]) if m.samplerate != SR else x
    ref = x.mean(axis=0)
    wav = torch.from_numpy((x - ref.mean()) / (ref.std() + 1e-8))
    torch.set_num_threads(max(1, __import__("os").cpu_count() - 2))
    with torch.no_grad():
        out = apply_model(m, wav[None], device="cpu", split=True, overlap=0.25, progress=False)[0]
    out = out.numpy() * (ref.std() + 1e-8) + ref.mean()
    folder.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, s in zip(m.sources, out):
        p = folder / f"{name}.wav"
        sf.write(str(p), s.T, m.samplerate, subtype="FLOAT")
        paths[name] = p
    return paths


def _f0_notes(mono: np.ndarray, fmin: float, fmax: float) -> tuple[np.ndarray, np.ndarray]:
    """pYIN pitch (MIDI, NaN where unvoiced) every 10 ms at 22.05 kHz."""
    import librosa

    y = librosa.resample(mono, orig_sr=SR, target_sr=22050)
    f0, voiced, _ = librosa.pyin(y, fmin=fmin, fmax=fmax, sr=22050, frame_length=2048, hop_length=220)
    t = librosa.times_like(f0, sr=22050, hop_length=220)
    m = np.where(voiced & np.isfinite(f0), 69 + 12 * np.log2(np.maximum(np.nan_to_num(f0), 1e-6) / 440), np.nan)
    return t, m


def _note_onsets(t: np.ndarray, m: np.ndarray) -> np.ndarray:
    """Note starts: a voiced run starting, or the pitch settling a semitone or more away."""
    v = np.isfinite(m)
    on = []
    prev = None
    for i in range(len(m)):
        if not v[i]:
            prev = None
            continue
        if prev is None or abs(m[i] - prev) >= 0.8:
            if not on or t[i] - on[-1] > 0.08:
                on.append(t[i])
            prev = m[i]
        else:
            prev = 0.8 * prev + 0.2 * m[i]
    return np.array(on)


def vocal_facts(x: np.ndarray, mix: np.ndarray, beats: np.ndarray) -> dict:
    """The vocal stem: range, how much of the time it sings, note rate and syncopation, its tone (bands
    against 200-1000 Hz, the same measure as VOCALS §13) and how far it stands above the band in 1-4 kHz."""
    from scipy.signal import butter, sosfiltfilt, welch

    mono = x.mean(axis=0)
    t, m = _f0_notes(mono, 70, 1100)
    v = np.isfinite(m)
    out: dict = {"sung_share": round(float(v.mean()), 3)}
    if v.sum() > 50:
        out.update({"range_midi_p5_p95": [round(float(np.percentile(m[v], 5)), 1), round(float(np.percentile(m[v], 95)), 1)],
                    "median_midi": round(float(np.median(m[v])), 1)})
        on = _note_onsets(t, m)
        if len(on) and len(beats) > 4:
            sung_s = v.sum() * (t[1] - t[0])
            out["notes_per_sung_second"] = round(len(on) / max(sung_s, 1e-6), 2)
            out["groove"] = groove(on, beats)
    f, p = welch(mono, SR, nperseg=4096)
    ref = p[(f >= 200) & (f < 1000)].mean() + 1e-20
    out["tone_vs_200_1000hz_db"] = {k: round(float(10 * np.log10(p[(f >= lo) & (f < hi)].mean() / ref)), 1)
                                    for k, (lo, hi) in {"3-6k": (3000, 6000), "6-10k": (6000, 10000), "10-16k": (10000, 16000)}.items()}
    sos = butter(2, [1000, 4000], "band", fs=SR, output="sos")
    vb, rest = sosfiltfilt(sos, mono), sosfiltfilt(sos, (mix - x).mean(axis=0))
    env = np.convolve(mono ** 2, np.ones(4410) / 4410, mode="same")
    on_mask = env > np.percentile(env, 60)
    if on_mask.sum() > SR:
        out["above_band_1_4k_db"] = round(_db(np.sqrt(np.mean(vb[on_mask] ** 2))) - _db(np.sqrt(np.mean(rest[on_mask] ** 2))), 1)
    return out


def bass_facts(x: np.ndarray, beats: np.ndarray, phase: int, ch: list[dict], tonic: int) -> dict:
    mono = x.mean(axis=0)
    t, m = _f0_notes(mono, 30, 400)
    v = np.isfinite(m)
    if v.sum() < 50:
        return {}
    on = _note_onsets(t, m)
    bars = max(1, len(beats[phase::4]))
    out = {"notes_per_bar": round(len(on) / bars, 2), "median_midi": round(float(np.median(m[v])), 1),
           "groove": groove(on, beats)}
    # How often the bass plays the chord's root (any octave) while that chord sounds.
    if ch and len(beats):
        hits = tot = 0
        for c in ch:
            a = beats[min(c["beat"], len(beats) - 1)]
            b = beats[min(c["beat"] + c["beats"], len(beats) - 1)]
            seg = m[(t >= a) & (t < b) & v]
            if len(seg) < 5:
                continue
            root = NAMES.index(re.match(r"[A-G][b#]?", c["name"]).group(0))
            hits += np.mean(np.round(seg) % 12 == root)
            tot += 1
        if tot:
            out["on_chord_root"] = round(float(hits / tot), 3)
    return out


def drum_facts(x: np.ndarray, beats: np.ndarray, phase: int) -> dict:
    """Kick, snare and hat onsets (by band) on a 16-step grid per bar; the most common bar pattern of each
    and how busy the hats are."""
    import librosa

    mono = x.mean(axis=0)
    S = np.abs(librosa.stft(mono, n_fft=2048, hop_length=HOP))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    starts = beats[phase::4]
    if len(starts) < 3:
        return {}
    out = {}
    for name, lo, hi in (("kick", 30, 150), ("snare", 150, 2500), ("hats", 6000, 16000)):
        band = S[(freqs >= lo) & (freqs < hi)]
        env = librosa.onset.onset_strength(S=librosa.amplitude_to_db(band), sr=SR, hop_length=HOP)
        on = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, units="time")
        pats = []
        for a, b in zip(starts[:-1], starts[1:]):
            grid = np.zeros(16, dtype=int)
            for o in on[(on >= a - 0.03) & (on < b - 0.03)]:
                grid[min(15, int(round((o - a) / (b - a) * 16)))] = 1
            pats.append("".join("x" if g else "." for g in grid))
        from collections import Counter

        common = Counter(pats).most_common(3)
        out[name] = {"common_bars": [{"pattern": p, "share": round(c / len(pats), 2)} for p, c in common],
                     "hits_per_bar": round(float(np.mean([p.count("x") for p in pats])), 2)}
    return out


# --------------------------------------------------------------------------------------------------
# The whole analysis
# --------------------------------------------------------------------------------------------------

def analyse(path: Path, stems: dict[str, Path] | None = None) -> dict:
    import librosa

    from ..analysis import key as keymod

    x = load(path)
    mono = x.mean(axis=0)
    dur = x.shape[1] / SR
    g = beat_grid(mono)
    beats, bpm = g["beats"], g["bpm"]
    bfr = librosa.time_to_frames(beats, sr=SR, hop_length=HOP)
    chroma = librosa.feature.chroma_cqt(y=mono, sr=SR, hop_length=HOP)
    beat_chroma = librosa.util.sync(chroma, bfr, aggregate=np.median)[:, :len(beats)]
    keys = keymod.detect(list(range(12)), list(chroma.mean(axis=1)))
    tonic = keys[0]["tonic"]
    phase = downbeat_phase(mono, beats, beat_chroma)
    ch = chords(beat_chroma, tonic)
    for c in ch:
        c["beat"] -= phase  # beats from the first downbeat
    starts, feats, levels = bar_features(mono, beats, phase)
    secs = sections(feats, levels)
    bar_t = np.r_[starts, dur]
    onsets = librosa.onset.onset_detect(onset_envelope=g["onset_env"], sr=SR, hop_length=HOP, units="time")
    for s in secs:
        a, b = bar_t[s["bar"]], bar_t[min(s["bar"] + s["bars"], len(bar_t) - 1)]
        seg = x[:, int(a * SR):int(b * SR)]
        mid, side = seg.mean(axis=0), (seg[0] - seg[1]) / 2
        nb = max(1, int(round((b - a) / (60 / bpm)))) if bpm else 1
        s.update({"start_s": round(float(a), 2), "seconds": round(float(b - a), 2), "lufs": lufs(seg),
                  "bands_db": band_shares(mid), "width_side_vs_mid_db": round(_db(np.std(side)) - _db(np.std(mid)), 1),
                  "onsets_per_beat": round(float(((onsets >= a) & (onsets < b)).sum() / nb), 2)})
    guess_names(secs)
    import pyloudnorm as pyln

    meter = pyln.Meter(SR)
    win, step = int(3 * SR), int(SR)
    short = [meter.integrated_loudness(x[:, i:i + win].T) for i in range(0, x.shape[1] - win, step)]
    short = np.array([v for v in short if np.isfinite(v) and v > -70])
    over = np.stack([librosa.resample(c, orig_sr=SR, target_sr=4 * SR) for c in x[:, : int(min(dur, 600) * SR)]])
    report = {
        "file": path.name, "seconds": round(dur, 1), "bpm": bpm, "tempo_drift_pct": g["tempo_drift_pct"],
        "key": keys[0]["name"], "key_alternatives": [k["name"] for k in keys[1:3]], "downbeat_phase": phase,
        "bars": len(starts),
        "loudness": {"integrated_lufs": lufs(x), "true_peak_dbfs": round(_db(float(np.abs(over).max())), 1),
                     "short_term_range_lu": round(float(np.percentile(short, 95) - np.percentile(short, 10)), 1) if len(short) > 5 else None,
                     "crest_db": round(_db(float(np.abs(x).max())) - _db(float(np.sqrt(np.mean(x ** 2)))), 1)},
        "bands_db": band_shares(mono),
        "width_side_vs_mid_db": round(_db(np.std((x[0] - x[1]) / 2)) - _db(np.std(mono)), 1),
        "groove": groove(onsets, beats),
        "sections": secs,
        "section_bars": [s["bars"] for s in secs],
        "chords": ch,
        "harmony": harmony_stats(ch, bpm),
        "density_by_bar": {"rms_db": [round(float(v), 1) for v in levels],
                           "onsets": [int(((onsets >= a) & (onsets < b)).sum()) for a, b in zip(bar_t[:-1], bar_t[1:])]},
    }
    if stems:
        report["stems"] = stem_report(stems, x, beats, phase, secs, bar_t, ch, tonic)
    return report


def stem_report(stems: dict[str, Path], mix: np.ndarray, beats, phase, secs, bar_t, ch, tonic) -> dict:
    out: dict = {"levels_by_section": []}
    loaded = {}
    for name, p in stems.items():
        s = load(p)
        n = min(s.shape[1], mix.shape[1])
        loaded[name] = np.pad(s[:, :n], ((0, 0), (0, mix.shape[1] - n)))
    for sec in secs:
        a, b = int(sec["start_s"] * SR), int((sec["start_s"] + sec["seconds"]) * SR)
        whole = lufs(mix[:, a:b])
        row = {"bar": sec["bar"], "label": sec["label"], "guess": sec.get("guess", "")}
        for name, s in loaded.items():
            v = lufs(s[:, a:b])
            row[name] = None if v is None or whole is None else round(v - whole, 1)  # LU against the full mix
        out["levels_by_section"].append(row)
    out["bands_db"] = {name: band_shares(s.mean(axis=0)) for name, s in loaded.items()}
    if "vocals" in loaded:
        out["vocals"] = vocal_facts(loaded["vocals"], mix, beats)
    if "bass" in loaded:
        out["bass"] = bass_facts(loaded["bass"], beats, phase, ch, tonic)
    if "drums" in loaded:
        out["drums"] = drum_facts(loaded["drums"], beats, phase)
    return out


def summary_md(r: dict) -> str:
    """A short readable page for one song."""
    L = r["loudness"]
    lines = [f"# {r['file']}", "",
             f"{r['bpm']} BPM (drift {r['tempo_drift_pct']}%), {r['key']} (or {', '.join(r['key_alternatives'])}), "
             f"{r['bars']} bars, {r['seconds']} s. Loudness {L['integrated_lufs']} LUFS, true peak {L['true_peak_dbfs']} dBFS, "
             f"short-term range {L['short_term_range_lu']} LU, crest {L['crest_db']} dB.", "",
             f"Groove: {r['groove']}", "", "| Bar | Bars | Label | Guess | LUFS | Onsets/beat | Width dB | Presence dB | Air dB |",
             "|---|---|---|---|---|---|---|---|---|"]
    for s in r["sections"]:
        lines.append(f"| {s['bar']} | {s['bars']} | {s['label']} | {s.get('guess', '')} | {s['lufs']} | {s['onsets_per_beat']} | "
                     f"{s['width_side_vs_mid_db']} | {s['bands_db'].get('presence')} | {s['bands_db'].get('air')} |")
    h = r.get("harmony") or {}
    if h:
        lines += ["", f"Harmony: a chord every {h['beats_per_chord_median']} beats; {h['sevenths_share'] * 100:.0f}% sevenths; "
                  f"most used: {', '.join(h['share_by_numeral'])}; common moves: {', '.join(h['common_moves'])}."]
    st = r.get("stems")
    if st:
        lines += ["", "Stem levels (LU against the full mix) by section:", "",
                  "| Bar | Label | " + " | ".join(k for k in st["levels_by_section"][0] if k not in ("bar", "label", "guess")) + " |"]
        lines.append("|---|---|" + "---|" * (len(st["levels_by_section"][0]) - 3))
        for row in st["levels_by_section"]:
            lines.append(f"| {row['bar']} | {row['label']}{' ' + row['guess'] if row['guess'] else ''} | " +
                         " | ".join(str(v) for k, v in row.items() if k not in ("bar", "label", "guess")) + " |")
        for k in ("vocals", "bass", "drums"):
            if k in st:
                lines += ["", f"{k.capitalize()}: {json.dumps(st[k])}"]
    return "\n".join(lines) + "\n"


def run(target: Path, out_root: Path, with_stems: bool = False) -> list[dict]:
    """Analyse one file or every audio file in a folder; writes <out_root>/<song>/analysis.json and
    summary.md (and stems/ when separating) and returns the reports."""
    files = [target] if target.is_file() else sorted(p for p in target.iterdir()
                                                    if p.suffix.lower() in (".flac", ".wav", ".mp3", ".ogg", ".m4a"))
    reports = []
    for f in files:
        out = out_root / slug(f)
        stem_dir = out / "stems"
        stems = find_stems(stem_dir)
        if with_stems and not stems:
            stems = separate(f, stem_dir)
        r = analyse(f, stems or None)
        out.mkdir(parents=True, exist_ok=True)
        (out / "analysis.json").write_text(json.dumps(r, indent=1, default=float))
        (out / "summary.md").write_text(summary_md(r), encoding="utf-8")
        reports.append(r)
        print(f"{f.name}: {r['bpm']} BPM, {r['key']}, sections {r['section_bars']} -> {out}", flush=True)
    return reports
