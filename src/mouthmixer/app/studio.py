"""The studio API: mixer (Incredibox-style parts), lyrics and vocals for a song.

Routes live under /api/songs/{song_id}/... and work on one version of the song (`v`, default the version
the app is showing). Anything that makes a new version updates the song's current version.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from .. import config
from ..arrange import catalog, lyrics, mixer, vocals
from ..arrange.styles import PACKS

_locks: dict[str, threading.Lock] = {}


def _lock(song_id: str) -> threading.Lock:
    return _locks.setdefault(song_id, threading.Lock())


def add_routes(app: FastAPI, lib, settings: config.Settings) -> None:

    def song_dir(song_id: str) -> Path:
        if not lib.get_song(song_id):
            raise HTTPException(404, "no such song")
        return lib.song_dir(song_id)

    def record(song_id: str) -> dict:
        return json.loads((song_dir(song_id) / "song.json").read_text())

    def version_of(song_id: str, v) -> int:
        rec = record(song_id)  # 404 for an unknown song
        if v is None:
            return int(lib.get_song(song_id)["version"])
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise HTTPException(400, "no such version")
        if not 0 <= v < len(rec["versions"]):
            raise HTTPException(400, "no such version")
        return v

    def mx(song_id: str, v: int | None) -> mixer.Mixer:
        return mixer.Mixer(song_dir(song_id), version_of(song_id, v))

    def state(m: mixer.Mixer, render: bool = True) -> dict:
        if render:
            m.render_stems()
        return m.public() | {"lead_mode": m.state.get("lead_mode", "duck")}

    def new_version(song_id: str, new: dict) -> dict:
        rec = record(song_id)
        idx = next(i for i, x in enumerate(rec["versions"]) if x["file"] == new["file"])
        lib.update_song(song_id, rec, idx)
        return {"version": idx, "title": new["title"], "critic": new["critic"],
                "vocals": new.get("vocals")}

    # --- settings ------------------------------------------------------------------------------------
    @app.get("/api/settings")
    def get_settings():
        s = config.Settings.load()
        return {"has_claude_key": bool(s.claude_api_key or os.environ.get("ANTHROPIC_API_KEY")),
                "claude_key_from_env": bool(os.environ.get("ANTHROPIC_API_KEY")) and not s.claude_api_key,
                "vocal_latency_ms": s.vocal_latency_ms, "latency_measured": s.measured_for("worklet"),
                "background_listening": s.background_listening}

    @app.post("/api/settings")
    def set_settings(body: dict = Body(...)):
        s = config.Settings.load()
        if "claude_api_key" in body:
            s.claude_api_key = str(body["claude_api_key"] or "").strip()
        if "vocal_latency_ms" in body:
            try:
                s.vocal_latency_ms = float(max(-500.0, min(1000.0, float(body["vocal_latency_ms"]))))
            except (TypeError, ValueError):
                raise HTTPException(400, "vocal_latency_ms is a number of milliseconds")
            s.latency_measured = True
            s.latency_pipeline = body.get("latency_pipeline") if body.get("latency_pipeline") in ("worklet", "script") else "worklet"
        if "background_listening" in body:
            on = bool(body["background_listening"])
            if on != s.background_listening:
                s.background_listening = on
                if on:
                    try:
                        from ..launcher import _spawn, listener_running

                        if not listener_running():
                            _spawn(["listen"])
                    except Exception:
                        pass
                else:
                    (config.paths()["control"] / f"quit-{time.time_ns()}.cmd").write_text("")
        s.save()
        settings.claude_api_key, settings.vocal_latency_ms = s.claude_api_key, s.vocal_latency_ms
        settings.background_listening = s.background_listening
        return get_settings()

    # --- mixer ---------------------------------------------------------------------------------------
    @app.get("/api/songs/{song_id}/mixer")
    def mixer_state(song_id: str, v: int | None = None):
        with _lock(song_id):
            return state(mx(song_id, v))

    @app.get("/api/songs/{song_id}/stems/{name}")
    def stem(song_id: str, name: str):
        d = (song_dir(song_id) / "stems").resolve()
        p = (d / name).resolve()
        if p.parent != d or not p.exists() or p.suffix != ".ogg":
            raise HTTPException(404)
        return FileResponse(p, media_type="audio/ogg")

    @app.post("/api/songs/{song_id}/mixer/part")
    def mixer_part(song_id: str, body: dict = Body(...)):
        with _lock(song_id):
            m = mx(song_id, body.get("v"))
            try:
                m.set(body["id"], muted=body.get("muted"), gain_db=body.get("gain_db"),
                      instrument=body.get("instrument"), pan=body.get("pan"))
            except KeyError:
                raise HTTPException(404, "no such part")
            except (TypeError, ValueError) as e:
                raise HTTPException(400, f"bad value: {e}")
            if body.get("lead_mode") in ("duck", "mute", "keep"):
                m.state["lead_mode"] = body["lead_mode"]
                m.save_state()
            return state(m, render=bool(body.get("instrument")))

    @app.post("/api/songs/{song_id}/mixer/add")
    def mixer_add(song_id: str, body: dict = Body(...)):
        if body.get("kind") not in catalog.PARTS:
            raise HTTPException(400, "unknown part")
        with _lock(song_id):
            m = mx(song_id, body.get("v"))
            part = m.add(body["kind"], body.get("instrument"))
            return state(m) | {"added": part["id"]}

    @app.post("/api/songs/{song_id}/mixer/remove")
    def mixer_remove(song_id: str, body: dict = Body(...)):
        with _lock(song_id):
            m = mx(song_id, body.get("v"))
            try:
                m.remove(body["id"])
            except KeyError:
                raise HTTPException(404, "no such part")
            except ValueError as e:
                raise HTTPException(400, str(e))
            return state(m, render=False)

    @app.post("/api/songs/{song_id}/mixer/vocal_hits")
    def mixer_vocal_hits(song_id: str, body: dict = Body(default={})):
        with _lock(song_id):
            m = mx(song_id, body.get("v"))
            try:
                added = m.vocal_hits(body.get("amount", "some"))
            except ValueError as e:
                raise HTTPException(400, str(e))
            hits = len({n[0] for n in added[0]["notes"]}) if added else 0
            return state(m) | {"added": [p["id"] for p in added], "hits": hits}

    @app.get("/api/songs/{song_id}/mixer/suggest")
    def mixer_suggest(song_id: str, v: int | None = None, vibe: str | None = None):
        m = mx(song_id, v)
        parts = [p for p in m.parts if not p.get("muted")]
        return {"vibes": [{"id": k, "label": val} for k, val in catalog.VIBES.items()], "vibe": vibe,
                "pack_vibes": catalog.PACK_VIBES.get(m.v["pack"], []), "categories": catalog.CATEGORIES,
                "suggestions": catalog.suggest(parts, m.v["pack"], vibe)}

    @app.post("/api/songs/{song_id}/mixer/save")
    def mixer_save(song_id: str, body: dict = Body(default={})):
        with _lock(song_id):
            m = mx(song_id, body.get("v"))
            if body.get("lead_mode") in ("duck", "mute", "keep"):
                m.state["lead_mode"] = body["lead_mode"]
                m.save_state()
            return new_version(song_id, m.bake())

    # --- lyrics --------------------------------------------------------------------------------------
    def lyric_view(v: dict) -> dict:
        smap = lyrics.syllable_map(v)
        lyr = v.get("lyrics") or {}
        chosen = lyr.get("chosen")
        opts = lyr.get("options", [])
        events = lyrics.align(opts[chosen], smap) if chosen is not None and chosen < len(opts) else []
        return {"map": smap, "brief": lyr.get("brief", ""), "options": opts, "chosen": chosen, "events": events,
                "bpm": v["bpm"]}

    def save_lyrics(song_id: str, vi: int, change) -> dict:
        d = song_dir(song_id)
        with _lock(song_id):
            rec = json.loads((d / "song.json").read_text())
            v = rec["versions"][vi]
            lyr = v.setdefault("lyrics", {"options": [], "chosen": None, "brief": ""})
            change(lyr)
            mixer.write_json(d / "song.json", rec)
            return lyric_view(v)

    @app.get("/api/songs/{song_id}/lyrics")
    def get_lyrics(song_id: str, v: int | None = None):
        return lyric_view(record(song_id)["versions"][version_of(song_id, v)])

    @app.post("/api/songs/{song_id}/lyrics/write")
    def write_lyrics(song_id: str, body: dict = Body(...)):
        vi = version_of(song_id, body.get("v"))
        v = record(song_id)["versions"][vi]
        key = config.Settings.load().claude_api_key or None
        if not key and not os.environ.get("ANTHROPIC_API_KEY"):
            raise HTTPException(400, "add your Claude API key in Setup first (or type your own lyrics)")
        try:
            opts = lyrics.write(str(body.get("brief", "")), v, api_key=key)
        except lyrics.LyricsError as e:
            raise HTTPException(502, str(e))

        def change(lyr):
            lyr["brief"] = str(body.get("brief", ""))
            lyr["options"] = opts + [o for o in lyr["options"] if o.get("idea") == "your own words"]
            lyr["chosen"] = 0 if opts else lyr.get("chosen")

        return save_lyrics(song_id, vi, change)

    @app.post("/api/songs/{song_id}/lyrics/own")
    def own_lyrics(song_id: str, body: dict = Body(...)):
        vi = version_of(song_id, body.get("v"))
        v = record(song_id)["versions"][vi]
        secs = body.get("sections") or {}
        if not isinstance(secs, dict):
            raise HTTPException(400, "sections is {section name: words}")
        opt = lyrics.from_text(str(body.get("title", "")), {str(k): str(t) for k, t in secs.items()}, v)

        def change(lyr):
            lyr["options"] = [o for o in lyr["options"] if o.get("idea") != "your own words"] + [opt]
            lyr["chosen"] = len(lyr["options"]) - 1

        return save_lyrics(song_id, vi, change)

    @app.post("/api/songs/{song_id}/lyrics/choose")
    def choose_lyrics(song_id: str, body: dict = Body(...)):
        vi = version_of(song_id, body.get("v"))

        def change(lyr):
            i = body.get("index")
            try:
                i = None if i is None else int(i)
            except (TypeError, ValueError):
                raise HTTPException(400, "no such option")
            if i is not None and not 0 <= i < len(lyr["options"]):
                raise HTTPException(400, "no such option")
            lyr["chosen"] = None if i is None else int(i)

        return save_lyrics(song_id, vi, change)

    # --- singing: takes and vocals -------------------------------------------------------------------
    def takes_path(song_id: str) -> Path:
        p = song_dir(song_id) / "takes"
        p.mkdir(exist_ok=True)
        return p

    def takes_list(song_id: str) -> list[dict]:
        f = takes_path(song_id) / "takes.json"
        return json.loads(f.read_text()) if f.exists() else []

    def save_takes(song_id: str, items: list[dict]) -> None:
        mixer.write_json(takes_path(song_id) / "takes.json", items)

    def load_take(song_id: str, t: dict) -> vocals.Take:
        import soundfile as sf

        x, sr = sf.read(str(takes_path(song_id) / t["file"]), dtype="float32", always_2d=True)
        lat = t["latency_ms"]
        s = config.Settings.load()
        if t.get("latency_estimated") and s.measured_for(t.get("pipeline", "worklet")):  # recorded on a guess; measured since
            lat = s.vocal_latency_ms
        return vocals.Take.from_recording(x.mean(axis=1), sr, t["start_sec"], lat, t["id"])

    def lead_notes(v: dict) -> list:
        return [n for t in v["tracks"] if t["role"] == "lead" for n in t["notes"]]

    @app.get("/api/vocal_presets")
    def vocal_presets():
        return [{"id": k, "label": p["label"]} for k, p in vocals.PRESETS.items()]

    @app.get("/api/vocal_options")
    def vocal_options():
        from ..arrange.mixer import VOCAL_TRACKS

        return {"presets": [{"id": k, "label": p["label"]} for k, p in vocals.PRESETS.items()],
                "characters": [{"id": k, "label": c["label"]} for k, c in vocals.CHARACTERS.items()],
                "tracks": list(VOCAL_TRACKS), "tweaks": vocals.TWEAKS}

    @app.get("/api/songs/{song_id}/takes")
    def get_takes(song_id: str):
        rec = record(song_id)
        v = rec["versions"][version_of(song_id, None)]
        return {"takes": takes_list(song_id), "preset": PACKS[v["pack"]].get("vocal_preset", "soul"),
                "latency_ms": config.Settings.load().vocal_latency_ms,
                "latency_measured": config.Settings.load().measured_for("worklet")}

    @app.post("/api/songs/{song_id}/takes")
    async def add_take(song_id: str, request: Request, start: float = 0.0, section: str = "", v: int | None = None,
                       track: str = "Lead", est_ms: float | None = None, gaps: int = 0, pipe: str = "worklet"):
        """A recorded take (WAV body). `start`: the song position (seconds) when recording began."""
        import soundfile as sf

        from .server import _wav_from_body

        body = await request.body()
        try:
            x, sr = _wav_from_body(body)
        except Exception:
            raise HTTPException(400, "not a WAV file")
        if len(x) < sr // 2:
            raise HTTPException(400, "that take is too short")
        vi = version_of(song_id, v)
        tid = time.strftime("%H%M%S") + "-" + uuid.uuid4().hex[:4]
        sf.write(str(takes_path(song_id) / f"{tid}.wav"), x, sr, subtype="FLOAT")
        t = {"id": tid, "file": f"{tid}.wav", "start_sec": start, "latency_ms": config.Settings.load().latency_ms(est_ms, pipe),
             "section": section, "version": vi, "created": time.time(), "seconds": round(len(x) / sr, 2),
             "track": str(track or "Lead")[:20],
             "latency_estimated": not config.Settings.load().measured_for(pipe) and est_ms is not None,
             "pipeline": pipe, "dropouts": int(gaps)}
        v_ = record(song_id)["versions"][vi]
        notes = vocals.notes_in_seconds(lead_notes(v_), v_["bpm"], v_["sections"])
        t["score"] = vocals.score_take(load_take(song_id, t), notes)
        with _lock(song_id):
            items = takes_list(song_id) + [t]
            save_takes(song_id, items)
        return t

    @app.delete("/api/songs/{song_id}/takes/{tid}")
    def delete_take(song_id: str, tid: str):
        with _lock(song_id):
            items = takes_list(song_id)
            keep = [t for t in items if t["id"] != tid]
            for t in items:
                if t["id"] == tid:
                    (takes_path(song_id) / t["file"]).unlink(missing_ok=True)
            save_takes(song_id, keep)
        return {"ok": True}

    @app.get("/api/songs/{song_id}/takes/{tid}/audio")
    def take_audio(song_id: str, tid: str):
        for t in takes_list(song_id):
            if t["id"] == tid:
                return FileResponse(takes_path(song_id) / t["file"], media_type="audio/wav")
        raise HTTPException(404)

    @app.post("/api/songs/{song_id}/vocals/preview")
    def preview_vocals(song_id: str, body: dict = Body(default={})):
        """A few seconds of your newest take on a track with a voice and tweaks, no band: a WAV to listen to."""
        import io

        import numpy as np
        import soundfile as sf
        from fastapi.responses import Response

        track = str(body.get("track") or "Lead")[:20]
        items = [t for t in takes_list(song_id) if t.get("track", "Lead") == track]
        if body.get("take"):
            items = [t for t in takes_list(song_id) if t["id"] == str(body["take"])]
        if not items:
            raise HTTPException(400, f"record a take on the {track} track first")
        t = items[-1]
        m = mx(song_id, body.get("v"))
        song = m.song(False)
        modes = {x["section"]: x.get("mode", "sung") for x in m.v.get("lyric_sheet", [])}
        for sec, feel in zip(m.v["sections"], m.v.get("section_feels", [])):
            if feel == "rap":
                modes.setdefault(sec["name"], "rap")
        untuned = track in ("Rap", "Announcer", "Whisper") or modes.get(t.get("section")) in ("rap", "spoken", "whisper")
        character = body.get("character") if body.get("character") in vocals.CHARACTERS else "natural"
        preset = body.get("preset") if body.get("preset") in vocals.PRESETS else PACKS[m.v["pack"]].get("vocal_preset")
        tweaks = vocals.clean_tweaks(body.get("tweaks"))
        tk = load_take(song_id, t)
        try:
            y, at = vocals.preview(tk, song.tonic, song.mode, preset, character, tweaks, untuned=untuned,
                                   with_start=True)
        except ValueError as e:
            raise HTTPException(400, str(e))
        if body.get("band"):  # the same seconds of the song under it, to hear whether it sits on the beat
            from ..arrange import render

            with _lock(song_id):
                m.render_stems()
                total, n = render.song_length(m.song(False))
                music, _, _, _ = m._stems(n)
            a = int(round((at + tweaks.get("timing", 0.0) / 1000) * vocals.SR))
            seg = np.zeros_like(y)
            lo, hi = max(0, a), min(music.shape[1], a + y.shape[1])
            if hi > lo:
                seg[:, lo - a:hi - a] = music[:, lo:hi]
            y = y * 0.8 + seg * 0.55
            y = (y / max(1.0, float(np.abs(y).max()) / 0.89)).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, y.T, vocals.SR, format="WAV", subtype="PCM_16")
        return Response(buf.getvalue(), media_type="audio/wav")

    @app.post("/api/songs/{song_id}/vocals")
    def make_vocals(song_id: str, body: dict = Body(default={})):
        """Comp, clean, tune, time, process and mix the takes into a new version of the song."""
        track = str(body.get("track") or "Lead")[:20]
        items = [t for t in takes_list(song_id) if t.get("track", "Lead") == track]
        if body.get("takes"):
            if not isinstance(body["takes"], list):
                raise HTTPException(400, "takes is a list of take ids")
            items = [t for t in items if t["id"] in {str(x) for x in body["takes"]}]
        if not items:
            raise HTTPException(400, "record a take first")
        lead_mode = body.get("lead_mode", "duck")
        if lead_mode not in ("duck", "mute", "keep"):
            raise HTTPException(400, "lead_mode is duck, mute or keep")
        preset = body.get("preset")
        if preset and preset not in vocals.PRESETS:
            raise HTTPException(400, "unknown preset")
        with _lock(song_id):
            m = mx(song_id, body.get("v"))
            takes = [load_take(song_id, t) for t in items]
            lyr = m.v.get("lyrics")
            try:
                tune = body.get("tune", "auto") if body.get("tune") in ("auto", "melody", "key") else "auto"
                character = body.get("character") if body.get("character") in vocals.CHARACTERS else "natural"
                ids = {t["id"] for t in items}
                choice = {str(k): str(v) for k, v in (body.get("choice") or {}).items() if str(v) in ids} \
                    if isinstance(body.get("choice"), dict) else None
                new = m.with_vocals(takes, preset, lead_mode, choice=choice or None, lyrics=lyr, tune=tune, track=track,
                                    character=character, tweaks=vocals.clean_tweaks(body.get("tweaks")))
            except ValueError as e:
                raise HTTPException(400, str(e))
        return new_version(song_id, new)
