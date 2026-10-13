"""From clips to finished songs (PLAN.md §7.7, §7.11): make many candidates (styles x seeds x clip
combinations), filter them with the critic, render the best few, check the audio, and keep the winner and
two alternatives. Nothing reaches the inbox unless it passed."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import arranger, critic, render
from .styles import DEFAULT_PACKS, PACKS


@dataclass
class ClipInfo:
    id: str
    result: dict  # pipeline result
    created: float = 0.0

    @property
    def has_melody(self) -> bool:
        return len(self.result.get("notes", [])) >= 5

    @property
    def has_beat(self) -> bool:
        return len(self.result.get("drums", [])) >= 8

    @property
    def bpm(self) -> float:
        return float(self.result.get("tempo", {}).get("bpm") or 100.0)


def _tempo_ok(a: float, b: float) -> bool:
    """Two clips can share a song if their tempos match within 8%, or at half/double (PLAN §7.2)."""
    for f in (0.5, 1.0, 2.0):
        if abs(a * f / b - 1) <= 0.08:
            return True
    return False


def candidates(primary: ClipInfo, others: list[ClipInfo], n: int, rng, packs: list[str] | None = None,
               exclude_pack: str | None = None) -> list[dict]:
    """Specs to try. Mixes styles (the decided three most often, the rest for range) and clip
    combinations: alone, + a matching beat, + another melody as the B section."""
    pool = packs or (DEFAULT_PACKS * 2 + [p for p in PACKS if p not in DEFAULT_PACKS])
    pool = [p for p in pool if p != exclude_pack] or list(PACKS)
    beats = [c for c in others if c.has_beat and c.id != primary.id]
    melodies = [c for c in others if c.has_melody and c.id != primary.id]
    specs = []
    for i in range(n):
        spec = {"pack": pool[rng.integers(len(pool))], "seed": int(rng.integers(1 << 30)), "clips": [primary.id]}
        if primary.has_melody:
            spec["melody"] = primary.id
            if primary.has_beat:
                spec["beat"] = primary.id
            elif beats and rng.random() < 0.5:
                b = beats[rng.integers(len(beats))]
                spec["beat"] = b.id
                spec["clips"].append(b.id)
            if melodies and rng.random() < 0.3:
                m = melodies[rng.integers(len(melodies))]
                spec["partner"] = m.id
                spec["clips"].append(m.id)
        else:  # a beat on its own: pair it with one of your melodies when the tempo fits, else compose one
            spec["beat"] = primary.id
            fits = [m for m in melodies if _tempo_ok(m.bpm, primary.bpm)]
            if fits and rng.random() < 0.7:
                m = fits[rng.integers(len(fits))]
                spec["melody"] = m.id
                spec["clips"].append(m.id)
        specs.append(spec)
    return specs


def build(spec: dict, clips: dict[str, ClipInfo]) -> arranger.Song:
    mel = clips.get(spec.get("melody")) if spec.get("melody") else None
    beat = clips.get(spec.get("beat")) if spec.get("beat") else None
    partner = clips.get(spec.get("partner")) if spec.get("partner") else None
    key = (mel.result.get("key") if mel else None) or {"tonic": int(np.random.default_rng(spec["seed"]).integers(12)),
                                                       "mode": "minor" if spec["pack"] in ("neon_night", "acid_jazz_battle") else "major"}
    return arranger.arrange(
        pack_name=spec["pack"], seed=spec["seed"],
        melody=mel.result["notes"] if mel else None, clip_bpm=mel.bpm if mel else None, key=key,
        beat=beat.result.get("drums") if beat else None, beat_bpm=beat.bpm if beat else None,
        partner_melody=partner.result["notes"] if partner else None,
        partner_key=partner.result.get("key") if partner else None,
    )


def title(song: arranger.Song, primary: ClipInfo) -> str:
    when = time.strftime("%a %H:%M", time.localtime(primary.created or time.time()))
    return f"{PACKS[song.pack]['title']} in {song.key_name} · from your {when} clip"


def song_summary(song: arranger.Song) -> dict:
    """What the app shows: sections, chords, and every part with its notes (for the score view)."""
    return {
        "pack": song.pack, "style": PACKS[song.pack]["title"], "describe": PACKS[song.pack]["describe"],
        "bpm": song.bpm, "key": song.key_name, "bars": song.bars,
        "sections": [{"name": n, "start": s, "bars": b} for n, s, b in song.sections],
        "chords": [{"start": round(s, 3), "length": round(l, 3), "name": c.name, "degree": c.degree,
                    "root": c.root, "quality": c.quality} for s, l, c in song.chords],
        "tracks": [{"name": t.name, "role": t.role, "instrument": t.instrument.replace("kit:", "").replace("_", " ")
                    + (" drum kit" if t.instrument.startswith("kit:") else ""), "key": t.instrument, "mine": t.mine,
                    "notes": [[round(s, 3), round(l, 3), int(p), int(v)] for s, l, p, v in t.notes]}
                   for t in song.tracks],
        "added": song.notes_for_user,
        "sources": song.sources,
    }


def write_songs(primary: ClipInfo, others: list[ClipInfo], out_dir: Path, *, n: int = 14, render_top: int = 4,
                keep: int = 3, seed: int | None = None, packs: list[str] | None = None,
                exclude_pack: str | None = None, start_index: int = 0, recent: list[str] | None = None) -> dict | None:
    """Make candidates, critique, render the best, keep the winner + alternatives. Returns the record
    written to song.json, or None if nothing passed."""
    rng = np.random.default_rng(seed if seed is not None else int(time.time() * 1000) % (1 << 31))
    clips = {c.id: c for c in [primary, *others]}
    specs = candidates(primary, others, n, rng, packs, exclude_pack)
    tally: dict[str, int] = {}
    scored = []
    for spec in specs:
        try:
            song = build(spec, clips)
        except Exception as e:  # a candidate that can't be built is just a reject
            tally[f"couldn't be built ({type(e).__name__})"] = tally.get(f"couldn't be built ({type(e).__name__})", 0) + 1
            continue
        verdict = critic.judge(song)
        if not verdict["ok"]:
            for r in verdict["rejects"]:
                tally[r] = tally.get(r, 0) + 1
            continue
        # Styles used in the last few songs count slightly against a candidate, so the inbox rotates
        # through styles instead of always picking the same one.
        penalty = 0.03 * (recent or []).count(spec["pack"])
        scored.append((verdict["score"] - penalty, spec, song))
    scored.sort(key=lambda x: -x[0])
    # Render the best few, preferring different styles so the alternatives really differ (§7.11 step 5).
    chosen, seen = [], set()
    for item in scored:
        if item[1]["pack"] not in seen or len(chosen) < 1:
            chosen.append(item)
            seen.add(item[1]["pack"])
        if len(chosen) >= render_top:
            break
    for item in scored:
        if len(chosen) >= render_top:
            break
        if item not in chosen:
            chosen.append(item)
    final = []
    for _, spec, song in chosen:
        mix, stems = render.mix(song)
        verdict = critic.judge(song, mix, stems)
        if not verdict["ok"]:
            for r in verdict["rejects"]:
                tally[r] = tally.get(r, 0) + 1
            continue
        final.append((verdict["score"] - 0.03 * (recent or []).count(spec["pack"]), spec, song, mix, verdict))
    if not final:
        return None
    final.sort(key=lambda x: -x[0])
    out_dir.mkdir(parents=True, exist_ok=True)
    versions = []
    for i, (score, spec, song, mix, verdict) in enumerate(final[:keep], start=start_index):
        render.write_audio(mix, out_dir / f"v{i}.ogg")
        render.write_midi(song, out_dir / f"v{i}.mid")
        versions.append({"file": f"v{i}.ogg", "midi": f"v{i}.mid", "spec": spec, "score": score,
                         "critic": verdict, "title": title(song, primary), **song_summary(song)})
    record = {
        "created": time.time(), "primary": primary.id, "versions": versions,
        "made": len(specs), "rejected": tally, "rendered": len(chosen),
        "summary": f"Made {len(specs)} versions, rejected {sum(tally.values())}"
                   + (f" ({', '.join(f'{v}× {k}' for k, v in sorted(tally.items(), key=lambda kv: -kv[1]))})" if tally else "")
                   + f"; rendered the best {len(chosen)} and kept {len(versions)}.",
    }
    if start_index == 0:
        (out_dir / "song.json").write_text(json.dumps(record, default=float))
    return record
