"""The critic (PLAN.md §7.11): checks every candidate against docs/MUSIC_KNOWLEDGE.md before the user hears
anything. Rule ids in comments match that file. Hard rejects first, then scores per area, combined with
the §10 default weights.

Also here: `clip_quality`, the "is this clip musically sound?" check used when the detector is unsure.
"""

from __future__ import annotations

import numpy as np

from . import theory
from .arranger import Song
from .render import SR
from .styles import DRUM, INSTRUMENTS, PACKS

WEIGHTS = {"melody": 0.20, "harmony": 0.15, "bass": 0.08, "rhythm": 0.15, "form": 0.10, "arrangement": 0.12,
           "mix": 0.12, "game": 0.08}


def melody_rules(notes: list[tuple]) -> dict:
    """M1-M3, M7, M15 on a list of (start, length, pitch, vel). Returns a score 0-1 and the measurements."""
    if len(notes) < 3:
        return {"score": 0.0, "reasons": ["too few notes"]}
    ps = [p for _, _, p, _ in notes]
    ivs = np.diff(ps)
    reasons = []
    rng_ = max(ps) - min(ps)
    s_range = 1.0 if rng_ <= 15 else 0.6 if rng_ <= 19 else 0.2  # M1
    if rng_ > 19:
        reasons.append(f"very wide range ({rng_} semitones)")
    steps = float(np.mean(np.abs(ivs) <= 2)) if len(ivs) else 1.0
    s_steps = 1.0 if 0.45 <= steps <= 0.92 else 0.6  # M2 (repeated notes count as steps)
    big = [i for i, d in enumerate(ivs[:-1]) if abs(d) > 5]
    filled = sum(1 for i in big if np.sign(ivs[i + 1]) != np.sign(ivs[i]) or ivs[i + 1] == 0)
    s_gap = 1.0 if not big else filled / len(big)  # M3
    # M7: a motif that returns (1-bar windows of intervals + rhythm).
    windows = {}
    for s, l, p, _ in notes:
        bar = int(s // 4)
        windows.setdefault(bar, []).append((round(s % 4, 2), p))
    sigs = [tuple((t, p - w[0][1]) for t, p in w) for w in windows.values() if len(w) >= 2]
    repeats = len(sigs) - len(set(sigs))
    s_motif = 1.0 if repeats >= 1 or len(sigs) <= 2 else 0.6
    # M15: breathing room.
    longest_run = 0.0
    run_start = notes[0][0]
    for (s, l, _, _), (s2, _, _, _) in zip(notes, notes[1:]):
        if s2 - (s + l) >= 0.5 or l >= 1.0:
            run_start = s2
        longest_run = max(longest_run, s2 - run_start)
    s_breath = 1.0 if longest_run <= 16 else 0.6
    score = 0.25 * s_range + 0.2 * s_steps + 0.2 * s_gap + 0.2 * s_motif + 0.15 * s_breath
    return {"score": round(float(score), 3), "range": int(rng_), "steps": round(steps, 2),
            "gap_fill": round(float(s_gap), 2), "motif_repeats": repeats, "reasons": reasons}


def _notes_at(track_notes, beat):
    return [n for n in track_notes if n[0] <= beat < n[0] + n[1]]


def judge(song: Song, mix: np.ndarray | None = None, stems: dict | None = None) -> dict:
    pack = PACKS[song.pack]
    rejects: list[str] = []
    notes: list[str] = []
    by_role: dict[str, list] = {}
    for t in song.tracks:
        by_role.setdefault(t.role, []).extend(t.notes)

    # --- A4: every part inside its instrument's range ----------------------------------------------
    for t in song.tracks:
        if t.instrument.startswith(("kit:", "fx:")) or not t.notes:
            continue
        lo, hi = INSTRUMENTS[t.instrument][2:4]
        out = sum(1 for _, _, p, _ in t.notes if not lo <= p <= hi)
        if out / len(t.notes) > 0.05:
            rejects.append(f"{t.name} goes outside the {t.instrument.replace('_', ' ')}'s range")

    # --- H1 / M11: melody against the chords ------------------------------------------------------
    lead = sorted(by_role.get("lead", []))
    strong, chord_tone, hard, soft = 0, 0, 0, 0
    for s, l, p, _ in lead:
        c = song.chord_at(round(s * 4) / 4 + 1e-6)
        if c is None:
            continue
        on_beat = abs(s - round(s)) < 0.05
        if not on_beat:
            continue
        strong += 1
        f = c.fit(p % 12, pack["tension"])
        if f >= 1.0:
            chord_tone += 1
        if f < 0:
            if l >= 1.0 and f <= -1.0:
                hard += 1
            else:
                soft += 1
        # A held melody note a half step from a chord-part note sounding at the same time.
        if l >= 1.0:
            for cs, cl, cp, _ in _notes_at(by_role.get("comp", []), round(s * 4) / 4 + 1e-6):
                # A minor 2nd, or a minor 9th with the melody on top. (Melody a semitone *below* a chord note
                # an octave or more down is a major 7th: consonant, it's the maj7 sound.)
                d = p - cp
                minor_second = abs(d) == 1 or (d > 0 and d % 12 == 1)
                if minor_second and c.fit(cp % 12, pack["tension"]) >= 1.0 and c.fit(p % 12, 0) < 1.0:
                    hard += 1
                    break
    ct_share = chord_tone / strong if strong else 1.0
    if hard >= 2 or (strong and hard / strong > 0.06):
        rejects.append(f"{hard} clashing melody notes")
    target = 0.5 if pack["tension"] >= 0.7 else 0.65
    s_harm_fit = min(1.0, ct_share / target) - 0.08 * soft / max(1, strong) * 10

    # --- H2 / H6: progression flow and voice leading --------------------------------------------------
    chords = [c for _, _, c in song.chords]
    flow = [theory.transition(a, b) for a, b in zip(chords, chords[1:]) if a != b]
    s_flow = float(np.clip((np.mean(flow) + 0.2) / 1.2, 0, 1)) if flow else 0.5
    comp = sorted(by_role.get("comp", []))
    groups: dict[float, list] = {}
    for s, l, p, _ in comp:
        groups.setdefault(round(s, 3), []).append(p)
    vs = [sorted(v) for _, v in sorted(groups.items())]
    moves = [sum(min(abs(x - y) for y in b) for x in a) for a, b in zip(vs, vs[1:]) if a != b]
    avg_move = float(np.mean(moves)) if moves else 0.0
    s_voice = 1.0 if avg_move <= 7 else max(0.3, 1 - (avg_move - 7) / 14)
    harmony = float(np.clip(0.5 * s_harm_fit + 0.3 * s_flow + 0.2 * s_voice, 0, 1))

    # --- B3: kick and bass lock ------------------------------------------------------------------------
    kicks = [s for s, _, p, _ in by_role.get("drums", []) if p in (DRUM["kick"], DRUM["concert_bd"])]
    bass_starts = np.array(sorted(s for s, _, _, _ in by_role.get("bass", [])))
    if kicks and len(bass_starts):
        locked = sum(1 for k in kicks if np.min(np.abs(bass_starts - k)) <= 0.13)
        lock = locked / len(kicks)
    else:
        lock = 0.7
    s_bass = float(np.clip(0.4 + lock, 0, 1))

    # --- Rhythm: clear pulse and a backbeat in the main sections (R1, R2) -----------------------------
    drums = by_role.get("drums", [])
    s_rhythm = 1.0 if len(drums) >= song.bars * 3 else 0.6

    # --- Melody (mostly the user's own; M-rules) --------------------------------------------------------
    first_a = song.sections[1] if len(song.sections) > 1 else song.sections[0]  # a one-section sting
    a_lead = [n for n in lead if first_a[1] * 4 <= n[0] < (first_a[1] + first_a[2]) * 4]
    mel = melody_rules([(s - first_a[1] * 4, l, p, v) for s, l, p, v in a_lead])

    # --- Arrangement: distinct colours, at most 3 foreground parts (A2, A5) ----------------------------
    instruments = [t.instrument for t in song.tracks if t.role not in ("drums",)]
    distinct = len(set(instruments)) / max(1, len(instruments))
    s_arr = 0.5 + 0.5 * distinct

    # --- Audio checks (X1, X4, X7, X10, X11) -----------------------------------------------------------
    mix_score, game_score = 0.7, 0.8
    details: dict = {}
    if mix is not None:
        peak_db = 20 * np.log10(np.abs(mix).max() + 1e-12)
        if peak_db > -0.8:
            rejects.append("clipping")
        corr = float(np.corrcoef(mix[0], mix[1])[0, 1])
        if corr < 0:
            rejects.append("falls apart in mono")
        spec = _band_energy(mix.mean(axis=0))
        mud = spec["mud"] / (spec["mid"] + 1e-12)
        details.update({"peak_db": round(float(peak_db), 2), "stereo_corr": round(corr, 2), "mud_ratio": round(float(mud), 2)})
        s_mud = 1.0 if mud < 2.2 else max(0.3, 1 - (mud - 2.2) / 3)
        s_lead = 0.7
        if stems and "lead" in stems:
            lead_band = _band(stems["lead"].mean(axis=0), 1000, 4000)
            rest = sum(v for k, v in stems.items() if k != "lead")
            rest_band = _band(rest.mean(axis=0), 1000, 4000) if isinstance(rest, np.ndarray) else 1e-12
            ratio_db = 10 * np.log10((lead_band + 1e-12) / (rest_band + 1e-12))
            details["lead_vs_rest_db"] = round(float(ratio_db), 1)
            if ratio_db < -4:
                rejects.append("the melody is buried")
            s_lead = float(np.clip((ratio_db + 4) / 8, 0, 1))
        if stems and "bass" in stems:
            b = stems["bass"].mean(axis=0)
            above = _band(b, 150, 2000)
            total = _band(b, 20, 2000)
            phone = above / (total + 1e-12)
            details["bass_audible_on_phones"] = round(float(phone), 3)
            if phone < 0.02:
                rejects.append("the bass disappears on phone speakers")
        mix_score = 0.4 * s_mud + 0.6 * s_lead
        length = mix.shape[1] / SR
        details["seconds"] = round(length, 1)
        game_score = 1.0 if 40 <= length <= 200 else 0.6

    sections = {
        "melody": mel["score"], "harmony": round(harmony, 3), "bass": round(s_bass, 3), "rhythm": s_rhythm,
        "form": 0.9, "arrangement": round(s_arr, 3), "mix": round(float(mix_score), 3), "game": game_score,
    }
    total = sum(WEIGHTS[k] * v for k, v in sections.items())
    if mel.get("reasons"):
        notes += mel["reasons"]
    details.update({"chord_tones_on_beats": round(ct_share, 2), "clashes": hard, "soft_clashes": soft,
                    "kick_bass_lock": round(lock, 2), "voice_leading": round(avg_move, 1),
                    "progression_flow": round(s_flow, 2)})
    return {"ok": not rejects, "score": round(float(total), 3), "rejects": rejects, "sections": sections,
            "details": details, "notes": notes}


def _band(x: np.ndarray, lo: float, hi: float) -> float:
    n = 1 << 14
    if len(x) < n:
        x = np.pad(x, (0, n - len(x)))
    frames = x[: len(x) // n * n].reshape(-1, n) * np.hanning(n)
    spec = (np.abs(np.fft.rfft(frames, axis=1)) ** 2).mean(axis=0)
    f = np.fft.rfftfreq(n, 1 / SR)
    return float(spec[(f >= lo) & (f < hi)].sum())


def _band_energy(x: np.ndarray) -> dict:
    return {"low": _band(x, 20, 200), "mud": _band(x, 200, 500), "mid": _band(x, 500, 2000), "high": _band(x, 2000, 12000)}


def clip_quality(result: dict) -> dict:
    """Does a transcribed clip follow musical rules well enough to build on? Used when the detector is
    unsure, and before making songs. Returns {"ok", "score", "reasons"}."""
    reasons = []
    scores = []
    notes = result.get("notes", [])
    drums = result.get("drums", [])
    conf = result.get("tempo", {}).get("confidence", 0.0)
    if notes:
        ps = [n["pitch"] for n in notes]
        n_ok = len(notes) >= 5 and len(set(ps)) >= 3
        if not n_ok:
            reasons.append("too few different notes for a melody")
        chrom = sum(1 for n in notes if n.get("chromatic")) / len(notes)
        key_conf = (result.get("keys") or [{}])[0].get("confidence", 0.0)
        mel = melody_rules([(n["start"], n["length"], n["pitch"], 80) for n in notes])
        raw = result.get("notes_raw", [])
        wobble = float(np.mean([abs(r["pitch"] - round(r["pitch"] - result.get("tuning_offset", 0)) -
                                    result.get("tuning_offset", 0)) for r in raw])) if raw else 0.3
        held = result.get("verdict", {}).get("scores", {}).get("plateau_frac", 0.5)
        steady = 1.0 if wobble < 0.16 else max(0.0, 1 - (wobble - 0.16) / 0.12)
        s = (0.2 * (1.0 if n_ok else 0.0) + 0.15 * min(1.0, conf / 0.6) + 0.1 * (1.0 if chrom <= 0.15 else 0.4)
             + 0.1 * min(1.0, key_conf / 0.35 + 0.3) + 0.1 * mel["score"] + 0.15 * steady + 0.2 * min(1.0, held / 0.6))
        if steady < 0.5:
            reasons.append("the pitch slides around like talking, not singing")
        # Hard requirements (measured: hums hold notes 90%+ of the time with a steady pulse; talking holds
        # under 30% with a weak one): without both it's not a melody to build on.
        if held < 0.4:
            reasons.append("notes aren't held like humming or singing")
            s = min(s, 0.45)
        if conf < 0.5:
            s = min(s, 0.5)
        if conf < 0.4:
            reasons.append("no steady rhythm")
        if chrom > 0.15:
            reasons.append("many notes outside any key")
        scores.append(s)
    if drums:
        kinds = [d["name"] for d in drums]
        n_ok = len(drums) >= 8 and kinds.count("kick") >= 2 and (kinds.count("snare") >= 2 or kinds.count("hat") >= 4)
        if not n_ok:
            reasons.append("not enough of a beat")
        s = 0.5 * (1.0 if n_ok else 0.2) + 0.5 * min(1.0, conf / 0.6)
        # Hard requirements: a beat repeats (periodic onsets) on a steady grid. Talking has syllable
        # "hits" too, but they don't repeat (measured: beatbox periodicity 0.5+, talking about 0.2).
        period = result.get("verdict", {}).get("scores", {}).get("periodicity", 0.5)
        if conf < 0.55 or period < 0.32:
            reasons.append("the hits don't repeat like a beat")
            s = min(s, 0.45)
        scores.append(s)
    score = max(scores) if scores else 0.0
    return {"ok": score >= 0.6, "score": round(float(score), 3), "reasons": reasons}
