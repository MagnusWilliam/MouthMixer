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
- **The user steers, never edits.** Every feature must work from suggestions (chips, briefs, A/B picks,
  "this bit" markers), not piano rolls or mixer controls.
- **Free instruments and CC0/permissive samples only**, each with a licence note.
- **LINE ZERO stays untouched** until the user approves the tool and its music.
- Change a critic rule's value only with a line in `docs/MUSIC_KNOWLEDGE.md` §13 (tuning log).
- Build in the phase order of `docs/PLAN.md` §14.
