"""The Make tab's API: starter beats, projects, pieces, booth recordings, takes, the song board, build."""

from __future__ import annotations

import threading

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from .. import config
from ..analysis import beatbox
from ..studio import starters
from ..studio.project import Project, delete_favourite, list_favourites, list_projects

_locks: dict[str, threading.Lock] = {}


def _lock(pid: str) -> threading.Lock:
    return _locks.setdefault(pid, threading.Lock())


def add_routes(app: FastAPI, lib, paths: dict) -> None:

    def proj(pid: str) -> Project:
        try:
            return Project.load(pid)
        except KeyError:
            raise HTTPException(404, "no such track")

    def bad(e: Exception):
        raise HTTPException(400, str(e))

    @app.get("/api/starters")
    def get_starters():
        return {"moods": [{"id": k, **v} for k, v in starters.MOODS.items()], "starters": starters.public()}

    @app.get("/api/presets")
    def get_presets():
        from ..studio import presets

        return presets.public()

    @app.post("/api/projects/{pid}/presets")
    def add_preset(pid: str, body: dict = Body(...)):
        with _lock(pid):
            p = proj(pid)
            try:
                q = p.add_preset(str(body.get("preset", "")))
            except KeyError:
                raise HTTPException(404, "no such ready-made part")
            return p.public() | {"added": q["id"]}

    @app.get("/api/projects")
    def projects():
        return list_projects()

    @app.get("/api/songbook")
    def get_songbook():
        from ..studio import songbook

        return songbook.songs()

    @app.post("/api/projects")
    def create(body: dict = Body(...)):
        if body.get("songbook"):
            from ..studio import songbook

            try:
                song = songbook.get(body["songbook"])
            except KeyError:
                raise HTTPException(404, "no such song in the songbook")
            p = Project.create(song["starter"], song["title"])
            p.apply_lyrics(song["lyrics"])
            p.data["songbook"] = {k: song.get(k, "") for k in ("id", "slot", "voices", "hits", "notes")}
            p.save()
            return p.public()
        if body.get("starter") not in starters.STARTERS:
            raise HTTPException(400, "pick a starter beat")
        p = Project.create(body["starter"], str(body.get("title", ""))[:60])
        return p.public()

    @app.get("/api/projects/{pid}")
    def get(pid: str):
        return proj(pid).public()

    @app.post("/api/projects/{pid}")
    def update(pid: str, body: dict = Body(...)):
        with _lock(pid):
            p = proj(pid)
            try:
                return _update(p, body)
            except (TypeError, ValueError, AttributeError) as e:
                bad(e)

    def _update(p: Project, body: dict) -> dict:
        if "title" in body:
            p.data["title"] = str(body["title"])[:60] or p.data["title"]
            p.save()
        if "tonic" in body:
            p.set_key(int(body["tonic"]))
        if body.get("combo"):
            try:
                p.apply_combo(str(body["combo"]))
            except KeyError:
                raise HTTPException(404, "no such combo")
        if body.get("lyrics"):
            try:
                p.apply_lyrics(str(body["lyrics"])[:20000])
            except ValueError as e:
                bad(e)
        if "sections" in body:
            try:
                p.set_sections(body["sections"])
            except ValueError as e:
                bad(e)
        return p.public()

    @app.delete("/api/projects/{pid}")
    def delete(pid: str):
        import shutil

        p = proj(pid)
        shutil.rmtree(p.dir)
        return {"ok": True}

    @app.get("/api/projects/{pid}/booth")
    def booth(pid: str, chords: str = "A"):
        """One seamless loop per piece (rendered on demand, cached), for the booth's Incredibox row."""
        with _lock(pid):
            p = proj(pid)
            out = []
            for q in p.pieces:
                if (not q["notes"] and not q.get("gen") and not q.get("audio")) or q.get("gen") in ("fx", "chime", "keys"):
                    continue  # risers and the chime only happen at section changes, not in the loop
                name, secs = p.booth_stem(q["id"], "B" if chords == "B" else "A")
                out.append({"id": q["id"], "stem": name, "seconds": secs})
            return {"loops": out, "bar_seconds": 4 * p.spb, "bpm": p.st["bpm"]}

    @app.get("/api/projects/{pid}/stems/{name}")
    def stem(pid: str, name: str):
        p = proj(pid)
        d = (p.dir / "stems").resolve()
        f = (d / name).resolve()
        if f.parent != d or not f.exists() or f.suffix != ".ogg":
            raise HTTPException(404)
        return FileResponse(f, media_type="audio/ogg")

    @app.post("/api/projects/{pid}/pieces")
    def add_piece(pid: str, body: dict = Body(...)):
        with _lock(pid):
            p = proj(pid)
            try:
                q = p.add_piece(body.get("slot", ""), body.get("bars"))
            except ValueError as e:
                bad(e)
            return p.public() | {"added": q["id"]}

    @app.post("/api/projects/{pid}/pieces/{qid}")
    def edit_piece(pid: str, qid: str, body: dict = Body(...)):
        with _lock(pid):
            p = proj(pid)
            extra = {}
            try:
                if body.get("note_op"):
                    p.note_op(qid, int(body.get("index", -1)), str(body["note_op"]))
                    extra["note_index"] = getattr(p, "last_note_index", None)
                elif body.get("variation"):
                    p.variation(qid, body["variation"])
                elif body.get("take"):
                    p.choose_take(qid, body["take"])
                elif "pattern" in body:
                    p.set_pattern(qid, str(body["pattern"] or ""))
                else:
                    p.edit_piece(qid, **{k: body.get(k) for k in ("name", "instrument", "octave", "gain_db", "repeat")})
            except KeyError:
                raise HTTPException(404, "no such piece or take")
            except (ValueError, IndexError, TypeError) as e:
                bad(e)
            return p.public() | extra

    @app.delete("/api/projects/{pid}/pieces/{qid}")
    def remove_piece(pid: str, qid: str):
        with _lock(pid):
            p = proj(pid)
            try:
                p.remove_piece(qid)
            except KeyError:
                raise HTTPException(404)
            return p.public()

    @app.post("/api/projects/{pid}/pieces/{qid}/record")
    async def record(pid: str, qid: str, request: Request, start: float = 0.0, est_ms: float | None = None):
        """A booth recording (WAV). `start`: loop time in seconds of the first sample, before latency.
        `est_ms`: the browser's own estimate of the round trip, used until the sync test has been done."""
        from .server import _wav_from_body

        body = await request.body()
        try:
            y, sr = _wav_from_body(body)
        except Exception:
            raise HTTPException(400, "not a WAV file")
        lat = config.Settings.load().latency_ms(est_ms) / 1000.0
        with _lock(pid):
            p = proj(pid)
            try:
                cal = beatbox.Calibration(paths["calibration"])
                new = p.add_recording(qid, y, sr, start - lat, cal)
            except KeyError:
                raise HTTPException(404)
            except ValueError as e:
                bad(e)
            return p.public() | {"new_takes": [t["id"] for t in new]}

    @app.delete("/api/projects/{pid}/pieces/{qid}/takes/{tid}")
    def delete_take(pid: str, qid: str, tid: str):
        with _lock(pid):
            p = proj(pid)
            try:
                p.delete_take(qid, tid)
            except KeyError:
                raise HTTPException(404, "no such piece")
            return p.public()

    @app.get("/api/projects/{pid}/takes/{rid}")
    def take_audio(pid: str, rid: str):
        p = proj(pid)
        f = (p.dir / "takes" / f"{rid}.wav").resolve()
        if f.parent != (p.dir / "takes").resolve() or not f.exists():
            raise HTTPException(404)
        return FileResponse(f, media_type="audio/wav")

    @app.get("/api/favourites")
    def favourites():
        return list_favourites()

    @app.delete("/api/favourites/{fid}")
    def remove_favourite(fid: str):
        try:
            delete_favourite(fid)
        except KeyError:
            raise HTTPException(404)
        return {"ok": True}

    @app.post("/api/projects/{pid}/pieces/{qid}/favourite")
    def save_favourite(pid: str, qid: str, body: dict = Body(default={})):
        p = proj(pid)
        try:
            return p.favourite(qid, str(body.get("name", "")))
        except KeyError:
            raise HTTPException(404)
        except ValueError as e:
            bad(e)

    @app.post("/api/projects/{pid}/favourites/{fid}")
    def use_favourite(pid: str, fid: str):
        with _lock(pid):
            p = proj(pid)
            try:
                q = p.use_favourite(fid)
            except KeyError:
                raise HTTPException(404, "no such favourite")
            return p.public() | {"added": q["id"]}

    @app.post("/api/projects/{pid}/build")
    def build(pid: str):
        with _lock(pid):
            p = proj(pid)
            try:
                return p.build(lib)
            except ValueError as e:
                bad(e)
