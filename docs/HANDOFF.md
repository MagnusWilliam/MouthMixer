# Handoff: from the cloud sessions to a local Claude Code session (2026-10-14)

Read this first, then `CLAUDE.md`, `docs/PLAN.md` (decisions box and §14 build status) and
`docs/MUSIC_KNOWLEDGE.md`. Everything below the line "The user's new requests" is the user's own list,
kept complete. The user is moving to a local session on their Windows PC because their web credit ran
out.

## What a local session can do that the cloud ones couldn't

- **Hear what the user hears, in numbers.** The user's real library lives in `%USERPROFILE%\MouthMixer`
  (songs, versions, stems, vocal takes, Make projects). The cloud sessions only ever had synthetic audio.
  Start by analysing the user's real takes and built song for "Last Train, First Light" (all its vocals
  are recorded): find out *why* their voice sounds muffled and why tuning makes it choppy, with measurements,
  before changing code.
- Run the app for real (`python -m mouthmixer app`, port 8765) and the GPU (RX 7900 XT: ONNX Runtime with
  DirectML; PyTorch on Windows+AMD has no CUDA, so prefer ONNX/DirectML or CPU).
- Reference audio: the user has these Persona tracks as FLAC (they sent them to the cloud session; they
  have the originals): *Burn My Dread*, *Signs of Love*, *It's Going Down Now*, *Color Your Night*. Ask the
  user where they are on the PC, or ask them to copy them to `reference_audio/` in the repo. **That folder is
  git-ignored: never commit copyrighted audio**, and keep analysis outputs about tendencies (numbers,
  patterns), never copied melodies or riffs (PLAN §8.3, §10).

## State of the app (what exists)

Everything is on `main` of `magnuswilliam/mouthmixer`, 141 tests passing. Highlights (details in PLAN §14):
- **Make** (main workflow): starter beats per mood, ready-made parts (`studio/presets.py`: 20 beats,
  13 basslines, 10 chord rhythms, 12 groove combos, 38 phrases), section feels, freeze-and-drop, song board,
  lyrics with `[Section, singers, N bars]` headers and `Gang:` line tags, songbook (19 songs: LINE ZERO songs 01-12, reference-inspired 13-19, superseded by the instrumentals in `studio/refsongs.py`, PERSONA_PRODUCTION §10),
  favourites, recording as a side option (audio-thread capture, sync test).
- **Sing**: vocal track cards, take choice per section, voice characters (WORLD vocoder), voice tweaks,
  preview with band, timing nudge, full lyrics view.
- **Mix**: parts on/off, sounds, volumes, band hits on vocal accents.
- Brass is "played" (scoops, vibrato, phrasing, doubling).

## Known problems (from the user's real use)

1. **Tuning makes the voice choppy** in the preview. Suspects: `vocals.tune_to_key` (WORLD resynthesis
   passage by passage, hard frame-level snapping, unvoiced/voiced boundaries), and running WORLD twice
   (tuning, then the character). Measure on the user's real takes first.
2. **Voice quality is muffled.** Suspects: noise reduction (`noisereduce` with prop_decrease 0.6),
   high-pass filters, de-esser, WORLD resynthesis losing the top end, OGG encoding. **Add a true "raw
   voice" option** (no tuning, no character, only level and placement) and make every processing step
   switchable and visible.
3. **The female voice sounds like "a guy trying to sound like a girl".** The current approach (WORLD
   octave shift plus formant warp) is the classic, limited one. Research and try modern voice conversion
   that runs locally (e.g. RVC-style models, so-vits-svc, Seed-VC, or OpenVoice-style approaches;
   check each one's licence and whether it runs on AMD via ONNX/DirectML). If nothing gets convincing,
   say so honestly and offer alternatives: re-key or rearrange the female parts for the user's own range,
   use a different arrangement (duet with the user's girlfriend? only if she agrees), or choir/stack textures.
4. **Adding vocal tracks creates a new song version for every track/section**, which is confusing. Redesign:
   one working version that collects vocal tracks, and an explicit "save as version" action.

## The user's new requests (complete)

1. Fix the choppy tuning, the muffled voice, and give more control over every option and tweak, including
   **just the raw voice**.
2. Find better ways to make the user's voice sound like a convincing girl. If it is truly impossible, give
   alternatives for the songs so they can sing them themselves. They are really hoping it can work.
3. **Research** (with sources): tips for singing better at different vibes and pitches; how music producers
   and software make the jump in quality (vocal production chains, mixing, mastering, arrangement).
4. **Make the app cleaner, better put together, more user-friendly and transparent** (example: the version
   spam from vocal tracks). Think hard about this across the whole app.
5. **Become an expert music analyst.** Take songs the user uploads, split them into individual instruments
   and vocals (stem separation), turn them into data you can read (MIDI/notes, beats, chords, section
   structure, levels per stem per section, timing feel, variation, tempo, arrangement density over time),
   and analyse them deeply to learn what makes them sound good, so we can make our own unique songs using
   their tendencies as a blueprint. Find software to link to, or a workaround. Candidates to evaluate (check
   licences; must run on Windows + AMD): Demucs / HTDemucs (stems), Basic Pitch (audio to MIDI),
   librosa / madmom-style beat and chord tracking, pyloudnorm for levels. Build this into a repeatable tool
   (e.g. `python -m mouthmixer analyse <file>`), write the findings into docs (e.g. `docs/REFERENCE_ANALYSIS.md`),
   and turn them into rules, presets and starters.
6. **Become a genius producer**: the main thing the user cares about is the actual song quality. Use YouTube
   examples of people making Persona-inspired music with their screens shown (instruments, chords, beats).
   You can't watch video; use transcripts, descriptions, and the spreadsheet below, and ask the user to
   describe or screenshot specific moments if needed.
   - https://youtu.be/4j0xpJulLVI
   - https://youtu.be/DQLHOrU-Yvw
   - https://youtu.be/ia1COXiyPXQ
   - https://youtu.be/5bXPMy69HPw
   - https://youtu.be/KM4NEyxvsII
   - Persona sound sources sheet: https://docs.google.com/spreadsheets/d/1J1b2aFEb-z7UKBWnIEUq_Q2369uNDdQRLCFvUzXboog/edit?gid=1798925961
7. Reference songs provided: *Burn My Dread*, *Signs of Love*, *It's Going Down Now*, *Color Your Night*
   (FLAC). The user will send more if asked: tell them which songs would help most.
8. "Last Train, First Light" is fully recorded but needs a lot of improvement before anyone hears it.
   The user's girlfriend is helping tweak and give advice; nothing goes out until it is good.

## Suggested order

1. Set up: the local clone, the venv, run the tests, run the app; find the user's library and the reference
   FLACs.
2. Measure the user's real recording problems (muffled, choppy) on their takes; fix them; add the raw
   voice option and per-step switches; fix version spam. Ask the user to listen.
3. Build the analysis tool (stems, notes, structure, levels) and analyse the four reference songs; write
   up findings; turn them into production rules.
4. Female voice research and trials; honest verdict with alternatives.
5. Production quality pass on "Last Train, First Light" using what was learned.

Keep the standing rules: free/permissive tools and samples only (licence notes), LINE ZERO untouched, add
a synthetic test for every behaviour change, log critic value changes in MUSIC_KNOWLEDGE §13, commit to
`main` with the attribution lines the session gives you, no PRs unless asked.
