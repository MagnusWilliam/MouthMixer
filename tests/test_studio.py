"""The studio screens' API: mixer, lyrics, takes and vocals on a real (generated) song."""

import io

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from mouthmixer import synth as S
from mouthmixer.__main__ import main as cli


def _wav(y, sr):
    b = io.BytesIO()
    sf.write(b, y, sr, format="WAV", subtype="FLOAT")
    return b.getvalue()


def test_studio_flow(home):
    from mouthmixer.app.server import create_app

    assert cli(["demo"]) == 0
    app = create_app(start_worker=False)
    app.state.worker.song_options = {"n": 4, "render_top": 1, "keep": 1}
    client = TestClient(app)
    app.state.worker.ingest_once()
    song = next(s for s in client.get("/api/songs").json())
    sid = song["id"]

    # --- mixer: parts with stems, mute, swap, suggestions, add, remove, save -----------------------
    st = client.get(f"/api/songs/{sid}/mixer").json()
    parts = st["parts"]
    assert {"lead", "drums", "bass"} <= {p["role"] for p in parts}
    assert client.get(f"/api/songs/{sid}/stems/{parts[0]['stem']}").status_code == 200
    assert client.get(f"/api/songs/{sid}/stems/..%2Fsong.json").status_code == 404
    comp = next(p for p in parts if p["role"] == "comp")
    st = client.post(f"/api/songs/{sid}/mixer/part", json={"id": comp["id"], "muted": True}).json()
    assert next(p for p in st["parts"] if p["id"] == comp["id"])["muted"]
    other = next(c for c in comp["choices"] if c != comp["instrument"])
    st = client.post(f"/api/songs/{sid}/mixer/part", json={"id": comp["id"], "instrument": other, "muted": False}).json()
    swapped = next(p for p in st["parts"] if p["id"] == comp["id"])
    assert swapped["instrument"] == other and swapped["stem"] != comp["stem"]
    sug = client.get(f"/api/songs/{sid}/mixer/suggest?vibe=dreamy").json()
    assert sug["vibes"] and sug["suggestions"] and all(s["why"] for s in sug["suggestions"])
    st = client.post(f"/api/songs/{sid}/mixer/add", json={"kind": sug["suggestions"][0]["id"]}).json()
    added = st["added"]
    assert any(p["id"] == added for p in st["parts"])
    lead = next(p for p in st["parts"] if p["mine"])
    assert client.post(f"/api/songs/{sid}/mixer/remove", json={"id": lead["id"]}).status_code == 400
    st = client.post(f"/api/songs/{sid}/mixer/remove", json={"id": added}).json()
    assert all(p["id"] != added for p in st["parts"])
    saved = client.post(f"/api/songs/{sid}/mixer/save", json={}).json()
    assert saved["critic"]["ok"], saved["critic"]["rejects"]
    v = saved["version"]
    assert client.get(f"/api/songs/{sid}").json()["version"] == v

    # --- settings and lyrics ---------------------------------------------------------------------------
    s = client.post("/api/settings", json={"vocal_latency_ms": 35}).json()
    assert s["vocal_latency_ms"] == 35
    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        assert client.post(f"/api/songs/{sid}/lyrics/write", json={"brief": "x"}).status_code == 400
    lyr = client.get(f"/api/songs/{sid}/lyrics").json()
    assert lyr["map"]
    texts = {sec["section"]: "\n".join("la " * ln["count"] for ln in sec["lines"]) for sec in lyr["map"]}
    lyr = client.post(f"/api/songs/{sid}/lyrics/own", json={"title": "la", "sections": texts}).json()
    assert lyr["chosen"] == 0 and lyr["events"] and lyr["options"][0]["check"]["score"] > 0.8

    # --- singing: a take over the first verse, then vocals mixed in ---------------------------------
    rec = client.get(f"/api/songs/{sid}").json()["record"]
    ver = rec["versions"][v]
    bpm = ver["bpm"]
    sec = next(x for x in ver["sections"] if x["name"] == "A")
    a, b = sec["start"] * 4, (sec["start"] + sec["bars"]) * 4
    notes = [(n[0], n[1], n[2]) for t in ver["tracks"] if t["role"] == "lead" for n in t["notes"] if a <= n[0] < b]
    start = (sec["start"] - 1) * 4 * 60 / bpm  # one bar of count-in
    x, _ = S.sing(notes, bpm, start=start + 4 * 60 / bpm, pre_roll=4 * 60 / bpm, seed=3)
    x = np.concatenate([np.zeros(int(0.035 * 48000), np.float32),
                        __import__("librosa").resample(x, orig_sr=44100, target_sr=48000)])
    take = client.post(f"/api/songs/{sid}/takes?start={start}&section=A", content=_wav(x, 48000)).json()
    assert take["score"]["score"] > 0.6 and take["latency_ms"] == 35, take["score"]
    assert client.get(f"/api/songs/{sid}/takes").json()["takes"][0]["id"] == take["id"]
    assert client.post(f"/api/songs/{sid}/vocals", json={"preset": "nope"}).status_code == 400
    out = client.post(f"/api/songs/{sid}/vocals", json={"lead_mode": "duck"}).json()
    assert out["critic"]["ok"], out["critic"]["rejects"]
    assert out["vocals"]["quality"]["checks"]
    st = client.get(f"/api/songs/{sid}/mixer?v={out['version']}").json()
    voc = next(p for p in st["parts"] if p["role"] == "vocal")
    assert voc["mine"] and voc["choices"] == []
    assert client.get(f"/api/songs/{sid}/stems/{voc['stem']}").status_code == 200
    new = client.get(f"/api/songs/{sid}").json()["record"]["versions"][out["version"]]
    assert new["lyrics"]["chosen"] == 0  # the words travel with the version
    # Vocal tracks collect in one working version instead of a new version each time.
    assert new["working"] and "working version" in new["title"]
    count = len(client.get(f"/api/songs/{sid}").json()["record"]["versions"])
    raw = client.post(f"/api/songs/{sid}/vocals", json={"v": out["version"], "tweaks": {"process": "raw"}}).json()
    assert raw["version"] == out["version"] and raw["vocals"]["raw"]
    assert len(client.get(f"/api/songs/{sid}").json()["record"]["versions"]) == count
    kept = client.post(f"/api/songs/{sid}/keep_version", json={"v": out["version"], "name": "first vocals"}).json()
    assert kept["title"].endswith("· first vocals")
    assert "working" not in client.get(f"/api/songs/{sid}").json()["record"]["versions"][out["version"]]
    assert client.post(f"/api/songs/{sid}/keep_version", json={"v": out["version"]}).status_code == 400
    nxt = client.post(f"/api/songs/{sid}/vocals", json={"v": out["version"]}).json()  # a new working version
    assert nxt["version"] == count
    # Muting the vocals and saving gives a version without them.
    client.post(f"/api/songs/{sid}/mixer/part", json={"v": out["version"], "id": "vocal", "muted": True})
    again = client.post(f"/api/songs/{sid}/mixer/save", json={"v": out["version"]}).json()
    assert "vocal_stem" not in client.get(f"/api/songs/{sid}").json()["record"]["versions"][again["version"]]
    assert client.delete(f"/api/songs/{sid}/takes/{take['id']}").json()["ok"]
