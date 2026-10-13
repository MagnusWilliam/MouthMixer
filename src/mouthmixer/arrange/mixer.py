"""The mixer (Incredibox-style): a song version as a set of parts you can mute, swap, add and remove.

Each part renders to its own stem (cached by content), so the app can switch parts on and off instantly
in the browser. Saving bakes the current set into a new mastered version of the song.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np

from . import arranger, catalog, critic, render, theory
from .styles import INSTRUMENTS, PACKS

def write_json(path: Path, obj) -> None:
    """Write-then-rename, so a reader in another request never sees a half-written file."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, default=float))
    tmp.replace(path)


def next_version_index(song_dir: Path, record: dict) -> int:
    """The next free vN number: past every version in the record and every vN.ogg on disk (a version
    still being written reserves its name with an empty file)."""
    on_disk = [int(p.stem[1:]) for p in song_dir.glob("v*.ogg") if p.stem[1:].isdigit()]
    return max([int(x["file"][1:-4]) for x in record["versions"]] + on_disk + [-1]) + 1


ROLE_PAN = {"comp": -0.3, "arp": 0.35, "counter": -0.35, "riff": 0.25, "perc": 0.4, "fx": 0.0}


def parse_chord(name: str) -> tuple[int, str]:
    """'Ebmaj7' -> (3, 'maj7'). Used for songs written before chords were stored with root and quality."""
    for root_len in (2, 1):
        root = name[:root_len]
        if root in theory.NAMES:
            suffix = name[root_len:]
            for q, sfx in theory.SUFFIX.items():
                if sfx == suffix:
                    return theory.NAMES.index(root), q
    return 0, "maj"


def song_from_version(v: dict, parts: list[dict] | None = None) -> arranger.Song:
    chords = []
    for c in v["chords"]:
        root, q = (c["root"], c["quality"]) if "root" in c else parse_chord(c["name"])
        chords.append((c["start"], c["length"], theory.Chord(root, q, c.get("degree", ""), "T")))
    key = v["key"].split()
    tonic = theory.NAMES.index(key[0]) if key[0] in theory.NAMES else 0
    tracks = []
    for p in (parts if parts is not None else _parts_from_version(v)):
        if p.get("muted"):
            continue
        tracks.append(arranger.Track(p["name"], p["role"], p["instrument"], [tuple(n) for n in p["notes"]],
                                     mine=p.get("mine", False), pan=p.get("pan", 0.0)))
    sections = [(s["name"], s["start"], s["bars"]) for s in v["sections"]]
    return arranger.Song(pack=v["pack"], bpm=v["bpm"], tonic=tonic, mode=key[1] if len(key) > 1 else "major",
                         swing=PACKS[v["pack"]]["swing"], sections=sections, chords=chords, tracks=tracks,
                         seed=v.get("spec", {}).get("seed", 0))


def _instrument_key(label: str, role: str) -> str:
    """Summaries store a readable instrument name; turn it back into the catalog key."""
    if label.endswith(" drum kit"):
        return "kit:" + label[: -len(" drum kit")].replace(" ", "_")
    return label.replace(" ", "_")


def _parts_from_version(v: dict) -> list[dict]:
    parts = []
    for i, t in enumerate(v["tracks"]):
        inst = t.get("key") or _instrument_key(t["instrument"], t["role"])
        parts.append({"id": f"p{i}", "name": t["name"], "role": t["role"], "instrument": inst,
                      "kind": f"orig:{t['role']}", "mine": t.get("mine", False), "muted": False, "gain_db": 0.0,
                      "pan": ROLE_PAN.get(t["role"], 0.0), "notes": t["notes"]})
    for a in v.get("audio_parts", []):  # recorded audio pieces (vocal chops from the Make tab)
        parts.append({"id": a["id"], "name": a["name"], "role": a.get("role", "chop"), "instrument": "your voice",
                      "kind": "audio", "mine": True, "muted": False, "gain_db": 0.0, "pan": 0.0, "notes": [],
                      "file": a["file"]})
    if v.get("vocal_stem"):
        parts.append(_vocal_part(v["vocal_stem"]))
    return parts


def _vocal_part(stem: str) -> dict:
    """Your processed vocals: a finished stem (no notes to re-render)."""
    return {"id": "vocal", "name": "Your vocals", "role": "vocal", "instrument": "your voice", "kind": "vocal",
            "mine": True, "muted": False, "gain_db": 0.0, "pan": 0.0, "notes": [], "file": stem}


class Mixer:
    """Mixer state for one song version, stored next to the song (mixer-v<N>.json, stems/)."""

    def __init__(self, song_dir: Path, version: int):
        self.dir = song_dir
        self.record = json.loads((song_dir / "song.json").read_text())
        self.version = version
        self.v = self.record["versions"][version]
        self.path = song_dir / f"mixer-v{version}.json"
        self.stem_dir = song_dir / "stems"
        self.stem_dir.mkdir(exist_ok=True)
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
        else:
            self.state = {"version": version, "parts": _parts_from_version(self.v), "next_id": len(self.v["tracks"])}
            self.save_state()

    # --- state ----------------------------------------------------------------------------------
    def save_state(self):
        write_json(self.path, self.state)

    @property
    def parts(self) -> list[dict]:
        return self.state["parts"]

    def part(self, pid: str) -> dict:
        for p in self.parts:
            if p["id"] == pid:
                return p
        raise KeyError(pid)

    def song(self, include_muted: bool = False) -> arranger.Song:
        parts = [p for p in self.parts if not p.get("file") and (include_muted or not p.get("muted"))]
        return song_from_version(self.v, parts)

    def public(self) -> dict:
        """What the app needs: parts (without the note lists) with their stem file and instrument choices."""
        out = []
        for p in self.parts:
            spec = catalog.PARTS.get(p["kind"])
            choices = [] if p.get("file") else spec["sounds"] if spec else _choices_for_role(p["role"], p["instrument"])
            out.append({k: v for k, v in p.items() if k != "notes"} | {
                "stem": self.stem_name(p), "choices": choices, "label": spec["label"] if spec else p["name"],
                "n_notes": len(p["notes"])})
        return {"version": self.version, "bpm": self.v["bpm"], "key": self.v["key"], "style": self.v["style"],
                "pack": self.v["pack"], "sections": self.v["sections"], "parts": out,
                "seconds": render.song_length(self.song(True))[0]}

    # --- stems ----------------------------------------------------------------------------------
    def stem_name(self, p: dict) -> str:
        if p.get("file"):
            return p["file"]
        h = hashlib.sha1(json.dumps([p["instrument"], p["role"], p.get("pan", 0), p["notes"], self.v["bpm"],
                                     self.v["pack"], self._duck_key()], default=float).encode()).hexdigest()[:12]
        return f"v{self.version}-{p['id']}-{h}.ogg"

    def _duck_key(self):
        return [p["id"] for p in self.parts if p["role"] == "drums" and not p.get("muted")]

    def render_stems(self) -> list[str]:
        """Render any stem that isn't cached yet. Returns the names rendered."""
        song = self.song(True)
        _, n = render.song_length(song)
        duck = render._sidechain(n, render.kick_times(self.song(False)))
        done = []
        for p in self.parts:
            name = self.stem_name(p)
            if p.get("file") or (self.stem_dir / name).exists():
                continue
            t = arranger.Track(p["name"], p["role"], p["instrument"], [tuple(x) for x in p["notes"]],
                               mine=p.get("mine", False), pan=p.get("pan", 0.0))
            x = render.render_stem(t, song, np.random.default_rng(abs(hash(p["id"])) % (1 << 31)), duck)
            render.write_audio(x, self.stem_dir / name)
            done.append(name)
        return done

    # --- edits ----------------------------------------------------------------------------------
    def set(self, pid: str, *, muted=None, gain_db=None, instrument=None, pan=None) -> dict:
        p = self.part(pid)
        if muted is not None:
            p["muted"] = bool(muted)
        if gain_db is not None:
            p["gain_db"] = float(np.clip(gain_db, -24, 12))
        if pan is not None:
            p["pan"] = float(np.clip(pan, -1, 1))
        if instrument and instrument != p["instrument"] and not p.get("file"):
            p["instrument"] = instrument
            spec = catalog.PARTS.get(p["kind"])
            if spec and spec["gen"] not in ("double",):
                p["notes"] = [list(n) for n in catalog.generate(p["kind"], self.song(), instrument)]
            elif not instrument.startswith(("kit:", "fx:")):
                notes = arranger.fit_range([tuple(n) for n in p["notes"]], instrument)
                if p["role"] != "lead":
                    lead = [tuple(n) for q in self.parts if q["role"] == "lead" and not q.get("muted") for n in q["notes"]]
                    notes = clear_of_melody(notes, lead, instrument)
                p["notes"] = [list(n) for n in notes]
        self.save_state()
        return p

    def add(self, kind: str, instrument: str | None = None) -> dict:
        spec = catalog.PARTS[kind]
        instrument = instrument or spec["sounds"][0]
        notes = catalog.generate(kind, self.song(), instrument)
        # A beat or bass "replaces" the current one: the old one is muted, not deleted (one click back).
        if spec.get("replaces"):
            for p in self.parts:
                if p["role"] == spec["replaces"] and not p.get("muted"):
                    p["muted"] = True
        pid = f"p{self.state['next_id']}"
        self.state["next_id"] += 1
        part = {"id": pid, "name": spec["label"], "role": spec["role"], "instrument": instrument, "kind": kind,
                "mine": False, "muted": False, "gain_db": 0.0, "pan": ROLE_PAN.get(spec["role"], 0.0),
                "notes": [list(n) for n in notes]}
        self.parts.append(part)
        self.save_state()
        return part

    def remove(self, pid: str) -> None:
        p = self.part(pid)
        if p.get("mine"):
            raise ValueError("your own parts can be muted but not removed")
        self.state["parts"] = [x for x in self.parts if x["id"] != pid]
        self.save_state()

    # --- bake -----------------------------------------------------------------------------------
    def _load(self, p: dict, n: int) -> np.ndarray:
        import soundfile as sf

        x, _ = sf.read(str(self.stem_dir / self.stem_name(p)), dtype="float32", always_2d=True)
        x = x.T[:, :n]
        if x.shape[1] < n:
            x = np.pad(x, ((0, 0), (0, n - x.shape[1])))
        return x * 10 ** (p.get("gain_db", 0.0) / 20)

    def _stems(self, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, dict]:
        """(music without the lead, lead, vocal or None, stems by role) from the unmuted parts."""
        music = np.zeros((2, n), dtype=np.float32)
        lead = np.zeros((2, n), dtype=np.float32)
        vocal = None
        stems: dict = {}
        for p in self.parts:
            if p.get("muted"):
                continue
            x = self._load(p, n)
            if p["role"] == "vocal":
                vocal = x
                continue
            if p["role"] == "lead":
                lead += x
            else:
                music += x
            stems[p["role"]] = stems.get(p["role"], 0) + x
        return music, lead, vocal, stems

    def bake(self, extra: dict | None = None, suffix: str = "your mix") -> dict:
        """Mix the unmuted parts (with their volumes) and master it: a new version of the song. With your
        vocals on, the music makes room for them (VOCALS §5 step 13) and the hummed lead ducks."""
        from . import vocals
        from .songwriter import song_summary

        self.render_stems()
        song = self.song(False)
        _, n = render.song_length(song)
        music, lead, vocal, stems = self._stems(n)
        if vocal is not None:
            p = vocals.preset((extra or {}).get("vocals", {}).get("preset") or self.v.get("vocals", {}).get("preset"))
            env = vocals.envelope_from_audio(vocal)
            out, vocal, lead = vocals.sit_in_song(music, vocal, env, p, lead, self.state.get("lead_mode", "duck"),
                                                  match_level=False)
            stems["lead"] = (lead if lead is not None else 0) + vocal
        else:
            out = music + lead
        mix = render.master(out)
        verdict = critic.judge(song, mix, stems)
        idx = next_version_index(self.dir, self.record)
        render.write_audio(mix, self.dir / f"v{idx}.ogg")
        render.write_midi(song, self.dir / f"v{idx}.mid")
        summary = song_summary(song)
        for t, p in zip(summary["tracks"], [p for p in self.parts if not p.get("muted") and not p.get("file")]):
            t["key"] = p["instrument"]
        new = {**self.v, **summary, "file": f"v{idx}.ogg", "midi": f"v{idx}.mid", "critic": verdict,
               "score": verdict["score"], "title": self.v["title"].split(" · ")[0] + " · " + suffix,
               "mixed_from": self.version, "mixed_at": time.time()}
        voc = next((p for p in self.parts if p.get("file") and p["role"] == "vocal" and not p.get("muted")), None)
        new.pop("vocal_stem", None)
        if voc:
            new["vocal_stem"] = voc["file"]
        new["audio_parts"] = [{"id": p["id"], "name": p["name"], "role": p["role"], "file": p["file"]}
                              for p in self.parts if p.get("file") and p["role"] != "vocal" and not p.get("muted")]
        new.update(extra or {})
        self.record = json.loads((self.dir / "song.json").read_text())  # as it is now
        self.record["versions"].append(new)
        write_json(self.dir / "song.json", self.record)
        return new

    # --- vocals ---------------------------------------------------------------------------------
    def with_vocals(self, takes: list, preset_name: str | None = None, lead_mode: str = "duck",
                    choice: dict | None = None, lyrics: dict | None = None) -> dict:
        """Process your takes (vocals.produce), set them against this mix and save a new version with a
        "Your vocals" part you can mute or turn up in the mixer like any other."""
        from . import vocals

        self.render_stems()
        song = self.song(False)
        total, n = render.song_length(song)
        # Every melody part you can hear (your hummed lead and the bridge melody written for it).
        lead_notes = [x for p in self.parts if p["role"] == "lead" and not p.get("muted") for x in p["notes"]]
        name = preset_name or PACKS[self.v["pack"]].get("vocal_preset", "soul")
        res = vocals.produce(takes, lead_notes, self.v["bpm"], self.v["sections"], song.tonic, song.mode, name,
                             total, choice)
        music, lead, _, _ = self._stems(n)
        voc = res.stereo[:, :n]
        if voc.shape[1] < n:
            voc = np.pad(voc, ((0, 0), (0, n - voc.shape[1])))
        env = vocals.voice_envelope(res.f0_after, n)
        _, voc, _ = vocals.sit_in_song(music, voc, env, vocals.preset(name), lead, lead_mode, res.report)
        h = hashlib.sha1(voc[:, ::97].tobytes()).hexdigest()[:12]
        stem = f"vocal-{h}.ogg"
        render.write_audio(voc, self.stem_dir / stem)
        self.state["parts"] = [p for p in self.parts if p["role"] != "vocal"] + [_vocal_part(stem)]
        self.state["lead_mode"] = lead_mode
        self.save_state()
        extra = {"vocals": res.report | {"lead_mode": lead_mode}}
        if lyrics:
            extra["lyrics"] = lyrics
        return self.bake(extra, suffix="with vocals")


def clear_of_melody(notes: list[tuple], melody: list[tuple], instrument: str) -> list[tuple]:
    """After moving a part by octaves (a new sound with another range), keep each note out of a half
    step's way of the melody note sounding with it (MUSIC_KNOWLEDGE H1): a minor 2nd, or a minor 9th
    with the melody on top, moves an octave (down first) or is dropped. A major 7th is fine."""
    lo, hi = INSTRUMENTS[instrument][2:4]

    def bad(x, s, l):
        return any(abs(m - x) == 1 or (m > x and (m - x) % 12 == 1)
                   for ms, ml, m, *_ in melody if ms < s + l and ms + ml > s)

    out = []
    for s, l, p, v in notes:
        if not bad(p, s, l):
            out.append((s, l, p, v))
            continue
        for q in (p - 12, p + 12):
            if lo <= q <= hi and not bad(q, s, l):
                out.append((s, l, q, v))
                break
    return out


def _choices_for_role(role: str, current: str) -> list[str]:
    if current.startswith("kit:"):
        return ["kit:" + k for k in ("standard", "room", "power", "electronic", "tr808", "dance", "jazz", "brush",
                                     "orchestra")]
    if current.startswith("fx:"):
        return [current]
    fam = INSTRUMENTS.get(current, (0, 0, 0, 0, "keys", 1))[4]
    same = [k for k, v in INSTRUMENTS.items() if v[4] == fam]
    if role == "lead":  # your melody can go to almost anything melodic
        same = [k for k, v in INSTRUMENTS.items() if v[4] in ("keys", "mallet", "guitar", "strings", "brass", "wind",
                                                               "synth", "reed", "world", "voice")]
    return [current] + [k for k in same if k != current]
