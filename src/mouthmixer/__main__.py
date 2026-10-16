"""Command line: `python -m mouthmixer [command]`.

  launch            (default) start everything and open the app window: what the shortcut runs
  listen            the background listener (tray icon, hotkey); --no-tray for a console run
  app               the local web app and clip worker
  stop              ask the listener to quit
  process FILE      analyse one clip into a folder (result.json, MIDI, preview.wav)
  scan FILE         find the musical moments in a long recording (Phase 0); --labels CSV scores it
  demo              put a few generated test clips into the library so the app has something to show
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path


def _scan(path: Path, labels: Path | None) -> int:
    import librosa

    from .analysis import detect, pipeline

    y, sr = pipeline.load(path)
    y16 = librosa.resample(y, orig_sr=sr, target_sr=16000) if sr != 16000 else y
    found = detect.scan(y16, 16000)
    music = [f for f in found if f["is_music"]]
    for f in found:
        mark = "MUSIC" if f["is_music"] else "  -  "
        print(f"{mark} {f['start']:8.1f}-{f['end']:8.1f}s  {f['kind']:6s}  melody={f['scores'].get('melody')}"
              f" beat={f['scores'].get('beat')}")
    if labels:
        # CSV rows: start_seconds,end_seconds[,kind] for every moment you marked as musical.
        truth = []
        with open(labels, newline="") as fh:
            for row in csv.reader(fh):
                if row and row[0].strip() and not row[0].startswith("#"):
                    try:
                        truth.append((float(row[0]), float(row[1])))
                    except ValueError:
                        continue
        caught = sum(1 for a, b in truth if any(f["start"] < b and f["end"] > a for f in music))
        junk = sum(1 for f in music if not any(f["start"] < b and f["end"] > a for a, b in truth))
        print()
        print(f"caught {caught} of {len(truth)} marked moments ({100 * caught / max(1, len(truth)):.0f}%, goal 85%)")
        print(f"junk: {junk} of {len(music)} kept clips ({100 * junk / max(1, len(music)):.0f}%, goal at most 20%)")
    return 0


def _demo() -> int:
    import soundfile as sf

    from . import config, synth
    from .analysis import detect

    p = config.ensure_dirs()
    clips = [
        ("demo-hum", synth.hum(synth.melody("ode"), bpm=92, drift=0.05, global_offset_cents=-30, seed=4)[0]),
        ("demo-minor", synth.hum(synth.melody("minor"), bpm=104, seed=5)[0]),
        ("demo-beat", synth.beatbox(bars=4, seed=6)[0]),
    ]
    for name, y in clips:
        stamp = time.strftime("%Y%m%d-%H%M%S") + "-" + name
        v = detect.judge(y, synth.SR)
        sf.write(str(p["incoming"] / f"{stamp}.part"), y, synth.SR, subtype="PCM_16", format="WAV")
        (p["incoming"] / f"{stamp}.json").write_text(json.dumps(
            {"source": "demo", "created": time.time(), "verdict": v.to_dict()}))
        (p["incoming"] / f"{stamp}.part").replace(p["incoming"] / f"{stamp}.wav")
        print("added", stamp, v.kind)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="mouthmixer")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("launch")
    sub.add_parser("stop", help="quit a running MouthMixer (setup does this before updating)")
    lp = sub.add_parser("listen")
    lp.add_argument("--no-tray", action="store_true")
    sub.add_parser("app")
    pp = sub.add_parser("process")
    pp.add_argument("file", type=Path)
    pp.add_argument("--out", type=Path)
    sp = sub.add_parser("scan")
    sp.add_argument("file", type=Path)
    sp.add_argument("--labels", type=Path)
    sub.add_parser("demo")
    rp = sub.add_parser("analyse", help="analyse reference songs (docs/REFERENCE_ANALYSIS.md)")
    rp.add_argument("target", type=Path, help="an audio file, or a folder of them")
    rp.add_argument("--stems", action="store_true", help="split into stems first (needs Demucs)")
    rp.add_argument("--out", type=Path, help="default: <library>/analysis")
    pp = sub.add_parser("profile", help="instrument profiles from six stems (reference/profile.py)")
    pp.add_argument("mix", type=Path, help="the reference audio file")
    pp.add_argument("song_dir", type=Path, help="its analysis folder (with stems6/)")
    a = ap.parse_args(argv)

    if a.cmd in (None, "launch"):
        from .launcher import launch

        launch()
    elif a.cmd == "stop":
        from . import config
        from .launcher import stop_old

        stop_old(config.Settings.load().port, force=True)
    elif a.cmd == "listen":
        from .listener.service import main as listen

        listen(tray=not a.no_tray)
    elif a.cmd == "app":
        from .app.server import main as app

        app()
    elif a.cmd == "process":
        from .analysis import pipeline

        out = a.out or a.file.with_suffix("")
        r = pipeline.process_file(a.file, out)
        print(f"{r['kind']}: {r['tempo']['bpm']} BPM, {(r['key'] or {}).get('name')}, "
              f"{len(r['notes'])} notes, {len(r['drums'])} drum hits -> {out}")
    elif a.cmd == "scan":
        return _scan(a.file, a.labels)
    elif a.cmd == "demo":
        return _demo()
    elif a.cmd == "analyse":
        from . import config
        from .reference import analyse

        analyse.run(a.target, a.out or config.home() / "analysis", with_stems=a.stems)
    elif a.cmd == "profile":
        from .reference import profile

        profile.profile(a.song_dir, a.mix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
