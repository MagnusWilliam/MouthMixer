"""The local app: a small web server for the browser window, plus the worker that processes new clips
from the listener (PLAN.md §6, §13). Only listens on 127.0.0.1."""

from __future__ import annotations

import io
import json
import logging
import shutil
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from .. import config
from ..analysis import beatbox, detect, pipeline
from ..arrange import critic, songwriter
from ..library.db import Library

log = logging.getLogger("mouthmixer.app")
STATIC = Path(__file__).parent / "static"
READING_LABELS = [
    "best guess",
    "half tempo",
    "double tempo",
    "looser timing",
    "second key",
    "no scale snapping",
]


class Worker:
    """Moves complete clips from incoming/ into the library and analyses them."""

    def __init__(self, lib: Library, paths: dict):
        self.lib = lib
        self.paths = paths
        self.cal = beatbox.Calibration(paths["calibration"])
        self._stop = False
        self.busy = 0
        self.writing = 0  # songs being made right now
        self.song_lock = threading.Lock()
        self.make_songs = True
        self.song_options: dict = {}  # passed to songwriter.write_songs (tests use fewer candidates)

    def start(self):
        threading.Thread(target=self._loop, daemon=True, name="ingest").start()

    def stop(self):
        self._stop = True

    def _loop(self):
        while not self._stop:
            try:
                self.ingest_once()
            except Exception:
                log.exception("ingest failed")
            time.sleep(1.5)

    def ingest_once(self) -> int:
        n = 0
        for wav in sorted(self.paths["incoming"].glob("*.wav")):
            meta_p = wav.with_suffix(".json")
            meta = json.loads(meta_p.read_text()) if meta_p.exists() else {"source": "upload", "created": time.time()}
            clip_id = wav.stem
            d = self.lib.clip_dir(clip_id)
            d.mkdir(parents=True, exist_ok=True)
            shutil.move(str(wav), str(d / "audio.wav"))
            if meta_p.exists():
                shutil.move(str(meta_p), str(d / "meta.json"))
            else:
                (d / "meta.json").write_text(json.dumps(meta))
            gate = (meta.get("verdict") or {}).get("scores", {})
            self.lib.add(clip_id, meta.get("source", "upload"), gate, meta.get("created"))
            self.analyse(clip_id, meta)
            n += 1
        return n

    def analyse(self, clip_id: str, meta: dict | None = None, reading_index: int = 0):
        d = self.lib.clip_dir(clip_id)
        meta = meta or json.loads((d / "meta.json").read_text())
        v = meta.get("verdict")
        verdict = detect.Verdict(v["is_music"], v["kind"], v.get("scores", {})) if v else None
        self.busy += 1
        try:
            self.cal = beatbox.Calibration(self.paths["calibration"])
            result = pipeline.process_file(d / "audio.wav", d, reading=pipeline.READINGS[reading_index],
                                           calibration=self.cal, verdict=verdict)
            self.lib.set_result(clip_id, result, reading_index)
            q = critic.clip_quality(result)
            self.lib.set_quality(clip_id, q)
            if q["ok"] and self.make_songs and reading_index == 0:
                self.write_song(clip_id)
        except Exception:
            log.exception("analysis failed for %s", clip_id)
            self.lib.set_status(clip_id, "failed")
        finally:
            self.busy -= 1


    # --- songs -------------------------------------------------------------------------------------
    def _clip_info(self, row: dict) -> songwriter.ClipInfo | None:
        rp = self.lib.clip_dir(row["id"]) / "result.json"
        if not rp.exists():
            return None
        return songwriter.ClipInfo(row["id"], json.loads(rp.read_text()), row["created"])

    def write_song(self, clip_id: str, *, song_id: str | None = None, exclude_pack: str | None = None) -> str | None:
        """Make (or add versions to) a song from a clip plus the rest of the usable library."""
        with self.song_lock:
            self.writing += 1
            try:
                primary = self._clip_info(self.lib.get(clip_id))
                if primary is None:
                    return None
                others = [c for c in (self._clip_info(r) for r in self.lib.usable_clips()) if c and c.id != clip_id]
                if song_id is None:
                    song_id = f"{clip_id}-song"
                    out = self.lib.song_dir(song_id)
                    recent = [r["style"] for r in self.lib.list_songs(["new", "kept", "tossed"])[:6]]
                    recent = [k for k, v in songwriter.PACKS.items() for t in recent if v["title"] == t]
                    rec = songwriter.write_songs(primary, others, out, recent=recent, **self.song_options)
                    if rec is None:
                        log.info("no song passed the critic for %s", clip_id)
                        return None
                    self.lib.add_song(song_id, rec)
                    return song_id
                from ..arrange.mixer import next_version_index, write_json
                from .studio import _lock

                out = self.lib.song_dir(song_id)
                with _lock(song_id):  # reserve the file name, so a mix saved meanwhile can't take it
                    start = next_version_index(out, json.loads((out / "song.json").read_text()))
                    (out / f"v{start}.ogg").touch()
                opts = {**self.song_options, "keep": 1}
                try:
                    rec = songwriter.write_songs(primary, others, out, exclude_pack=exclude_pack, start_index=start, **opts)
                except Exception:
                    rec = None
                    raise
                finally:
                    if rec is None:
                        (out / f"v{start}.ogg").unlink(missing_ok=True)
                if rec is None:
                    return None
                with _lock(song_id):  # merge into the record as it is now (the studio may have added versions)
                    record = json.loads((out / "song.json").read_text())
                    record["versions"] += rec["versions"]
                    record["history"] = record.get("history", []) + [rec["summary"]]
                    write_json(out / "song.json", record)
                self.lib.update_song(song_id, record, len(record["versions"]) - 1)
                return song_id
            finally:
                self.writing -= 1


def _wav_from_body(body: bytes) -> tuple[np.ndarray, int]:
    y, sr = sf.read(io.BytesIO(body), dtype="float32", always_2d=True)
    return y.mean(axis=1), sr


def create_app(start_worker: bool = True) -> FastAPI:
    paths = config.ensure_dirs()
    settings = config.Settings.load()
    lib = Library(paths["db"], paths["clips"])
    worker = Worker(lib, paths)
    @asynccontextmanager
    async def lifespan(_app):
        if start_worker:
            worker.start()
        yield
        worker.stop()

    app = FastAPI(title="MouthMixer", lifespan=lifespan)
    app.state.lib, app.state.worker, app.state.paths = lib, worker, paths

    @app.get("/")
    def index():
        return FileResponse(STATIC / "index.html")

    @app.get("/static/{name}")
    def static(name: str):
        p = (STATIC / name).resolve()
        if p.parent != STATIC.resolve() or not p.exists():
            raise HTTPException(404)
        return FileResponse(p)

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    @app.get("/api/status")
    def status():
        st = {"state": "not running"}
        if paths["status"].exists():
            try:
                st = json.loads(paths["status"].read_text())
                if time.time() - st.get("updated", 0) > 5:
                    st = {"state": "not running"}
            except (OSError, ValueError):
                pass
        counts = {}
        for row in lib.conn.execute("SELECT status, COUNT(*) c FROM clips GROUP BY status"):
            counts[row["status"]] = row["c"]
        songs = {}
        for row in lib.conn.execute("SELECT status, COUNT(*) c FROM songs GROUP BY status"):
            songs[row["status"]] = row["c"]
        return {"listener": st, "counts": counts, "songs": songs, "processing": worker.busy,
                "writing": worker.writing, "hotkey": settings.hotkey}

    @app.post("/api/listener/{cmd}")
    def listener_cmd(cmd: str):
        if cmd not in ("pause", "resume", "save_last", "quit", "reload_mic"):
            raise HTTPException(400, "unknown command")
        (paths["control"] / f"{cmd}-{time.time_ns()}.cmd").write_text("")
        return {"ok": True}

    @app.get("/api/clips")
    def clips(view: str = "all"):
        statuses = {"inbox": ["new", "processing", "failed"], "kept": ["kept"], "tossed": ["tossed", "not_music"],
                    "all": None}
        return lib.list(statuses.get(view))

    # --- songs ---------------------------------------------------------------------------------------
    @app.get("/api/songs")
    def songs(view: str = "inbox"):
        statuses = {"inbox": ["new"], "kept": ["kept"], "tossed": ["tossed"]}.get(view, ["new"])
        return lib.list_songs(statuses)

    @app.get("/api/songs/{song_id}")
    def song(song_id: str):
        row = lib.get_song(song_id)
        if not row:
            raise HTTPException(404)
        row["record"] = json.loads((lib.song_dir(song_id) / "song.json").read_text())
        return row

    @app.get("/api/songs/{song_id}/file/{name}")
    def song_file(song_id: str, name: str):
        p = (lib.song_dir(song_id) / name).resolve()
        if p.parent != lib.song_dir(song_id).resolve() or not p.exists() or p.suffix not in (".ogg", ".mid"):
            raise HTTPException(404)
        media = "audio/ogg" if p.suffix == ".ogg" else "audio/midi"
        return FileResponse(p, media_type=media, filename=f"{song_id}-{name}")

    @app.post("/api/songs/{song_id}/status")
    def song_status(song_id: str, body: dict = Body(...)):
        st = body.get("status")
        if st not in ("kept", "tossed", "new") or not lib.get_song(song_id):
            raise HTTPException(400)
        lib.set_song_status(song_id, st)
        return {"ok": True}

    @app.post("/api/songs/{song_id}/version")
    def song_version(song_id: str, body: dict = Body(...)):
        row = lib.get_song(song_id)
        if not row:
            raise HTTPException(404)
        record = json.loads((lib.song_dir(song_id) / "song.json").read_text())
        v = int(body.get("version", 0))
        if not 0 <= v < len(record["versions"]):
            raise HTTPException(400)
        lib.update_song(song_id, record, v)
        return {"ok": True}

    @app.post("/api/songs/{song_id}/another")
    def song_another(song_id: str, body: dict = Body(default={})):
        """A new version, the same style mix or a different style (runs in the background)."""
        row = lib.get_song(song_id)
        if not row:
            raise HTTPException(404)
        record = json.loads((lib.song_dir(song_id) / "song.json").read_text())
        current = record["versions"][row["version"]]
        exclude = current["pack"] if body.get("different_style") else None
        primary = record["primary"]
        threading.Thread(target=worker.write_song, args=(primary,),
                         kwargs={"song_id": song_id, "exclude_pack": exclude}, daemon=True).start()
        return {"ok": True}

    @app.post("/api/clips/{clip_id}/song")
    def clip_song(clip_id: str):
        """Make a song from this clip now (also for clips the quality check wasn't sure about)."""
        if not lib.get(clip_id):
            raise HTTPException(404)
        threading.Thread(target=worker.write_song, args=(clip_id,), daemon=True).start()
        return {"ok": True}

    # --- microphone ----------------------------------------------------------------------------------
    @app.get("/api/mics")
    def mics():
        try:
            import sounddevice as sd

            devs, apis = sd.query_devices(), sd.query_hostapis()
        except Exception as e:  # no audio system (e.g. tests)
            return {"devices": [], "current": settings.mic_name, "error": str(e)}
        seen, out = set(), []
        prefer = "MME" if any(a["name"] == "MME" for a in apis) else None
        for d in devs:
            api = apis[d["hostapi"]]["name"]
            if d["max_input_channels"] <= 0 or (prefer and api != prefer) or d["name"] in seen:
                continue
            seen.add(d["name"])
            out.append({"name": d["name"]})
        cur = config.Settings.load().mic_name
        return {"devices": out, "current": cur}

    @app.post("/api/mic")
    def set_mic(body: dict = Body(...)):
        s = config.Settings.load()
        s.mic_name = str(body.get("name", ""))
        s.save()
        settings.mic_name = s.mic_name
        (paths["control"] / f"reload_mic-{time.time_ns()}.cmd").write_text("")
        return {"ok": True, "mic": s.mic_name}

    @app.get("/api/clips/{clip_id}")
    def clip(clip_id: str):
        row = lib.get(clip_id)
        if not row:
            raise HTTPException(404)
        rp = lib.clip_dir(clip_id) / "result.json"
        row["result"] = json.loads(rp.read_text()) if rp.exists() else None
        row["reading_label"] = READING_LABELS[row.get("reading") or 0]
        return row

    @app.get("/api/clips/{clip_id}/audio/{which}")
    def audio(clip_id: str, which: str):
        name = {"raw": "audio.wav", "preview": "preview.wav"}.get(which)
        p = lib.clip_dir(clip_id) / (name or "")
        if not name or not p.exists():
            raise HTTPException(404)
        return FileResponse(p, media_type="audio/wav")

    @app.get("/api/clips/{clip_id}/midi/{which}")
    def midi(clip_id: str, which: str):
        if which not in ("clean", "raw"):
            raise HTTPException(404)
        p = lib.clip_dir(clip_id) / f"{which}.mid"
        if not p.exists():
            raise HTTPException(404)
        return FileResponse(p, media_type="audio/midi", filename=f"{clip_id}-{which}.mid")

    @app.post("/api/clips/{clip_id}/status")
    def set_status(clip_id: str, body: dict = Body(...)):
        st = body.get("status")
        if st not in ("kept", "tossed", "not_music", "new"):
            raise HTTPException(400)
        if not lib.get(clip_id):
            raise HTTPException(404)
        lib.set_status(clip_id, st)
        return {"ok": True}

    @app.post("/api/clips/{clip_id}/reading")
    def next_reading(clip_id: str):
        """"Not what I hummed": analyse again with the next alternative reading."""
        row = lib.get(clip_id)
        if not row:
            raise HTTPException(404)
        nxt = ((row.get("reading") or 0) + 1) % len(pipeline.READINGS)
        lib.log(clip_id, "reading", nxt)
        worker.analyse(clip_id, reading_index=nxt)
        return {"reading": nxt, "label": READING_LABELS[nxt]}

    @app.post("/api/upload")
    async def upload(request: Request, name: str = "upload"):
        """Add any recording (a WAV body). Long recordings are scanned and only the musical parts kept."""
        body = await request.body()
        try:
            y, sr = _wav_from_body(body)
        except Exception:
            raise HTTPException(400, "send a WAV file")
        import librosa

        y16 = librosa.resample(y, orig_sr=sr, target_sr=16000) if sr != 16000 else y
        found = detect.scan(y16, 16000) if len(y) / sr > 200 else [
            {"start": 0.0, "end": len(y) / sr, **detect.judge(y16, 16000).to_dict()}]
        kept = 0
        for i, seg in enumerate(found):
            if not seg["is_music"] and len(found) > 1:
                continue
            stamp = time.strftime("%Y%m%d-%H%M%S") + f"-up{i:03d}"
            part = y[int(seg["start"] * sr) : int(seg["end"] * sr)]
            sf.write(str(paths["incoming"] / f"{stamp}.part"), part, sr, subtype="PCM_16", format="WAV")
            (paths["incoming"] / f"{stamp}.json").write_text(json.dumps({
                "source": "upload", "created": time.time(), "name": name,
                "verdict": {k: seg[k] for k in ("is_music", "kind", "scores")}}))
            (paths["incoming"] / f"{stamp}.part").replace(paths["incoming"] / f"{stamp}.wav")
            kept += 1
        return {"segments": len(found), "kept": kept}

    @app.get("/api/calibration")
    def calibration():
        cal = beatbox.Calibration(paths["calibration"])
        counts: dict[str, int] = {}
        for label, _ in cal.examples:
            counts[label] = counts.get(label, 0) + 1
        return {"counts": counts, "ready": cal.ready}

    @app.post("/api/calibration/{label}")
    async def add_calibration(label: str, request: Request):
        if label not in beatbox.GM:
            raise HTTPException(400, "unknown sound")
        y, sr = _wav_from_body(await request.body())
        cal = beatbox.Calibration(paths["calibration"])
        n = beatbox.calibrate_from_take(y, sr, label, cal)
        cal.save()
        return {"added": n}

    @app.delete("/api/calibration")
    def reset_calibration():
        paths["calibration"].unlink(missing_ok=True)
        return {"ok": True}

    from . import make, studio

    studio.add_routes(app, lib, settings)
    make.add_routes(app, lib, paths)

    @app.exception_handler(Exception)
    async def errors(request, exc):
        log.exception("request failed")
        return JSONResponse({"error": str(exc)}, status_code=500)

    return app


def main():
    import uvicorn

    from ..runtime import setup

    log = setup("app")
    settings = config.Settings.load()
    try:
        # log_config=None: uvicorn's own console logging breaks without a console (pythonw).
        uvicorn.run(create_app(), host="127.0.0.1", port=settings.port, log_config=None, log_level="warning")
    except Exception:
        log.exception("the app stopped")
        raise
