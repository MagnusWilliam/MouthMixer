"""Sampled and synthesised instruments (docs/INSTRUMENTS.md, docs/PERSONA_PRODUCTION.md §1).

Free libraries live in <library>/instruments/ (downloaded by the user, never in git). Each instrument key
("sfz:rhodes", "kit:muldjord", "synth:organ_jazz"...) maps to an SFZ file, a folder of samples turned into
SFZ on the fly, or a synth. When a library isn't installed the instrument falls back to its General MIDI
cousin, so songs still render (and the tests run) everywhere.

Licences (credits go in the game's credits where marked CC-BY):
- jRhodes3d (Jeff Learman): music made with it is free to use; the samples are not redistributed.
- Black And Blue Basses (Karoryfer): CC0. VCSL and VSCO-2 CE (Versilian Studios): CC0.
- MuldjordKit (DrumGizmo / FreePats): CC-BY 4.0. Salamander Grand Piano V3 (Alexander Holm): CC-BY 3.0.
- FreePats Tenor Saxophone and FSBS Clean Electric Guitar: CC0.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from .. import config
from . import sampler, synths

SR = sampler.SR


def root() -> Path:
    import os

    return Path(os.environ["MOUTHMIXER_INSTRUMENTS"]) if os.environ.get("MOUTHMIXER_INSTRUMENTS") else config.home() / "instruments"


VSCO = "VSCO-2-CE"
# key: (source, GM fallback, family, low, high, gain, credit)
# source: an .sfz path, ("folder", path, file filter), ("bbb", articulation layers) or ("perc", map name)
SAMPLED: dict[str, dict] = {
    "sfz:rhodes": {"src": "jRhodes3d/jRhodes3d-st-no-xfade.sfz", "gm": "rhodes", "family": "keys", "range": (28, 103)},
    "sfz:piano": {"src": "Salamander/SalamanderGrandPiano-SFZ+FLAC-V3+20200602/SalamanderGrandPiano-V3+20200602.sfz",
                  "gm": "piano", "family": "keys", "range": (21, 108)},
    "sfz:bass_finger": {"src": ("bbb", [("darkblack_reg_p_map", 1, 40), ("darkblack_reg_mp_map", 41, 72),
                                        ("darkblack_reg_mf_map", 73, 104), ("darkblack_reg_f_map", 105, 127)]),
                        "gm": "finger_bass", "family": "bass", "range": (23, 67), "key_shift": 12},
    "sfz:bass_ghost": {"src": ("bbb", [("darkblack_ghost_p_map", 1, 70), ("darkblack_ghost_f_map", 71, 127)]),
                       "gm": "finger_bass", "family": "bass", "range": (23, 67), "key_shift": 12},
    "sfz:bass_stac": {"src": ("bbb", [("darkblack_stac_map", 1, 127)]), "gm": "finger_bass", "family": "bass",
                      "range": (23, 67), "key_shift": 12},
    "sfz:guitar_clean": {"src": "FSBS-clean/EGuitarFSBS-clean SFZ+FLAC-20260807/EGuitarFSBS-clean bridge 20260807.sfz",
                         "gm": "clean_guitar", "family": "guitar", "range": (40, 88)},
    "sfz:tenor_sax": {"src": "TenorSax/TenorSaxophone-SFZ+FLAC-20200717/TenorSaxophone-20200717.sfz",
                      "gm": "tenor_sax", "family": "reed", "range": (44, 75)},
    "sfz:violins": {"src": ("folder", f"{VSCO}/Strings/Violin Section/susVib", ""), "gm": "strings",
                    "family": "strings", "range": (55, 100)},
    "sfz:violins_spic": {"src": ("folder", f"{VSCO}/Strings/Violin Section/Spic", ""), "gm": "pizzicato",
                         "family": "strings", "range": (55, 100)},
    "sfz:violins_pizz": {"src": ("folder", f"{VSCO}/Strings/Violin Section/Pizz", ""), "gm": "pizzicato",
                         "family": "strings", "range": (55, 100)},
    "sfz:violas": {"src": ("folder", f"{VSCO}/Strings/Viola Section/susvib", ""), "gm": "strings",
                   "family": "strings", "range": (48, 88)},
    "sfz:cellos": {"src": ("folder", f"{VSCO}/Strings/Cello Section/susvib", ""), "gm": "strings",
                   "family": "strings", "range": (36, 76)},
    "sfz:cellos_spic": {"src": ("folder", f"{VSCO}/Strings/Cello Section/spic", ""), "gm": "pizzicato",
                        "family": "strings", "range": (36, 76)},
    "sfz:trumpet": {"src": ("folder", f"{VSCO}/Brass/Trumpet/sus", ""), "gm": "trumpet", "family": "brass",
                    "range": (54, 84)},
    "sfz:trumpet_harmon": {"src": ("folder", f"{VSCO}/Brass/Trumpet/harmonM-sus", ""), "gm": "muted_trumpet",
                           "family": "brass", "range": (52, 84)},
    "sfz:trumpet_stac": {"src": ("folder", f"{VSCO}/Brass/Trumpet/stac", ""), "gm": "trumpet", "family": "brass",
                         "range": (54, 84)},
    "sfz:trombone": {"src": ("folder", f"{VSCO}/Brass/Tenor Trombone/sus", ""), "gm": "trombone", "family": "brass",
                     "range": (34, 72)},
    "sfz:trombone_stac": {"src": ("folder", f"{VSCO}/Brass/Tenor Trombone/stac", ""), "gm": "trombone",
                          "family": "brass", "range": (34, 72)},
    "sfz:harp": {"src": ("folder", f"{VSCO}/Strings/Harp", ""), "gm": "harp", "family": "strings", "range": (24, 103)},
    "sfz:horn": {"src": ("folder", f"{VSCO}/Brass/F Horn/sus", ""), "gm": "french_horn", "family": "brass",
                 "range": (34, 77)},
}
SYNTH_KEYS = {f"synth:organ_{k}": ("organ", k) for k in synths.ORGANS} | \
    {f"synth:{k}": ("synth", k) for k in synths.SYNTHS}
# Drum kits on General MIDI drum notes.
KITS = {
    "kit:muldjord": {"src": "MuldjordKit/MuldjordKit SFZ+FLAC-20201018/MuldjordKit 20201018.sfz", "gm": "kit:room",
                     # GM note -> the kit's key (kick L/R alternate, toms high to low, pedal hat = closed, soft)
                     "map": {35: 49, 36: 48, 37: 65, 38: 50, 40: 51, 42: 52, 44: 52, 46: 53, 51: 54, 59: 56, 53: 55,
                             49: 58, 57: 59, 52: 60, 55: 59, 50: 61, 48: 62, 47: 63, 45: 63, 43: 64, 41: 64},
                     "choke": {"closed": [52], "open": [53]}},
    "kit:latin": {"src": ("perc", "latin"), "gm": "kit:standard", "map": None, "choke": {}},
}
# GM percussion notes for the hand percussion kit (VCSL, CC0).
VCSL = "VCSL"
PERC = {
    60: ("Membranophones/Struck Membranophones/Bongos", "BongoH_Hit1"),
    61: ("Membranophones/Struck Membranophones/Bongos", "BongoL_Hit1"),
    62: ("Membranophones/Struck Membranophones/Conga", "Conga_HitFM"),  # mute (slap) high conga
    63: ("Membranophones/Struck Membranophones/Conga", "Conga_HitN"),  # open high conga
    64: ("Membranophones/Struck Membranophones/Conga", "Tumba_HitN"),  # low conga
    65: ("Membranophones/Struck Membranophones/Conga", "Quinto_HitN"),
    54: ("Idiophones/Struck Idiophones/Tambourine 1", "Tamb1_Hit"),
    80: ("Idiophones/Struck Idiophones/Triangles", "Triangle1_HitM"),  # mute triangle
    81: ("Idiophones/Struck Idiophones/Triangles", "Triangle1_Hit_"),  # open triangle
    82: ("Idiophones/Struck Idiophones/Shaker, Small", "Mid_ShakerHighFaster"),
}

_NOTE_RE = re.compile(r"_([A-G]#?)(-?\d)(?:_v(\d+))?(?:_(?:rr|RR)?(\d+))?(?=[_.])", re.I)


def folder_sfz(folder: Path, name_filter: str = "") -> str:
    """SFZ text for a folder of samples named like Name_Artic_A#3_v2_rr1.wav: each recorded note covers the
    keys halfway to its neighbours, velocity layers split evenly, round robins in sequence."""
    files: dict[tuple[int, int], list[str]] = {}
    for p in sorted(folder.glob("*.wav")) + sorted(folder.glob("*.flac")):
        if name_filter and name_filter not in p.name:
            continue
        m = _NOTE_RE.search(p.name)
        if not m:
            continue
        key = sampler.note_number(m[1].lower() + m[2])
        files.setdefault((key, int(m[3] or 1)), []).append(p.name)
    if not files:
        return ""
    keys = sorted({k for k, _ in files})
    layers = sorted({v for _, v in files})
    out = []
    for i, k in enumerate(keys):
        lo = 0 if i == 0 else (keys[i - 1] + k) // 2 + 1
        hi = 127 if i == len(keys) - 1 else (k + keys[i + 1]) // 2
        have = [v for v in layers if (k, v) in files]
        for j, v in enumerate(have):
            lovel = 1 + round(126 * j / len(have))
            hivel = round(127 * (j + 1) / len(have))
            names = files[(k, v)]
            for r, nm in enumerate(names):
                seq = f" seq_length={len(names)} seq_position={r + 1}" if len(names) > 1 else ""
                out.append(f"<region> sample={nm} lokey={lo} hikey={hi} pitch_keycenter={k} lovel={lovel} "
                           f"hivel={hivel} amp_veltrack=60 ampeg_release=0.35{seq}")
    return "\n".join(out) + "\n"


def perc_sfz(base: Path) -> str:
    """The hand percussion kit (bongos, congas, tambourine, triangles, shaker) on GM percussion notes."""
    out = []
    for key, (folder, prefix) in PERC.items():
        d = base / folder
        names = sorted(p.name for p in d.glob(f"{prefix}*.wav"))
        by_v: dict[int, list[str]] = {}
        for nm in names:
            m = re.search(r"_v(\d+)", nm)
            by_v.setdefault(int(m[1]) if m else 1, []).append(nm)
        vs = sorted(by_v)
        for j, v in enumerate(vs):
            lovel, hivel = 1 + round(126 * j / len(vs)), round(127 * (j + 1) / len(vs))
            for r, nm in enumerate(by_v[v]):
                rel = (Path(folder) / nm).as_posix()
                seq = f" seq_length={len(by_v[v])} seq_position={r + 1}" if len(by_v[v]) > 1 else ""
                out.append(f"<region> sample={rel} key={key} lovel={lovel} hivel={hivel} amp_veltrack=70 "
                           f"loop_mode=one_shot{seq}")
    return "\n".join(out) + "\n"


def _materialise(src, home: Path) -> Path | None:
    """The SFZ file for a source, writing generated wrappers into the libraries' folders (once)."""
    if isinstance(src, str):
        p = home / src
        return p if p.exists() else None
    kind = src[0]
    if kind == "folder":
        folder = home / src[1]
        if not folder.exists():
            return None
        out = folder / f"_mm_{src[2] or 'all'}.sfz"
        if not out.exists():
            text = folder_sfz(folder, src[2])
            if not text:
                return None
            out.write_text(text)
        return out
    if kind == "bbb":
        programs = home / "BlackAndBlue" / "Programs"
        if not programs.exists():
            return None
        name = "_mm_" + "_".join(m for m, _, _ in src[1]) + ".sfz"
        out = programs / name
        if not out.exists():
            text = "".join(f"<group> seq_length=4 lovel={lo} hivel={hi} amp_veltrack=45 ampeg_release=0.08\n"
                           f'#include "maps/{m}.sfz"\n' for m, lo, hi in src[1])
            out.write_text(text)
        return out
    if kind == "perc":
        base = home / VCSL
        if not base.exists():
            return None
        out = base / "_mm_latin.sfz"
        if not out.exists():
            out.write_text(perc_sfz(base))
        return out
    return None


_CACHE: dict[str, sampler.Instrument | None] = {}


def instrument(key: str) -> sampler.Instrument | None:
    """The loaded instrument, or None when its library isn't installed."""
    if key not in _CACHE:
        spec = SAMPLED.get(key) or KITS.get(key)
        path = _materialise(spec["src"], root()) if spec else None
        try:
            inst = sampler.Instrument(path) if path else None
        except (ValueError, OSError):
            inst = None
        if inst is not None and key in KITS and KITS[key]["choke"]:
            closed, opened = KITS[key]["choke"]["closed"], KITS[key]["choke"]["open"]
            for r in inst.regions:
                if r.lokey in closed:
                    r.group = 1
                elif r.lokey in opened:
                    r.group, r.off_by = 2, 1
        _CACHE[key] = inst
    return _CACHE[key]


# Transition effects (docs/PERSONA_PRODUCTION.md rule 14): a reverse cymbal swelling into the note's end and a
# sub boom on its start. Notes: (start, length, key, velocity); the swell ends where the note ends.
SFX = {"sfx:reverse_crash", "sfx:boom"}


def sfx(key: str, notes_sec, total_sec: float, rng) -> np.ndarray:
    n = int(total_sec * SR)
    out = np.zeros((2, n), dtype=np.float32)
    if key == "sfx:reverse_crash":
        kit = instrument("kit:muldjord")
        if kit is not None:
            r = max((r for r in kit.regions if r.lokey == 58), key=lambda r: r.hivel)
            crash = sampler.load_sample(r.sample)
        else:  # no kit installed: shaped noise
            t = np.arange(int(2.5 * SR)) / SR
            crash = np.stack([rng.normal(0, 0.3, len(t)) * np.exp(-t * 1.6)] * 2).astype(np.float32)
        for s, l, _, v in notes_sec:
            m = min(int(l * SR), crash.shape[1])
            seg = crash[:, :m][:, ::-1] * (v / 127)
            end = int((s + l) * SR)
            a = max(0, end - m)
            out[:, a:end] += seg[:, m - (end - a):]
    elif key == "sfx:boom":
        for s, l, _, v in notes_sec:
            m = min(int(max(l, 1.2) * SR), n - int(s * SR))
            t = np.arange(m) / SR
            f = 38 + 50 * np.exp(-t * 9)
            x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4) * (v / 127)
            x[: int(0.004 * SR)] += rng.normal(0, 0.2, int(0.004 * SR))
            a = int(s * SR)
            out[:, a:a + m] += x[None, :] * 0.8
    return out


def available(key: str) -> bool:
    if key in SYNTH_KEYS or key in SFX:
        return True
    return instrument(key) is not None


def handles(key: str) -> bool:
    return key in SAMPLED or key in KITS or key in SYNTH_KEYS or key in SFX


def fallback(key: str) -> str:
    if key in SYNTH_KEYS or key in SFX:
        return key
    return (SAMPLED.get(key) or KITS.get(key))["gm"]


def render(key: str, notes_sec: list[tuple[float, float, int, int]], total_sec: float, rng) -> np.ndarray:
    """notes_sec: (start s, length s, key, velocity). Returns (2, n) float32 with the instrument's own effects."""
    if key in SFX:
        return sfx(key, notes_sec, total_sec, rng)
    if key in SYNTH_KEYS:
        kind, preset = SYNTH_KEYS[key]
        if kind == "organ":
            return synths.organ(notes_sec, total_sec, preset, rng)
        return synths.synth(notes_sec, total_sec, preset, rng)
    inst = instrument(key)
    if key in KITS:
        mp = KITS[key]["map"]
        notes = [(s, l, mp.get(int(p), int(p)) if mp else int(p), v) for s, l, p, v in notes_sec]
        return sampler.render_kit(inst, notes, total_sec, rng)
    shift = SAMPLED[key].get("key_shift", 0)  # libraries mapped as written, an octave above how they sound
    x = inst.render([(s, l, p + shift, v) for s, l, p, v in notes_sec], total_sec, rng)
    return post_fx(key, x, rng)


def post_fx(key: str, x: np.ndarray, rng) -> np.ndarray:
    """The instrument's own character (docs/PERSONA_PRODUCTION.md rules 1 and 7)."""
    from pedalboard import Chorus, Distortion, Gain, HighpassFilter, Pedalboard, PeakFilter

    x = x.astype(np.float32)
    if key == "sfz:rhodes":
        # Pan Cake Kore style: auto-pan, a little chorus, a touch of amp; no distortion
        t = np.arange(x.shape[1]) / SR
        pan = 0.35 * np.sin(2 * np.pi * 0.45 * t)
        mono = x.mean(axis=0)
        x = np.stack([mono * np.sqrt(0.5 - pan / 2) * 1.414, mono * np.sqrt(0.5 + pan / 2) * 1.414]) * 0.5 + x * 0.5
        x = Pedalboard([Chorus(rate_hz=0.8, depth=0.18, mix=0.3), Distortion(drive_db=4), Gain(-3.5),
                        PeakFilter(cutoff_frequency_hz=300, gain_db=-4.0, q=0.8),
                        PeakFilter(cutoff_frequency_hz=1200, gain_db=2.0, q=0.8)])(x.astype(np.float32), SR)
    elif key == "sfz:piano" or SAMPLED.get(key, {}).get("family") in ("strings", "brass"):
        # Salamander and the VSCO sections are recorded wide (the VSCO violins even have more side than middle,
        # which thins out on mono speakers); in a band mix they sit nearer the middle: 60% width
        mid, side = x.mean(axis=0), (x[0] - x[1]) / 2
        x = np.stack([mid + 0.6 * side, mid - 0.6 * side])
    elif key == "sfz:guitar_clean":
        x = Pedalboard([HighpassFilter(110), Distortion(drive_db=6), Gain(-5),
                        PeakFilter(cutoff_frequency_hz=2400, gain_db=3, q=0.9)])(x, SR)
    elif key.startswith("sfz:bass"):
        # neck pickup is warm; add the Fender's clank and growl around 800 Hz-2 kHz
        x = Pedalboard([PeakFilter(cutoff_frequency_hz=350, gain_db=-2.5, q=0.9),
                        PeakFilter(cutoff_frequency_hz=900, gain_db=3.0, q=0.9),
                        PeakFilter(cutoff_frequency_hz=2200, gain_db=2.0, q=1.2)])(x, SR)
    return x.astype(np.float32)


def credits() -> list[str]:
    return ["MuldjordKit by the DrumGizmo team (CC-BY 4.0)", "Salamander Grand Piano by Alexander Holm (CC-BY 3.0)",
            "jRhodes3d by Jeff Learman", "Black And Blue Basses by Karoryfer Samples (CC0)",
            "VSCO-2 Community Edition and VCSL by Versilian Studios (CC0)", "FreePats tenor sax and FSBS guitar (CC0)"]
