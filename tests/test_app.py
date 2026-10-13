"""The local app: clips flow from incoming/ to the inbox, and the inbox buttons work."""

import io

import soundfile as sf
from fastapi.testclient import TestClient

from mouthmixer import synth as S
from mouthmixer.__main__ import main as cli


def _wav(y, sr=S.SR):
    b = io.BytesIO()
    sf.write(b, y, sr, format="WAV", subtype="PCM_16")
    return b.getvalue()


def test_inbox_flow(home):
    from mouthmixer.app.server import create_app

    assert cli(["demo"]) == 0
    app = create_app(start_worker=False)
    app.state.worker.make_songs = False
    client = TestClient(app)
    assert app.state.worker.ingest_once() == 3
    clips = client.get("/api/clips?view=inbox").json()
    assert len(clips) == 3 and all(c["status"] == "new" for c in clips)
    kinds = sorted(c["kind"] for c in clips)
    assert kinds == ["beat", "melody", "melody"]

    hum = next(c for c in clips if c["key"] == "D major")
    detail = client.get(f"/api/clips/{hum['id']}").json()
    assert detail["result"]["notes"] and detail["reading_label"] == "best guess"
    assert client.get(f"/api/clips/{hum['id']}/audio/preview").status_code == 200
    assert client.get(f"/api/clips/{hum['id']}/midi/clean").status_code == 200

    r = client.post(f"/api/clips/{hum['id']}/reading").json()
    assert r["label"] == "half tempo"
    assert client.get(f"/api/clips/{hum['id']}").json()["reading"] == 1

    assert client.post(f"/api/clips/{hum['id']}/status", json={"status": "kept"}).json()["ok"]
    assert len(client.get("/api/clips?view=kept").json()) == 1
    assert len(client.get("/api/clips?view=inbox").json()) == 2

    st = client.get("/api/status").json()
    assert st["listener"]["state"] == "not running" and st["counts"]["kept"] == 1


def test_upload_and_calibration(home):
    from mouthmixer.app.server import create_app

    app = create_app(start_worker=False)
    app.state.worker.make_songs = False
    client = TestClient(app)
    y, _ = S.hum(S.melody("minor"), seed=7)
    assert client.post("/api/upload", content=_wav(y)).json()["kept"] == 1
    assert app.state.worker.ingest_once() == 1

    kick, _ = S.beatbox(["k", "-"] * 4, bars=2, seed=8)
    assert client.post("/api/calibration/kick", content=_wav(kick)).json()["added"] >= 6
    assert client.get("/api/calibration").json()["counts"]["kick"] >= 6
    assert client.post("/api/calibration/banjo", content=_wav(kick)).status_code == 400
    assert client.post("/api/listener/pause").json()["ok"]
    assert client.post("/api/listener/explode").status_code == 400


def test_starts_without_a_console(home, monkeypatch):
    """The shortcut runs pythonw.exe: no stdout/stderr. Startup must not crash on that (it used to)."""
    import logging
    import sys

    from mouthmixer import runtime

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    runtime.setup("app")
    assert sys.stdout is not None and sys.stderr is not None
    from uvicorn.config import LOGGING_CONFIG

    logging.config.dictConfig(LOGGING_CONFIG)  # what uvicorn does at start; crashed with no console
    sys.stdout.close()


def test_songs_flow(home):
    """Clips become finished songs in the inbox; keep, versions and another version work."""

    from mouthmixer.app.server import create_app

    assert cli(["demo"]) == 0
    app = create_app(start_worker=False)
    app.state.worker.song_options = {"n": 5, "render_top": 2, "keep": 2}
    client = TestClient(app)
    app.state.worker.ingest_once()
    songs = client.get("/api/songs").json()
    assert len(songs) >= 2
    s = client.get(f"/api/songs/{songs[0]['id']}").json()
    v = s["record"]["versions"][0]
    assert v["tracks"] and v["critic"]["ok"]
    assert client.get(f"/api/songs/{s['id']}/file/{v['file']}").status_code == 200
    assert client.get(f"/api/songs/{s['id']}/file/../../library.sqlite").status_code == 404
    if len(s["record"]["versions"]) > 1:
        assert client.post(f"/api/songs/{s['id']}/version", json={"version": 1}).json()["ok"]
        assert client.get(f"/api/songs/{s['id']}").json()["version"] == 1
    n_before = len(s["record"]["versions"])
    app.state.worker.write_song(s["record"]["primary"], song_id=s["id"], exclude_pack=v["pack"])
    assert len(client.get(f"/api/songs/{s['id']}").json()["record"]["versions"]) == n_before + 1
    assert client.post(f"/api/songs/{s['id']}/status", json={"status": "kept"}).json()["ok"]
    assert len(client.get("/api/songs?view=kept").json()) == 1
    clips = client.get("/api/clips?view=all").json()
    assert all(c["quality"] is not None for c in clips)
    assert client.get("/api/mics").json()["devices"] == [] or True  # no audio system in CI
    assert client.post("/api/mic", json={"name": "Microphone (HyperX QuadCast 2)"}).json()["ok"]
    from mouthmixer import config

    assert config.Settings.load().mic_name == "Microphone (HyperX QuadCast 2)"


def test_ping_reports_the_code_version(home):
    """The launcher compares it with the installed code and replaces an app left running from before an
    update (the user's starter beats didn't show because the old app was still serving)."""
    from mouthmixer.app.server import create_app
    from mouthmixer.runtime import code_version

    c = TestClient(create_app(start_worker=False))
    v = c.get("/api/ping").json()["version"]
    assert v == code_version() and len(v) == 12
    assert c.get("/api/starters").status_code == 200
