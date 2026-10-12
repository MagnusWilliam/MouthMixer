# MouthMixer

Hum, whistle or beatbox while you work. MouthMixer listens in the background, keeps only the musical
moments, and turns them into clean notes and drum hits you can listen to and download as MIDI. Later
phases build finished, original game music around them in the style you ask for, with a critic that only
shows you the best options (see the plan).

**New:** every good clip now becomes a **finished song** before it reaches your inbox: a full arrangement
in one of six styles (city-pop day, neon night, acid-jazz battle, orchestral adventure, arcade, dream) with
many instruments, effects and a mastered mix. MouthMixer tries many versions and combinations of your clips,
checks each against the music rules in `docs/MUSIC_KNOWLEDGE.md`, and shows the best three. Raw clips live
in the **Clips** tab; pick your microphone in **Setup**.

**Status (prototype, 2026-10-12):** Phases 1-2 of [`docs/PLAN.md`](docs/PLAN.md) are built as a first
version: background capture, the music detector, hum and beatbox transcription, cleanup (tempo drift,
swing, key, scale), the inbox app and the Windows shortcut. It has only been tested on generated audio so
far (the build machine has no mic), so **your first real hums are the real test.**

## Set up (Windows)

1. Install Python 3.12 if you don't have it: `winget install Python.Python.3.12`
2. Download this repo (green **Code** button > Download ZIP, unzip it somewhere permanent) or clone it.
3. Double-click **`scripts\windows\setup.cmd`**. It installs everything into
   `%LOCALAPPDATA%\MouthMixer\venv` (outside OneDrive), makes the
   **MouthMixer** shortcut on your desktop and in the Start menu, and runs the self-checks.
   - Want listening to start when Windows starts? Run `scripts\windows\setup.cmd -StartWithWindows`.
4. Double-click **MouthMixer** on the desktop. The tray icon appears (bottom right) and the app opens in its
   own window.

## Using it

- **Just work.** Hum, whistle or beatbox when you feel like it. The tray icon is blue while listening and
  amber while it's catching something. Talking, typing and silence are dropped without being saved.
- **Missed one?** Press **Ctrl+Alt+M** right after: it saves the last 30 seconds, whatever the detector
  thought.
- **The inbox** (open from the shortcut or the tray icon): each clip has **What you did** and
  **Cleaned up** players and a note view (faint = as heard, solid = cleaned).
  - **Keep** / **Toss** / **Not music** (this one teaches the detector).
  - **Not what I hummed** tries the next reading: half tempo, double tempo, looser timing, the second most
    likely key, or no scale snapping.
  - MIDI downloads are there too (you don't need them; they're for later phases and other tools).
- **Setup tab:**
  - **Beatbox calibration:** do each sound ~10 times so it learns *your* kick, snare and hats.
  - **Mic test:** type, then hum; it tells you if the mic position keeps the keyboard far enough below
    your voice.
  - **Add a recording:** any WAV (a hum, or a whole workday; only the musical parts are kept).
- **Pause** any time from the tray or the app. It also pauses on its own while Discord, Zoom, Teams, Slack
  and similar apps use the mic, and during quiet hours you set.
- Your clips live in `%USERPROFILE%\MouthMixer` and never leave your PC.

**Settings** are in `%USERPROFILE%\MouthMixer\settings.json` (created on first run): the hotkey, the mic
name (default: the first device with "QuadCast" in its name), quiet hours (`"quiet_start": "22:00"`,
`"quiet_end": "08:00"`) and the apps that pause it.

## Phase 0: recordings that tune the detector

The detector's thresholds are starting guesses. Real recordings make them right:
1. Record a normal stretch of work with any recorder (Audacity is free) and save it as WAV.
2. Write down roughly when you hummed or beatboxed, as a CSV with one `start_seconds,end_seconds` line per
   moment.
3. Run `%LOCALAPPDATA%\MouthMixer\venv\Scripts\python -m mouthmixer scan yourfile.wav --labels yourfile.csv`. It
   prints how many moments it caught (goal: 85%) and how much junk it kept (goal: at most 20%).
4. Share the WAV clips you're comfortable sharing with the next build session (the musical bits plus a few
   minutes of typing and talking), and it gets tuned against them.

## For developers

```
python -m venv .venv && .venv/bin/pip install -e .[dev]     # Linux/macOS (no mic or tray needed)
python -m pytest                                          # 42 tests on generated audio
python -m mouthmixer demo && python -m mouthmixer app     # demo clips + the app at http://127.0.0.1:8765
python -m mouthmixer process hum.wav                      # one clip -> result.json, MIDI, preview.wav
```

| Doc | What it covers |
| --- | --- |
| [`docs/PLAN.md`](docs/PLAN.md) | The whole design, the decisions, the build phases |
| [`docs/MUSIC_KNOWLEDGE.md`](docs/MUSIC_KNOWLEDGE.md) | The critic's rulebook (used from Phase 4) |
| [`CLAUDE.md`](CLAUDE.md) | Rules for build sessions |

Code map: `listener/` (capture, segmenter, tray, hotkey, auto-pause), `analysis/` (music gate, pitch,
melody and beatbox transcription, tempo/swing/downbeat, key, cleanup, pipeline), `library/` (SQLite),
`app/` (local web app + clip worker), `synth.py` (generated test audio and the preview sound),
`launcher.py` (what the shortcut runs).
