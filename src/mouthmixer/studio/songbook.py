"""The songbook: ready-to-start songs (lyrics, a starter beat, a voice plan) in assets/songbook/*.txt.

File format: "key: value" lines (title, slot, starter, voices, hits, notes), a line "---", then the lyrics
with [Section] headers, exactly as you would paste them into Make.
"""

from __future__ import annotations

from pathlib import Path

from . import starters

ROOT = Path(__file__).resolve().parents[3] / "assets" / "songbook"


def _parse(path: Path) -> dict:
    head, _, body = path.read_text(encoding="utf-8").partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        k, _, v = line.partition(":")
        if k.strip():
            meta[k.strip().lower()] = v.strip()
    meta["id"] = path.stem
    meta["lyrics"] = body.strip()
    return meta


def songs() -> list[dict]:
    out = []
    for f in sorted(ROOT.glob("*.txt")):
        m = _parse(f)
        st = starters.STARTERS.get(m.get("starter", ""))
        if not st:
            continue
        out.append(m | {"style": starters.PACKS[st["pack"]]["title"], "bpm": st["bpm"],
                        "key": f"{starters.theory.NAMES[st['tonic']]} {st['mode']}"})
    return out


def get(song_id: str) -> dict:
    for s in songs():
        if s["id"] == song_id:
            return s
    raise KeyError(song_id)
