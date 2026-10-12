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
