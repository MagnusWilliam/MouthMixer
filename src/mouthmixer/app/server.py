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
        except Exception:
            log.exception("analysis failed for %s", clip_id)
            self.lib.set_status(clip_id, "failed")
        finally:
            self.busy -= 1


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
        return {"listener": st, "counts": counts, "processing": worker.busy, "hotkey": settings.hotkey}

    @app.post("/api/listener/{cmd}")
    def listener_cmd(cmd: str):
        if cmd not in ("pause", "resume", "save_last", "quit"):
            raise HTTPException(400, "unknown command")
        (paths["control"] / f"{cmd}-{time.time_ns()}.cmd").write_text("")
        return {"ok": True}

    @app.get("/api/clips")
    def clips(view: str = "inbox"):
        statuses = {"inbox": ["new", "processing", "failed"], "kept": ["kept"], "tossed": ["tossed", "not_music"]}
        return lib.list(statuses.get(view))

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

    @app.exception_handler(Exception)
    async def errors(request, exc):
        log.exception("request failed")
        return JSONResponse({"error": str(exc)}, status_code=500)

    return app


def main():
    import uvicorn

    p = config.ensure_dirs()
    logging.basicConfig(filename=str(p["logs"] / "app.log"), level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = config.Settings.load()
    uvicorn.run(create_app(), host="127.0.0.1", port=settings.port, log_level="warning")
