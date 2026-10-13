"""The Make tab's API: starter beats, projects, pieces, booth recordings, takes, the song board, build."""

from __future__ import annotations

import threading

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse

from .. import config
from ..analysis import beatbox
from ..studio import starters
from ..studio.project import Project, list_projects

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

    @app.get("/api/projects")
    def projects():
        return list_projects()

    @app.post("/api/projects")
    def create(body: dict = Body(...)):
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
            if "title" in body:
                p.data["title"] = str(body["title"])[:60] or p.data["title"]
                p.save()
            if "tonic" in body:
                p.set_key(int(body["tonic"]))
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
                if not q["notes"] and not q.get("gen") and not q.get("audio"):
                    continue
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
            try:
                if body.get("note_op"):
                    p.note_op(qid, int(body.get("index", -1)), body["note_op"])
                elif body.get("variation"):
                    p.variation(qid, body["variation"])
                elif body.get("take"):
                    p.choose_take(qid, body["take"])
                else:
                    p.edit_piece(qid, **{k: body.get(k) for k in ("name", "instrument", "octave", "gain_db", "repeat")})
            except KeyError:
                raise HTTPException(404, "no such piece or take")
            except (ValueError, IndexError) as e:
                bad(e)
            return p.public()

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
    async def record(pid: str, qid: str, request: Request, start: float = 0.0):
        """A booth recording (WAV). `start`: loop time in seconds of the first sample, before latency."""
        from .server import _wav_from_body

        body = await request.body()
        try:
            y, sr = _wav_from_body(body)
        except Exception:
            raise HTTPException(400, "not a WAV file")
        lat = config.Settings.load().vocal_latency_ms / 1000.0
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
            p.delete_take(qid, tid)
            return p.public()

    @app.get("/api/projects/{pid}/takes/{rid}")
    def take_audio(pid: str, rid: str):
        p = proj(pid)
        f = (p.dir / "takes" / f"{rid}.wav").resolve()
        if f.parent != (p.dir / "takes").resolve() or not f.exists():
            raise HTTPException(404)
        return FileResponse(f, media_type="audio/wav")

    @app.post("/api/projects/{pid}/build")
    def build(pid: str):
        with _lock(pid):
            p = proj(pid)
            try:
                return p.build(lib)
            except ValueError as e:
                bad(e)
