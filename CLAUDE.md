# Working on MouthMixer

Read `docs/PLAN.md` (the design and the decisions box at its top) and `docs/MUSIC_KNOWLEDGE.md` (the
critic's rules) before building anything.

Constraints that hold for every session:
- **Target:** Windows desktop, Python. Browser UI opened in an app window from a desktop shortcut.
- **Hardware:** Ryzen 9 7900 + AMD Radeon RX 7900 XT. No CUDA: run models through ONNX Runtime
  (DirectML provider, CPU fallback).
- **Mic:** HyperX QuadCast 2 with a pop shield; the user usually wears headphones.
- **The cloud build sessions have no mic and no speakers.** Test with synthetic audio and the user's
  shared recordings; check numbers, and ask the user to listen at the end of each phase.
- **The user steers; no piano rolls.** Features work from suggestions (chips, briefs, A/B picks, ranked part
  suggestions) and simple controls. Allowed at the user's request: the Incredibox-style piece/part controls
  (on/off, sound swap, octave, volume, add/remove, simpler/busier) and one-note fixes in Make (up/down,
  earlier/later, longer/shorter, delete). No drawing notes from scratch.
- **The main workflow is Make**: pick a starter beat, mix and match **ready-made parts** (`studio/presets.py`)
  and tweak them; recording your own pieces is a side option. Background listening is off by default and
  optional.
- **Free instruments and CC0/permissive samples only**, each with a licence note.
- **LINE ZERO stays untouched** until the user approves the tool and its music.
- Change a critic rule's value only with a line in `docs/MUSIC_KNOWLEDGE.md` §13 (tuning log).
- Build in the phase order of `docs/PLAN.md` §14.

Working in this repo:
- Status and what's next: `docs/PLAN.md` §14 "Build status".
- Tests: `python -m pytest` (all on generated audio from `src/mouthmixer/synth.py`; add a synthetic case
  for every behaviour you change). Hardware code (`sounddevice`, `pystray`, `pynput`, `winreg`) is
  imported lazily so the tests run without it.
- Vocals and lyrics: `docs/VOCALS.md`; style research: `docs/PERSONA_STYLE.md`, `docs/ARRANGING.md`. Test singing
  with `synth.sing` (it knows the true onsets and pitch errors). The Claude lyric call is tested with a
  stand-in client; never spend the user's credits in tests.
- Try the app headless: `python -m mouthmixer demo` then `python -m mouthmixer app` (port 8765).
