"""A track you're making on purpose (the Make tab): a starter beat, the pieces you record for it, and the
song board that says which pieces play in which section.

Pieces are like Incredibox characters. **Loop pieces** repeat (beat, bassline, riff, accent stabs, vocal
chop, extra percussion); **one-off pieces** play once per section (hook, verse melody, bridge, intro
motif, answer line, drum fill). Each piece has takes (every pass of a loop recording is a take), a
chosen take, an instrument, octave and volume, and its notes (which you can nudge one at a time).

Pitched pieces remember the chords they were sung over; placed over other chords (the bridge), they move
by scale steps with the chord roots, so a bassline still follows the harmony.

Files: <home>/projects/<id>/project.json, takes/ (raw recordings and chop audio), stems/ (booth loops).
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path

import numpy as np

from .. import config
from ..arrange import arranger, critic, render, theory
from ..arrange.mixer import write_json
from ..arrange.styles import INSTRUMENTS, PACKS
from . import starters, transcribe

# slot -> what it is. kind: loop (repeats) | one (plays once per section, from its start)
SLOTS = {
    # loops
    "beat": {"label": "Beat", "kind": "loop", "source": "beatbox", "bars": 2, "role": "drums",
             "hint": "Beatbox a groove: \"b\" for kick, \"pf\" or \"k\" for snare, \"ts\" for hats."},
    "bass": {"label": "Bassline", "kind": "loop", "source": "hum", "bars": 4, "role": "bass",
             "hint": "Hum low, short notes (\"dum, dum-dum\"). It follows the chords in the bridge too."},
    "riff": {"label": "Riff / backing figure", "kind": "loop", "source": "hum", "bars": 2, "role": "riff",
             "hint": "A short figure that repeats under everything, like a keyboard or guitar riff."},
    "stab": {"label": "Accent stabs", "kind": "loop", "source": "hum", "bars": 2, "role": "riff",
             "hint": "Short \"bah!\" hits, often just before the beat. Each one becomes a full chord stab."},
    "chop": {"label": "Vocal chop", "kind": "loop", "source": "voice", "bars": 2, "role": "chop",
             "hint": "A short sung sound (\"hey!\", \"ah-ah\", \"oh-oh\"). It stays your voice: tuned and cut on the beat."},
    "perc": {"label": "Extra percussion", "kind": "loop", "source": "beatbox", "bars": 2, "role": "perc",
             "hint": "Beatbox again: kicks become congas, snares claps, hats shaker and tambourine."},
    # one-offs
    "hook": {"label": "Hook", "kind": "one", "source": "hum", "bars": 4, "role": "lead", "repeat": True,
             "hint": "The catchy line people remember. Short, simple, easy to sing back."},
    "lead": {"label": "Verse melody", "kind": "one", "source": "hum", "bars": 8, "role": "lead",
             "hint": "The tune of the verse: calmer and lower than the hook, it leads into it."},
    "bridge": {"label": "Bridge melody", "kind": "one", "source": "hum", "bars": 8, "role": "lead", "chords": "B",
               "hint": "Something different before the last hook. Recorded over the bridge chords."},
    "counter": {"label": "Answer line", "kind": "one", "source": "hum", "bars": 4, "role": "counter", "repeat": True,
                "hint": "A short reply in the gaps of the hook (call and response)."},
    "intro": {"label": "Intro / outro motif", "kind": "one", "source": "hum", "bars": 4, "role": "counter",
              "hint": "A few notes that open the track and come back at the end."},
    "fill": {"label": "Drum fill", "kind": "one", "source": "beatbox", "bars": 1, "role": "drums", "at_end": True,
             "hint": "One bar of beatbox that leads into the next section."},
    # starter-only
    "chords": {"label": "Chords", "kind": "loop", "source": "starter", "bars": 4, "role": "comp", "hint": ""},
    "pad": {"label": "Pad", "kind": "loop", "source": "starter", "bars": 4, "role": "pad", "hint": ""},
}
RECORDABLE = [k for k, v in SLOTS.items() if v["source"] != "starter"]
MIX_ROLE = {"lead": "lead", "counter": "counter", "riff": "riff", "drums": "drums", "perc": "perc", "bass": "bass",
            "comp": "comp", "pad": "pad", "chop": "chop"}
PAN = {"riff": 0.25, "counter": -0.3, "perc": 0.35, "comp": -0.2, "chop": 0.0}

DEFAULT_FORM = [("Intro", 4, "A"), ("Verse", 8, "A"), ("Hook", 8, "A"), ("Verse 2", 8, "A"), ("Hook 2", 8, "A"),
                ("Bridge", 8, "B"), ("Hook 3", 8, "A"), ("Outro", 4, "A")]


def projects_dir() -> Path:
    p = config.home() / "projects"
    p.mkdir(parents=True, exist_ok=True)
    return p


def list_projects() -> list[dict]:
    out = []
    for d in sorted(projects_dir().iterdir(), reverse=True):
        f = d / "project.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
            except ValueError:
                continue
            out.append({"id": data["id"], "title": data["title"], "created": data["created"],
                        "starter": data["starter"]["id"], "mood": starters.MOODS[data["starter"]["mood"]]["label"],
                        "pieces": sum(1 for p in data["pieces"] if p["source"] != "starter"),
                        "song_id": data.get("song_id")})
    return out


def _section_kind(name: str) -> str:
    n = name.lower()
    for k in ("intro", "outro", "verse", "hook", "bridge", "break"):
        if n.startswith(k):
            return k
    return "verse"


DEFAULT_PLAYS = {  # slot -> section kinds it plays in when first added
    "beat": {"verse", "hook", "bridge"}, "bass": {"verse", "hook", "bridge"}, "chords": {"intro", "verse", "hook", "bridge", "outro"},
    "pad": {"intro", "hook", "bridge", "outro"}, "riff": {"hook", "verse"}, "stab": {"hook"}, "chop": {"hook"},
    "perc": {"hook", "bridge"}, "hook": {"hook"}, "lead": {"verse"}, "bridge": {"bridge"}, "counter": {"hook"},
    "intro": {"intro", "outro"}, "fill": {"verse", "bridge"},
}


class Project:
    def __init__(self, path: Path):
        self.dir = path
        self.data = json.loads((path / "project.json").read_text())
        (self.dir / "takes").mkdir(exist_ok=True)
        (self.dir / "stems").mkdir(exist_ok=True)

    # --- create / save ---------------------------------------------------------------------------
    @classmethod
    def create(cls, starter_id: str, title: str = "", tonic: int | None = None) -> "Project":
        st = dict(starters.STARTERS[starter_id], id=starter_id)
        if tonic is not None:
            st["tonic"] = int(tonic) % 12
        pid = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]
        d = projects_dir() / pid
        (d / "takes").mkdir(parents=True)
        data = {"id": pid, "title": title or f"{starters.MOODS[st['mood']]['label']} track", "created": time.time(),
                "starter": st, "pieces": [], "sections": [], "next": 1, "song_id": None}
        write_json(d / "project.json", data)
        p = cls(d)
        for sp in starters.starter_parts(st):
            p._new_piece(sp["slot"], source="starter", name=sp["name"], instrument=sp["instrument"], gen=sp["gen"])
        p.data["sections"] = [{"id": f"s{i}", "name": n, "bars": b, "chords": c, "parts": []}
                              for i, (n, b, c) in enumerate(DEFAULT_FORM)]
        for piece in p.pieces:
            p._default_sections(piece)
        p.save()
        return p

    @classmethod
    def load(cls, pid: str) -> "Project":
        d = projects_dir() / pid
        if not (d / "project.json").exists() or d.resolve().parent != projects_dir().resolve():
            raise KeyError(pid)
        return cls(d)

    def save(self):
        write_json(self.dir / "project.json", self.data)

    @property
    def st(self) -> dict:
        return self.data["starter"]

    @property
    def pieces(self) -> list[dict]:
        return self.data["pieces"]

    @property
    def pack(self) -> dict:
        return PACKS[self.st["pack"]]

    @property
    def spb(self) -> float:
        return 60.0 / self.st["bpm"]

    def piece(self, pid: str) -> dict:
        for p in self.pieces:
            if p["id"] == pid:
                return p
        raise KeyError(pid)

    # --- pieces ----------------------------------------------------------------------------------
    def _default_instrument(self, slot: str) -> str:
        pk = self.st["pack"]
        kit = "kit:" + self.pack["kit"][0]
        return {"beat": kit, "fill": kit, "perc": kit, "bass": starters.instrument_for(pk, "bass"),
                "riff": starters.instrument_for(pk, "riff"), "stab": "brass_section", "chop": "your voice",
                "hook": starters.instrument_for(pk, "lead"), "lead": starters.instrument_for(pk, "lead", 1),
                "bridge": starters.instrument_for(pk, "lead", 2), "counter": starters.instrument_for(pk, "counter"),
                "intro": starters.instrument_for(pk, "arp"), "chords": starters.instrument_for(pk, "comp"),
                "pad": starters.instrument_for(pk, "pad")}[slot]

    def _new_piece(self, slot: str, *, source: str | None = None, name: str = "", instrument: str = "",
                   gen: str | None = None, bars: int | None = None) -> dict:
        spec = SLOTS[slot]
        same = sum(1 for p in self.pieces if p["slot"] == slot and p["source"] != "starter")
        piece = {"id": f"q{self.data['next']}", "slot": slot, "kind": spec["kind"], "role": spec["role"],
                 "source": source or spec["source"], "name": name or (spec["label"] + (f" {same + 1}" if same else "")),
                 "bars": int(bars or spec["bars"]), "instrument": instrument or self._default_instrument(slot),
                 "octave": 0, "gain_db": 0.0, "notes": [], "over": [], "takes": [], "take": None,
                 "repeat": bool(spec.get("repeat")), "chords": spec.get("chords", "A"), "audio": None,
                 "created": time.time()}
        if gen:
            piece["gen"] = gen
        self.data["next"] += 1
        self.pieces.append(piece)
        return piece

    def _default_sections(self, piece: dict):
        kinds = DEFAULT_PLAYS.get(piece["slot"], {"hook"})
        for s in self.data["sections"]:
            if _section_kind(s["name"]) in kinds and piece["id"] not in s["parts"]:
                s["parts"].append(piece["id"])

    def add_piece(self, slot: str, bars: int | None = None) -> dict:
        if slot not in RECORDABLE:
            raise ValueError("not a recordable slot")
        if bars is not None and bars not in (1, 2, 4, 8):
            raise ValueError("bars must be 1, 2, 4 or 8")
        piece = self._new_piece(slot, bars=bars)
        self.save()
        return piece

    def remove_piece(self, pid: str):
        self.piece(pid)
        self.data["pieces"] = [p for p in self.pieces if p["id"] != pid]
        for s in self.data["sections"]:
            s["parts"] = [x for x in s["parts"] if x != pid]
        self.save()

    def edit_piece(self, pid: str, **kw) -> dict:
        p = self.piece(pid)
        if "name" in kw and kw["name"]:
            p["name"] = str(kw["name"])[:40]
        if kw.get("instrument") and p["source"] != "voice":
            inst = kw["instrument"]
            if not (inst.startswith("kit:") or inst in INSTRUMENTS):
                raise ValueError("unknown instrument")
            p["instrument"] = inst
        if kw.get("octave") is not None:
            p["octave"] = int(np.clip(int(kw["octave"]), -2, 2))
        if kw.get("gain_db") is not None:
            p["gain_db"] = float(np.clip(float(kw["gain_db"]), -24, 12))
        if kw.get("repeat") is not None:
            p["repeat"] = bool(kw["repeat"])
        self.save()
        return p

    def note_op(self, pid: str, index: int, op: str) -> dict:
        """One-note fixes: up / down (a scale step; shift = half step), earlier / later (a 16th), longer /
        shorter (a 16th), delete."""
        p = self.piece(pid)
        notes = p["notes"]
        if not 0 <= index < len(notes):
            raise IndexError(index)
        s, l, pitch, v = notes[index]
        L = p["bars"] * 4
        if op in ("up", "down"):
            pitch = self._step(pitch, 1 if op == "up" else -1)
        elif op in ("up1", "down1"):
            pitch += 1 if op == "up1" else -1
        elif op == "earlier":
            s = max(0.0, s - 0.25)
        elif op == "later":
            s = min(L - 0.25, s + 0.25)
        elif op == "longer":
            l = min(L - s, l + 0.25)
        elif op == "shorter":
            l = max(0.25, l - 0.25)
        elif op == "delete":
            notes.pop(index)
            self.save()
            return p
        else:
            raise ValueError(op)
        notes[index] = [s, l, int(pitch), v]
        notes.sort(key=lambda n: n[0])
        self.save()
        return p

    def _step(self, pitch: int, d: int) -> int:
        """Next note of the key up or down."""
        scale = {(self.st["tonic"] + i) % 12 for i in theory.MODES.get(self.st["mode"], theory.MODES["major"])}
        q = pitch + d
        while q % 12 not in scale:
            q += d
        return q

    def variation(self, pid: str, kind: str) -> dict:
        """simpler: drop short off-beat notes / merge repeats. busier: split long notes into a rhythm.
        Drums: simpler keeps kick, snare and on-beat hats; busier adds 16th hats and ghost snares."""
        p = self.piece(pid)
        notes = [list(n) for n in p["notes"]]
        drums = p["instrument"].startswith("kit:")
        if kind == "simpler":
            if drums:
                notes = [n for n in notes if n[2] in (36, 38, 39, 64) or abs(n[0] - round(n[0])) < 0.01]
            else:
                keep = [n for n in notes if n[1] >= 0.5 or abs(n[0] - round(n[0])) < 0.01]
                notes = keep if len(keep) >= max(2, len(notes) // 2) else notes[::2]
                for a, b in zip(notes, notes[1:]):  # close the gaps left behind
                    a[1] = max(a[1], min(b[0] - a[0], 2.0))
        elif kind == "busier":
            if drums:
                have = {(n[0], n[2]) for n in notes}
                hat = 42 if p["slot"] != "perc" else 70
                for i in range(p["bars"] * 16):
                    if (i / 4, hat) not in have and i % 2 == 1:
                        notes.append([i / 4, 0.2, hat, 50])
                for b in range(p["bars"] * 4):
                    if (b + 0.75, 38) not in have and b % 2 == 1:
                        notes.append([b + 0.75, 0.2, 38, 36])
            else:
                out = []
                for s, l, pitch, v in notes:
                    if l >= 1.0:
                        k = int(l / 0.5)
                        out += [[s + i * 0.5, 0.45, pitch if i % 2 == 0 else self._step(pitch, 1), v] for i in range(k)]
                    else:
                        out.append([s, l, pitch, v])
                notes = out
        else:
            raise ValueError(kind)
        p["notes"] = sorted(notes)
        self.save()
        return p

    # --- takes -----------------------------------------------------------------------------------
    def add_recording(self, pid: str, audio: np.ndarray, sr: int, start: float, cal=None) -> list[dict]:
        """A loop recording for a piece. `start` = loop time (s) of sample 0, latency already removed.
        Every complete pass becomes a take; the best is picked (you can choose another)."""
        import soundfile as sf

        p = self.piece(pid)
        if p["source"] == "starter":
            raise ValueError("starter parts aren't recorded")
        rid = f"r{int(time.time() * 1000) % 10 ** 10}"
        sf.write(str(self.dir / "takes" / f"{rid}.wav"), audio, sr, subtype="FLOAT")
        bars = p["bars"]
        cycle_s = bars * 4 * self.spb
        if p["source"] == "beatbox":
            res = transcribe.beat(audio, sr, start, self.st["bpm"], bars, cal, perc=p["slot"] == "perc")
        else:
            res = transcribe.hum(audio, sr, start, self.st["bpm"], bars, self.st["tonic"], self.st["mode"])
        new = []
        for k, d in sorted(res.items()):
            t = {"id": f"{rid}-{k}", "recording": rid, "pass": k, "start": start, "sr": sr, "score": d["score"],
                 "detail": d["detail"], "notes": d["notes"], "created": time.time()}
            if p["source"] == "voice":
                t["audio"] = self._chop_audio(audio, sr, start, k, cycle_s, d["notes"], t["id"])
            p["takes"].append(t)
            new.append(t)
        if not new:
            raise ValueError("the recording didn't cover a whole pass: keep going until the loop comes round")
        best = max(new + [t for t in p["takes"] if t["id"] == p["take"]], key=lambda t: t["score"])
        self._use_take(p, best)
        self.save()
        return new

    def _chop_audio(self, audio, sr, start, k, cycle_s, notes, tid) -> str:
        """A vocal chop pass: cut on the loop, high-passed, gently tuned to the notes heard, level-matched."""
        import soundfile as sf

        from ..arrange import vocals

        x = transcribe.cut_pass(np.asarray(audio, dtype=np.float32), sr, start, k, cycle_s, render.SR)
        x = vocals._filt(x, vocals._sos("high", 110))
        if notes:
            ns = [vocals.Note(s * self.spb, (s + l) * self.spb, int(pt), i) for i, (s, l, pt, _) in enumerate(notes)]
            try:
                x, _, _ = vocals.correct(x, ns, vocals.preset("bright_pop"), {})
            except Exception:
                pass
        pk = float(np.abs(x).max()) or 1.0
        x = (x / pk * 0.7).astype(np.float32)
        name = f"chop-{tid}.wav"
        sf.write(str(self.dir / "takes" / name), x, render.SR, subtype="FLOAT")
        return name

    def _use_take(self, p: dict, t: dict):
        p["take"] = t["id"]
        p["notes"] = [list(n) for n in t["notes"]]
        p["audio"] = t.get("audio")
        # The chords it was sung over, per bar (for following other chords later).
        prog = self.progression(p["chords"], p["bars"], start_bar=t["pass"] * p["bars"])
        p["over"] = [c.root for _, _, c in prog]
        if not any(s for s in self.data["sections"] if p["id"] in s["parts"]):
            self._default_sections(p)
            if p["slot"] in ("beat", "bass"):  # your beat / bassline takes over from the starter's
                for s in self.data["sections"]:
                    for q in self.pieces:
                        if q["source"] == "starter" and q["slot"] == p["slot"] and q["id"] in s["parts"] \
                                and p["id"] in s["parts"]:
                            s["parts"].remove(q["id"])

    def choose_take(self, pid: str, tid: str) -> dict:
        p = self.piece(pid)
        t = next((t for t in p["takes"] if t["id"] == tid), None)
        if t is None:
            raise KeyError(tid)
        self._use_take(p, t)
        self.save()
        return p

    def delete_take(self, pid: str, tid: str) -> dict:
        p = self.piece(pid)
        p["takes"] = [t for t in p["takes"] if t["id"] != tid]
        if p["take"] == tid:
            if p["takes"]:
                self._use_take(p, max(p["takes"], key=lambda t: t["score"]))
            else:
                p["take"], p["notes"], p["audio"] = None, [], None
        self.save()
        return p

    # --- the board -------------------------------------------------------------------------------
    def set_sections(self, sections: list[dict]) -> list[dict]:
        ids = {p["id"] for p in self.pieces}
        out = []
        for i, s in enumerate(sections):
            bars = int(s.get("bars", 8))
            if bars not in (1, 2, 4, 8, 12, 16):
                raise ValueError("a section is 1, 2, 4, 8, 12 or 16 bars")
            out.append({"id": s.get("id") or f"s{time.time_ns() % 10 ** 9}{i}", "name": str(s.get("name", "Section"))[:24],
                        "bars": bars, "chords": "B" if s.get("chords") == "B" else "A",
                        "parts": [x for x in s.get("parts", []) if x in ids]})
        if not out:
            raise ValueError("a song needs at least one section")
        self.data["sections"] = out
        self.save()
        return out

    def set_key(self, tonic: int) -> None:
        """Move the whole track to another key: recorded notes move with it (by the nearest way)."""
        d = ((int(tonic) - self.st["tonic"]) + 6) % 12 - 6
        self.st["tonic"] = int(tonic) % 12
        for p in self.pieces:
            if not p["instrument"].startswith("kit:"):
                p["notes"] = [[s, l, pt + d, v] for s, l, pt, v in p["notes"]]
                for t in p["takes"]:
                    t["notes"] = [[s, l, pt + d, v] for s, l, pt, v in t["notes"]]
                p["over"] = [(r + d) % 12 for r in p["over"]]
        self.save()

    # --- turning pieces into notes ---------------------------------------------------------------
    def progression(self, which: str, bars: int, start_bar: int = 0) -> list:
        deg = self.st["b"] if which == "B" else self.st["a"]
        # A section's chords start from the loop's first chord, wherever the section starts.
        prog = starters.progression(deg, self.st["tonic"], self.st["ext"], bars)
        return [(s + start_bar * 4, l, c) for s, l, c in prog]

    def _degree(self, root: int) -> int:
        scale = theory.MODES.get(self.st["mode"], theory.MODES["major"])
        off = (root - self.st["tonic"]) % 12
        return max(i for i, x in enumerate(scale) if x <= off)

    def place(self, p: dict, start_bar: int, bars: int, chords: list, last_section: bool = False,
              melody: list | None = None, section_name: str = "") -> list[tuple]:
        """The piece's notes laid into a section starting at `start_bar`, `bars` long."""
        if p.get("gen"):
            kind = _section_kind(section_name)
            light = kind in ("intro", "outro")
            fills = p["gen"] == "drums" and bars >= 8 and not last_section
            return starters.generate(p["gen"], self.st, chords, (start_bar, start_bar + bars), fills=fills,
                                     light=light, melody=melody, rng=np.random.default_rng(hash(p["id"]) % 997))
        if not p["notes"]:
            return []
        L = p["bars"] * 4
        S = bars * 4
        if p["kind"] == "one" and SLOTS[p["slot"]].get("at_end"):
            offsets = [max(0, S - L)]
        elif p["kind"] == "one" and not p.get("repeat"):
            offsets = [0]
        else:
            offsets = list(range(0, S, L))
        drums = p["instrument"].startswith("kit:")
        out = []
        for off in offsets:
            for s, l, pitch, v in p["notes"]:
                t = off + s
                if t >= S:
                    continue
                l = min(l, S - t)
                if not drums and p["over"]:
                    target = next((c for cs, cl, c in chords if cs <= (start_bar * 4 + t) < cs + cl), None)
                    src_root = p["over"][int(s // 4) % len(p["over"])]
                    if target is not None and target.root != src_root:
                        steps = self._degree(target.root) - self._degree(src_root)
                        steps = (steps + 3) % 7 - 3  # the nearest way
                        pitch = self._shift(pitch, steps)
                out.append((start_bar * 4 + t, l, int(pitch), int(v)))
        if p["slot"] == "stab":
            out = self._stabs(out, chords)
        return out

    def _shift(self, pitch: int, steps: int) -> int:
        q = pitch
        for _ in range(abs(steps)):
            q = self._step(q, 1 if steps > 0 else -1)
        return q

    def _stabs(self, notes: list[tuple], chords: list) -> list[tuple]:
        """Each hummed hit becomes a short 3-note chord of the chord sounding then, topped by the chord tone
        nearest what you hummed."""
        out = []
        for s, l, pitch, v in notes:
            c = next((c for cs, cl, c in chords if cs <= s < cs + cl), None)
            if c is None:
                continue
            pcs = sorted({(c.root + i) % 12 for i in theory.QUALITIES[c.quality]})
            top = min((pitch + d for d in range(-6, 7) if (pitch + d) % 12 in pcs), key=lambda q: abs(q - pitch))
            while top > 82:
                top -= 12
            while top < 64:
                top += 12
            voices = [top]
            q = top
            while len(voices) < 3:
                q -= 1
                if q % 12 in pcs:
                    voices.append(q)
            for x in voices:
                out.append((s, min(l, 0.5), x, min(120, v + 10)))
        return out

    def _instrument_notes(self, p: dict, notes: list[tuple]) -> list[tuple]:
        if p["instrument"].startswith("kit:") or p["source"] == "voice" or not notes:
            return notes
        notes = arranger.fit_range(notes, p["instrument"])
        if p["octave"]:
            lo, hi = INSTRUMENTS[p["instrument"]][2:4]
            shifted = [(s, l, pt + 12 * p["octave"], v) for s, l, pt, v in notes]
            if all(lo - 5 <= x[2] <= hi + 5 for x in shifted):
                notes = shifted
        return notes

    def _track(self, p: dict, notes: list[tuple]) -> arranger.Track:
        role = MIX_ROLE.get(p["role"], "riff")
        return arranger.Track(p["name"], role, p["instrument"], self._instrument_notes(p, notes),
                              mine=p["source"] != "starter", pan=PAN.get(role, 0.0))

    def _song(self, sections: list[tuple], chords: list, tracks: list) -> arranger.Song:
        return arranger.Song(pack=self.st["pack"], bpm=float(self.st["bpm"]), tonic=self.st["tonic"],
                             mode=self.st["mode"], swing=self.pack["swing"], sections=sections, chords=chords,
                             tracks=tracks, seed=int(hashlib.sha1(self.data["id"].encode()).hexdigest()[:6], 16))

    # --- booth: one loop per piece ---------------------------------------------------------------
    def cycle_bars(self, p: dict) -> int:
        return max(4, p["bars"])

    def booth_stem(self, pid: str, which: str = "A") -> tuple[str, float]:
        """One seamless loop of the piece over chords A or B (rendered 3 times, the middle one kept so
        reverb tails wrap around). Returns (file name in stems/, loop seconds). Cached by content."""
        p = self.piece(pid)
        cb = self.cycle_bars(p)
        key = json.dumps([p["notes"], p["instrument"], p["octave"], p.get("gen"), p.get("audio"), p["over"], which, cb,
                          self.st["tonic"], self.st["bpm"], self.st["a"], self.st["b"], p["slot"]], default=float)
        name = f"booth-{pid}-{which}-{hashlib.sha1(key.encode()).hexdigest()[:12]}.ogg"
        loop_s = cb * 4 * self.spb
        path = self.dir / "stems" / name
        if path.exists():
            return name, loop_s
        n = int(round(loop_s * render.SR))
        if p["source"] == "voice":
            x = self._chop_loop(p, cb)
        elif not p["notes"] and not p.get("gen"):
            x = np.zeros((2, n), dtype=np.float32)
        else:
            bars = 3 * cb
            chords = self.progression(which, bars)
            notes = self.place(p, 0, bars, chords, section_name="Verse")
            song = self._song([("A", 0, bars)], chords, [])
            t = self._track(p, notes)
            song.tracks = [t]
            full = render.render_stem(t, song, np.random.default_rng(1))
            x = full[:, n:2 * n]
            if x.shape[1] < n:
                x = np.pad(x, ((0, 0), (0, n - x.shape[1])))
        for old in (self.dir / "stems").glob(f"booth-{pid}-{which}-*.ogg"):
            old.unlink()
        render.write_audio(x, path)
        return name, loop_s

    def _chop_loop(self, p: dict, cb: int) -> np.ndarray:
        import soundfile as sf

        n = int(round(cb * 4 * self.spb * render.SR))
        out = np.zeros(n, dtype=np.float32)
        if p.get("audio"):
            a, _ = sf.read(str(self.dir / "takes" / p["audio"]), dtype="float32")
            L = len(a)
            for off in range(0, n, max(1, L)):
                seg = a[: n - off]
                out[off:off + len(seg)] += seg
        out = _level(out, render.LEVEL["lead"] - 4)
        return np.stack([out, out]).astype(np.float32)

    def public(self) -> dict:
        d = dict(self.data)
        d["style"] = self.pack["title"]
        d["key"] = f"{theory.NAMES[self.st['tonic']]} {self.st['mode']}"
        d["chords_a"] = [c.name for _, _, c in self.progression("A", 4)]
        d["chords_b"] = [c.name for _, _, c in self.progression("B", 4)]
        d["slots"] = {k: {kk: vv for kk, vv in v.items()} for k, v in SLOTS.items()}
        d["recordable"] = RECORDABLE
        pieces = []
        for p in self.pieces:
            q = dict(p)
            q["takes"] = [{k: v for k, v in t.items() if k != "notes"} for t in p["takes"]]
            q["choices"] = _choices(p)
            pieces.append(q)
        d["pieces"] = pieces
        return d

    # --- the whole song --------------------------------------------------------------------------
    def song(self) -> tuple[arranger.Song, list[dict]]:
        """The song as the board says. Returns (Song, audio parts [{piece, sections}] for chops)."""
        secs, chords, start = [], [], 0
        for s in self.data["sections"]:
            secs.append((s["name"], start, s["bars"]))
            chords += self.progression(s["chords"], s["bars"], start_bar=start)
            start += s["bars"]
        tracks: dict[str, list] = {}
        audio: dict[str, list] = {}
        # Melodies first, so generated chords can step out of their way (H1).
        order = sorted(self.pieces, key=lambda p: 0 if p["role"] == "lead" else 1)
        melody: list = []
        for p in order:
            for s, (name, sb, bars) in zip(self.data["sections"], secs):
                if p["id"] not in s["parts"]:
                    continue
                if p["source"] == "voice":
                    audio.setdefault(p["id"], []).append((sb, bars))
                    continue
                sec_chords = [c for c in chords if sb * 4 <= c[0] < (sb + bars) * 4]
                notes = self.place(p, sb, bars, sec_chords, last_section=s is self.data["sections"][-1],
                                   melody=melody, section_name=name)
                tracks.setdefault(p["id"], []).extend(notes)
                if p["role"] == "lead":
                    melody += notes
        out_tracks = [self._track(self.piece(pid), sorted(n)) for pid, n in tracks.items() if n]
        song = self._song(secs, chords, out_tracks)
        return song, [{"piece": self.piece(pid), "where": w} for pid, w in audio.items()]

    def chop_stem(self, p: dict, where: list, total_bars: int) -> np.ndarray:
        """A vocal chop across the song: its loop audio laid into each section it plays in."""
        import soundfile as sf

        _, n = render.song_length(self._song([("A", 0, total_bars)], [], []))
        out = np.zeros(n, dtype=np.float32)
        if not p.get("audio"):
            return np.stack([out, out])
        a, _ = sf.read(str(self.dir / "takes" / p["audio"]), dtype="float32")
        bar_n = 4 * self.spb * render.SR
        for sb, bars in where:
            i0, i1 = int(sb * bar_n), int((sb + bars) * bar_n)
            for off in range(i0, i1, max(1, len(a))):
                seg = a[: min(len(a), i1 - off, n - off)]
                out[off:off + len(seg)] += seg
        from pedalboard import Pedalboard, Reverb

        out = _level(out, render.LEVEL["lead"] - 4)
        st = np.stack([out, out]).astype(np.float32)
        st = st + 0.4 * Pedalboard([Reverb(room_size=0.4, wet_level=1.0, dry_level=0.0)])(st * 0.2, render.SR)
        return st.astype(np.float32)

    def build(self, lib) -> dict:
        """Render the song as the board says, check it, and put it in the Songs list (a new version of
        the same song when you rebuild), so Mix, Lyrics and Sing work on it."""
        from ..arrange.mixer import next_version_index
        from ..arrange.songwriter import song_summary

        song, chops = self.song()
        if not song.tracks and not chops:
            raise ValueError("nothing to play yet: turn some pieces on in the song board")
        _, n = render.song_length(song)
        duck = render._sidechain(n, render.kick_times(song))
        mix = np.zeros((2, n), dtype=np.float32)
        stems: dict = {}
        gains = {p["name"]: p["gain_db"] for p in self.pieces}
        for t in song.tracks:
            x = render.render_stem(t, song, np.random.default_rng(len(t.notes)), duck, gains.get(t.name, 0.0))
            mix += x
            stems[t.role] = stems.get(t.role, 0) + x
        song_id = self.data.get("song_id")
        sdir = lib.song_dir(song_id) if song_id and lib.get_song(song_id) else None
        if sdir is None:
            song_id = f"make-{self.data['id']}"
            sdir = lib.song_dir(song_id)
        (sdir / "stems").mkdir(parents=True, exist_ok=True)
        audio_parts = []
        for c in chops:
            p = c["piece"]
            x = self.chop_stem(p, c["where"], song.bars) * 10 ** (p["gain_db"] / 20)
            name = f"chop-{p['id']}-{hashlib.sha1(x[:, ::101].tobytes()).hexdigest()[:10]}.ogg"
            render.write_audio(x, sdir / "stems" / name)
            mix += x[:, :n]
            stems["riff"] = stems.get("riff", 0) + x[:, :n]
            audio_parts.append({"id": f"a-{p['id']}", "name": p["name"], "role": "chop", "file": name})
        master = render.master(mix)
        verdict = critic.judge(song, master, stems)
        record = json.loads((sdir / "song.json").read_text()) if (sdir / "song.json").exists() else None
        idx = next_version_index(sdir, record) if record else 0
        render.write_audio(master, sdir / f"v{idx}.ogg")
        render.write_midi(song, sdir / f"v{idx}.mid")
        summary = song_summary(song)
        version = {"file": f"v{idx}.ogg", "midi": f"v{idx}.mid", "score": verdict["score"], "critic": verdict,
                   "title": f"{self.data['title']} · {self.pack['title']}",
                   "spec": {"clips": [], "seed": song.seed, "project": self.data["id"], "starter": self.st["id"]},
                   **summary, "audio_parts": audio_parts,
                   "added": [p["name"] for p in self.pieces if p["source"] == "starter"
                             and any(p["id"] in s["parts"] for s in self.data["sections"])]}
        if record:
            record["versions"].append(version)
            write_json(sdir / "song.json", record)
            lib.update_song(song_id, record, len(record["versions"]) - 1)
        else:
            record = {"created": time.time(), "primary": None, "versions": [version], "project": self.data["id"],
                      "summary": f"Built from your Make track \"{self.data['title']}\"."}
            write_json(sdir / "song.json", record)
            lib.add_song(song_id, record)
        self.data["song_id"] = song_id
        self.save()
        return {"song_id": song_id, "version": len(record["versions"]) - 1, "critic": verdict,
                "seconds": round(n / render.SR, 1)}


def _choices(p: dict) -> list[str]:
    if p["source"] == "voice":
        return []
    if p["instrument"].startswith("kit:"):
        return ["kit:" + k for k in ("standard", "room", "power", "electronic", "tr808", "dance", "jazz", "brush")]
    fam = INSTRUMENTS.get(p["instrument"], (0, 0, 0, 0, "keys", 1))[4]
    if p["role"] == "bass":
        fams = ("bass",)
    elif p["role"] in ("lead", "counter", "riff"):
        fams = ("keys", "mallet", "guitar", "strings", "brass", "wind", "synth", "reed", "world", "voice")
    else:
        fams = (fam,)
    same = [k for k, v in INSTRUMENTS.items() if v[4] in fams]
    return [p["instrument"]] + [k for k in same if k != p["instrument"]]



def _level(x: np.ndarray, level_db: float) -> np.ndarray:
    """Same loudness rule as render.render_stem: the sounding part's RMS set from the role's level."""
    active = np.abs(x) > 1e-4
    if not active.any():
        return x
    rms = float(np.sqrt(np.mean(x[active] ** 2)))
    return (x * 10 ** (level_db / 20) / rms * 0.25).astype(np.float32)
