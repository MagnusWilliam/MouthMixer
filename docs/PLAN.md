# MouthMixer: the plan (hums and beatbox into game music)

> **Status 2026-10-13:** prototype built through parts of Phase 6; see §14 "Build status".
> MouthMixer is a standalone desktop tool (Windows first) that can feed any game project. Its first
> customer is **LINE ZERO** (repo `magnuswilliam/line-0`). Where this plan says `AUDIO_PLAN`,
> `MusicDirector`, `MusicCues.luau`, `sound_ids.csv` or motifs H / S / L0 / T / B, it means
> LINE ZERO's `docs/design/AUDIO_PLAN.md` and the AT67 decisions in its `docs/TODO.md`.
> The critic's rulebook is [`MUSIC_KNOWLEDGE.md`](MUSIC_KNOWLEDGE.md).

**What it does, in one paragraph.** It runs quietly in the background and listens to the mic. It keeps
only the moments where you hum, whistle, sing or beatbox, and drops everything else without saving it.
It turns those clips into clean notes and drum hits (MIDI), fixes the timing and pitch, and files them in
a library by key, tempo and feel. It then pairs clips with each other and with a **style pack** (for
example "city-pop day" or "acid-jazz battle") to make full arrangements, warns you when a melody is too
close to a known song, and exports loop-ready audio plus MIDI for the game.

**Ground rule:** the tool suggests and you choose. You give creative direction only: you never edit
notes, chords or mixes yourself. It never ships anything on its own. The music stays
yours because it is built from your melodies with rule-based arranging and instruments you own. There is
no black-box AI song generator in the main path.

**DECIDED 2026-10-12 (user answers):**
- **Own repository** for the tool, so other projects can use it: **`magnuswilliam/mouthmixer`** (this repo).
- **Mic:** HyperX QuadCast 2 (USB condenser), with a pop shield available. **Headphones** are worn most of
  the time.
- **App:** a local page in the browser, opened from a **desktop / Start-menu shortcut** (see §13).
- **LINE ZERO stays untouched until the tool is proven.** Nothing is wired into the game, uploaded to
  Roblox or added to `MusicCues.luau` until you approve it. Exports are plain files until then.
- **PC:** AMD Ryzen 9 7900 (12 cores) and an **AMD Radeon RX 7900 XT**. There's no NVIDIA card, so
  nothing may depend on CUDA (see §13).
- **Free instruments only.**
- **You only steer, you don't edit** (§7.10). So the tool must catch its own mistakes: **the critic**
  (§7.11) filters out weak ideas and bad mixes before you ever hear them, using the rulebook in
  [`MUSIC_KNOWLEDGE.md`](MUSIC_KNOWLEDGE.md).
- **MIDI downloads are OK** for the originality check's reference set and danger list.
- **Loud keyboard:** move the mic onto a **boom arm**, back of the mic toward the keyboard (§2 mic setup).
- **First style packs confirmed:** city-pop day, neon night, acid-jazz battle.
- **Lyrics and real vocals:** the tool suggests lyrics that fit a finished song; you sing them; it cleans
  up and mixes the vocal (§7.13, Phase 6).
- **Lyrics model: the Claude API** (decided 2026-10-12). Used only in Phase 6, opt-in, text only.
- **Prototype started 2026-10-12** (Phases 1-2, first version), built against synthetic audio; see
  §14 "Build status".
- **Songs don't have to come only from your voice.** The tool may write its own parts and add sounds
  when something is missing (§7.12). Your ideas stay the centre; additions support them.
- **Incredibox-style mixer (decided 2026-10-12, later).** On songs you like you can turn parts on and off,
  swap a part's sound, change its volume, and add or remove parts from ranked suggestions ("what sound are
  you going for?", sorted by pairing/synergy and by vibe, each with a reason). This relaxes "steer, don't
  edit" for *parts*, not notes: there is still no piano roll and no mixer console, and every saved mix
  goes through the critic. Research: [`ARRANGING.md`](ARRANGING.md), [`PERSONA_STYLE.md`](PERSONA_STYLE.md).
- **You mostly hum the lead melody**; drums, bass and accents come as default loops and generated parts.
- **New main workflow: Make (decided 2026-10-13).** You record on purpose instead of being listened to in the
  background. Pick a **starter beat** (5 moods: battle, daily life, night, dungeon, boss; Persona genre
  traits, no copied songs), then record **pieces** in a booth over the loop: loops that repeat (beat,
  bassline, riff, accent stabs, vocal chop, extra percussion) and one-off parts (hook, verse melody,
  bridge, answer line, intro motif, drum fill). Each pass round the loop is a take. Pieces work like
  Incredibox characters (on/off, swap sound, octave, volume, simpler/busier) and you may **nudge single
  notes** (up/down, earlier/later, longer/shorter, delete): this relaxes "never edit notes" at the user's
  request. A **song board** places pieces in sections; **Build** makes a song that the Mix, Lyrics and
  Sing tabs then work on. Vocal chops stay your voice (tuned, cut on the beat).
- **Ready-made parts first, recording on the side (decided 2026-10-13, night).** After trying Make, the user
  found hummed pieces didn't sound right and asked for preset beat combos to mix and match and then tweak.
  Make now leads with **ready-made parts**: beat, bassline and chord grooves (they keep each section's feel),
  riffs, stabs, answer lines, intro motifs, hooks, percussion and fills (they follow the chords), and named
  **groove combos**. Every part has a pattern dropdown, simpler/busier, sound, octave and one-note fixes.
  Recording your own is a fold-out ("Record your own (optional)").
- **Background listening is off by default** (a switch in Setup); the hotkey only works when it's on.
- **Vocals and lyrics in the app now** (ahead of Phase 6's order, at the user's request): a Lyrics screen
  and a Sing screen (karaoke, pitch lane, takes), with the processing system in [`VOCALS.md`](VOCALS.md).

---

## Contents

1. How the whole thing flows
2. Stage A: background listening
3. Stage B: "is this music?"
4. Stage C: turning sound into notes
5. Stage D: cleanup with music rules
6. Stage E: the library and "idea threads"
7. Stage F: the pairing engine (how songs get made)
8. Style packs, starting with the Persona-inspired family
9. Worked example: one hum, six LINE ZERO cues
10. Stage G: the originality check
11. Stage H: rendering and export to Roblox
12. Problems and risks, with solutions
13. Architecture and tech choices
14. Build phases, with "done when" tests
15. Open questions for you

---

## 1. How the whole thing flows

```
 mic ──► [A] listen (cheap, always on, RAM only)
          │  sound detected
          ▼
        [B] "is this music, and is it me?"  ── no ──► discarded, never written to disk
          │ yes
          ▼
        [C] transcribe: hum → melody notes, beatbox → drum hits, singing → notes + kept audio
          ▼
        [D] clean up: tempo, grid, key, scale, note tidy (original kept alongside)
          ▼
        [E] library: tags, "idea threads" (repeated ideas grouped), daily review inbox
          ▼
        [F] pairing engine: clips + style pack → several candidate arrangements
          ▼
        [G] originality check on every melody, bass line and full arrangement
          ▼
        [H] render (instruments, mix, loops) → export WAV/OGG + MIDI + cue data → Roblox / DAW
```

Stages A and B run all the time in the background. Stages C and D run on each kept clip, right away or
when the PC is idle. Stages E to H run when you open the app.

---

## 2. Stage A: background listening

**Goal:** never miss an idea, use almost no CPU, and never store anything private.

- **Capture:** read the mic at 16 kHz mono for detection. Also keep a 44.1/48 kHz copy in memory so kept
  clips are full quality.
- **Ring buffer:** the last **30 seconds** stay in RAM only. When a musical moment is detected, the clip
  starts up to 5 s *before* the trigger, because ideas often start quietly.
- **Voice activity detector:** Silero VAD (small, about 1% of one CPU core) answers one question: is there
  a voice-like sound at all? Silence and steady noise never reach the heavier stages.
- **End of a clip:** the clip closes after about 2.5 s with no musical sound. Clips shorter than about
  1.5 s are dropped. Clips are capped at 3 minutes, then continue as a new linked clip.
- **Manual "save that!" hotkey** (like a game's instant-replay button): saves the last 30 s whatever the
  classifier thought. This is the safety net for anything the detector missed, and every use of it is a
  training example ("the detector should have caught this").
- **Tray icon states:** grey = paused, blue = listening, pulsing amber = capturing. One click pauses.
  It also auto-pauses on schedules you set and while a call app is using the mic (see §12).

**Mic setup (HyperX QuadCast 2):**
- It's a USB condenser mic, so it's very sensitive: it hears the keyboard and desk thumps too. The
  beatbox-vs-typing rules (§3 B2) handle what gets through, but less noise in = better notes out.
- **Your keyboard is loud, so use a boom arm** (decided):
  - The arm takes the mic off the desk, so typing thumps no longer travel up the stand. Keep the shock
    mount on the arm.
  - The QuadCast 2 is a **side-address** mic: you talk into the side with the logo. It hears least from
    directly behind. Point the **back of the mic toward the keyboard** and the front toward your mouth.
    If your model has a pattern setting, use cardioid.
  - **Distance matters most.** Noise drops about 6 dB every time its distance doubles. Aim for the mic
    about 15-25 cm from your mouth while you work (close enough for quiet hums, not in your face) and as
    far from the keyboard as the arm allows. Then turn the gain down until loud hums don't clip; lower
    gain also means less keyboard.
  - Setup runs a short test: type for 10 s, hum for 10 s, and it shows how far apart they are.
- Its **tap-to-mute** on top doubles as a hardware privacy switch: muted means the tool hears nothing.
  The tray icon shows "mic muted" so you know it isn't listening.
- **Pop shield:** good for hums and singing. But beatbox kicks and snares *are* plosives ("b", "p"),
  and the shield softens them. So the beatbox calibration (§4 C2) is done with the shield in the same
  position you'll normally use, and redone if you move it.
- **Headphones** mean the speaker-playback problem mostly goes away. The loopback check stays on
  because it's cheap and covers the times you take them off.
- Capture at 48 kHz. The mic's gain knob should be set once in setup with a level meter (loud hums
  and beatbox shouldn't clip).

---

## 3. Stage B: "is this music?"

Three checks, cheapest first. A clip needs to pass all three.

**B1. Sound type (pretrained classifier).** Run YAMNet or PANNs, which are trained on Google AudioSet and
already know the labels *Humming*, *Whistling*, *Singing*, *Beatboxing*, *Speech*, *Music*, *Typing*,
*Laughter*, *Cough* and more. Each second of audio gets a score per label. We keep a moving average
and look for "musical voice" (hum + whistle + sing + beatbox) beating "speech" for at least about 2 s.

**B2. Musical features (hand-written rules, cheap and explainable).**

| Feature | Hum or sing | Talking | Beatbox | Typing or tapping |
|---|---|---|---|---|
| Pitch held steady per note (pYIN voiced frames, low jitter) | high | low (pitch glides) | n/a | n/a |
| Pitches land near a scale (12-tone histogram is "peaky") | yes | no | n/a | n/a |
| Repeating rhythm (autocorrelation of onsets) | some | little | strong | strong but flat |
| Spectrum of hits (kick-like low burst, snare-like noise, hat-like hiss) | n/a | n/a | varied | all the same "click" |

A clip scores points per feature. Typing has a strong rhythm but no pitch and all hits sound alike, so it
fails. Beatbox has rhythm plus varied hit types, so it passes.

**B3. Is it you, and is it live?**
- **Your voice:** a one-minute enrolment ("hum, talk and beatbox for a minute") gives a speaker embedding
  (Resemblyzer or ECAPA from SpeechBrain). Clips that don't match you are dropped, so other people and the
  TV don't get kept.
- **Not your speakers:** on Windows, WASAPI loopback lets the app hear what the PC itself is playing. If
  the mic signal correlates strongly with the loopback signal (the same music, delayed by a few ms), it's
  playback, not you, so it's dropped. With headphones this problem barely exists.

**Learning from you.** The daily inbox (§6) has keep / toss buttons. After a week or two, those answers
train a tiny personal classifier (logistic regression on the YAMNet embedding plus the B2 features).
It slowly replaces the hand-set thresholds, so the tool gets better at knowing what *you* count as an idea.

**Start strict.** In the first version the thresholds are set so that false keeps are rare. The hotkey
covers misses. Loosen the thresholds once the inbox data shows what's being missed.

---

## 4. Stage C: turning sound into notes

Every clip is split into **segments** by type, because one clip can hold a beatbox loop and then a hum on
top of it.

**C1. Hums, whistles, sung melodies → melody notes.**
1. **Clean the audio first:** noise suppression (DeepFilterNet or RNNoise) removes fans and room noise,
   which otherwise create fake notes.
2. **Track the pitch:** run two trackers and combine them: Spotify's *Basic Pitch* (fast, gives notes
   directly) and *CREPE* or *pYIN* (very accurate frame-by-frame pitch). Where they disagree, trust the
   one with higher confidence on that frame.
3. **Cut the pitch curve into notes:** a new note starts when the pitch jumps by more than about 0.6
   semitones and stays there for more than 60 ms, or when loudness dips then rises again (a re-articulated
   "hm-hm" on the same pitch). This "hysteresis" stops wobble from turning into lots of tiny notes.
4. **Keep the expression:** each note stores its pitch-bend curve, loudness curve (→ velocity) and vibrato.
   These come back in Stage H so the result doesn't sound robotic.

**C2. Beatbox → drum hits.**
1. **Find the hits:** onset detection (librosa spectral flux) finds the start of every sound.
2. **Classify each hit:** a short window around each onset becomes features (MFCCs plus the YAMNet
   embedding) and a small classifier sorts it into *kick*, *snare*, *closed hat*, *open hat*, *clap*,
   *rim*, *tom* or *other*.
3. **Calibration (the key trick):** a 3-minute setup asks you to do each of your sounds 10 times. Your
   "b", "pf", "ts", "k" are different from everyone else's, so a classifier trained on *your* examples
   (k-nearest-neighbours is enough) is far more accurate than a generic one. Every correction you make
   later adds another example.
4. **Map to drums:** each class becomes a General MIDI drum note. Loudness becomes velocity, which keeps
   accents and ghost notes.

**C3. Singing with words.** Treated as a melody (C1) *and* the cleaned audio is kept, because you may want
the vocal itself as a hook or a chopped "vocal sample". No lyrics transcription is needed in version 1.

**C4. Low hums.** A hum below about E3 that repeats a short pattern is tagged as a probable **bass line**
rather than a melody. This matters for pairing (§7).

---

## 5. Stage D: cleanup with music rules

Everything here is non-destructive: the raw transcription is kept, and every step has a strength slider.

**D1. Tempo, with drift handled.** People speed up and slow down while humming. A beat tracker (madmom or
librosa) estimates a **tempo curve**, not one number. The clip is then *warped* onto a steady grid (like
Ableton's warp markers) before quantising. Simple quantising of a drifting take puts notes in the wrong
bar; warping first fixes the drift and then the grid fixes the small errors.
- Tempo octave errors (is it 80 or 160?) are resolved by the beatbox if one is present, otherwise by
  asking: the inbox shows "80 or 160?" with both versions playable.

**D2. Meter and downbeat.** 4/4 is assumed; 3/4 and 6/8 are detected from accent patterns. The downbeat
(where "1" is) uses the strongest accents and the melody's longest notes.

**D3. Quantise, with feel kept.**
- Snap strength defaults to about 70% (notes move most of the way, not all the way).
- **Swing is detected and kept:** if your off-beat 8ths consistently land late, the grid becomes a swing
  grid (for example 60%) instead of straightening them.
- **Groove templates:** a style pack can pull timing toward its own feel (a laid-back neo-soul pocket,
  a tight funk pocket).

**D4. Key and scale.**
- Key detection: a note-duration histogram is compared against key profiles (Krumhansl-Schmuckler,
  plus Temperley profiles which do better on short melodies). The result is a ranked list
  ("C major 71%, A minor 22%"), not one answer.
- **Scale snapping is probabilistic, not blind.** A note 40 cents sharp of D, in C major, becomes D. But a
  note that is clearly F# held for a full beat stays F# (it's probably a deliberate chromatic note) and is
  marked so you can confirm it. Modes (Dorian, Mixolydian) are detected too, because they matter a lot in
  jazzy styles.

**D5. Note tidying.**
- Merge stutters (two near-identical notes split by a breath).
- Delete grace-note blips under about 50 ms unless they're on the beat.
- Snap note lengths to musical values (no 0.93-beat notes).
- Fix octave jumps from the pitch tracker (a single note an octave off its neighbours).

**D6. Phrase detection.** Breaths and long notes mark phrase ends. Phrases get labelled with their bar
length (2, 4, 8 bars), which the arranger uses to build sections.

---

## 6. Stage E: the library and "idea threads"

**Each clip stores:**
- the raw audio, the cleaned audio, the raw and cleaned MIDI;
- type (melody / bass / beat / vocal), key and mode, tempo, meter, length in bars;
- **contour** (the up/down shape of the melody), range (lowest to highest note), rhythm density
  (notes per beat), syncopation score, energy;
- a "mood" estimate from those (major/minor, fast/slow, busy/sparse, high/low);
- date, time and what you were doing if you tag it ("while coding", "at the bus stop");
- originality status (§10);
- your rating and notes.

**Idea threads.** You will hum the same idea many times over days. The tool compares melodies in a way
that ignores key and tempo (it compares the *intervals* between notes and the *relative* rhythm) and
groups close matches into a thread. A thread shows:
- every take, with the "best take" chosen by highest pitch accuracy and most complete phrase;
- a **merged version**: where takes agree, keep that; where they differ, list the variants
  ("bar 3 has two endings").

Threads are how short 3-second fragments grow into full 8-bar melodies over a week.

**The daily inbox.** A list of what was captured today. Each item shows a waveform, a piano roll and a
play button, with keep / toss / "not music" buttons. A good day's inbox should take 2 to 5 minutes.

**Search.** By tags, by "hum to search your own library" (find that thing you hummed last Tuesday), and by
"what fits with this?" (§7).

---

## 7. Stage F: the pairing engine (how songs get made)

This is the core. It answers two questions: **which of my clips go together**, and **how do I dress them
in a style**.

### 7.1 Roles

Every arrangement has slots for these roles:

| Role | Job | Typical source |
|---|---|---|
| **Groove** | drums | a beatbox clip, or the style's own drum patterns |
| **Bass** | root movement, the pulse under the harmony | a low hum (C4), or generated from the chords |
| **Harmony** | chords | generated (harmonisation, §7.3) |
| **Lead** | the main melody | a hum or whistle |
| **Counter-line** | an answering melody in the gaps | a second hum, or derived from the lead |
| **Hook / riff** | a short repeating figure | a short repeated hum, or a vocal chop |
| **Texture** | pads, ambience, train sounds | style pack |

A song needs at least a lead *or* a groove. Everything else can be generated.

### 7.2 Compatibility scoring (which clips fit together)

For any two clips the engine scores how well they would pair:

| Factor | How it's scored |
|---|---|
| **Key** | MIDI can be transposed freely, so the real question is "how far would I move it, and does it stay in a sensible range for its role?" Small moves score high. Same key, relative major/minor and fifth-neighbours score highest. |
| **Tempo** | Same tempo, or exactly half/double, scores high. Up to ±8% can be stretched without sounding strange. Beyond that, the score drops fast. |
| **Meter** | Same meter. A 4/4 melody can be converted to 3/4 (see §7.6), at a small penalty. |
| **Rhythmic fit** | A busy melody over a busy beat clashes. A melody whose gaps line up with the beat's fills makes call and response. Computed by comparing onset density per beat position. |
| **Register** | Lead above bass, with at least about an octave between their average pitches. |
| **Mood** | Similar energy and brightness, unless you ask for contrast. |
| **Phrase length** | 4-bar with 4-bar, or 2-bar loops under 8-bar phrases. |

The library's "what fits with this?" button lists the top matches with the reasons ("same key, tempo
within 3%, its gaps fill your melody's long notes").

### 7.3 Harmonisation (chords under a melody)

This is where the styles really show. It works bar by bar (or half-bar for faster harmony), like this:

1. **Candidates.** For each bar, list chords from the style's chord vocabulary in the key. A city-pop pack
   offers maj7, m7, 7, m9 and sus chords plus borrowed chords; a rock pack offers triads and power chords.
2. **Melody fit.** Score each candidate against the melody notes in that bar, weighted by beat strength:
   a chord tone on the downbeat scores high; a tension the style allows (9th, 11th, 13th in jazz styles)
   scores medium; a note that clashes (for example a natural 4th held over a major chord) scores low.
3. **Progression fit.** Each style has a table of how likely each chord is to follow another (ii→V→I,
   IV→V→iii→vi, tritone substitutions, backdoor iv→bVII→I...). These tables are **written by hand from
   general music theory for the genre**, not learned from specific songs.
4. **Voice leading.** Prefer chords whose notes move smoothly from the last chord.
5. **Search.** A beam search (or Viterbi) finds the best path through all the bars. Then it finds the
   best *few different* paths (forcing variety), so you get several harmonisations to choose from.
6. **Cadences.** Phrase ends from D6 get proper endings: a full cadence at the end of a section, a half
   cadence (ending on V) in the middle, and for game loops a "turnaround" that leads back to the top.

### 7.4 Bass, drums and parts

- **Bass from chords:** each style has **bass cells**, short rhythmic patterns with slots like "root",
  "fifth", "octave", "approach note into the next chord". Filling the slots from the chosen chords gives a
  bass line in the style. If you hummed a bass line, it is used instead and the chords are checked against
  it.
- **Drums from beatbox:** your kick/snare/hat pattern is kept as the skeleton. The style pack then adds
  its touches: ghost notes on the snare for funk, a swung hat for neo-soul, a crash on section starts, a
  fill on the last beat of every 4th or 8th bar. Without a beatbox clip, the style's own patterns are used.
- **Chord parts:** each style has **voicing and rhythm rules** per instrument. Rhodes plays rootless jazz
  voicings on the off-beats; a city-pop guitar plays cutting 16ths; strings hold pads.
- **Counter-lines:** made from the lead by taking its long notes and filling them with an answer in the
  rhythm gaps, using chord tones.

### 7.5 Arrangement and form for games

Game music mostly loops, so forms are built for looping:

| Form | Use | Shape |
|---|---|---|
| **Loop A-B** | field, city, dungeon | intro (4 bars, plays once) → A (8) → B (8) → A' (8) → B' (8) → back to A |
| **Battle** | battles | intro (2-4 bars) → riff (8) → A (16) → B (8) → riff → back; plus a "pinch" version |
| **Sting** | victory, level-up, rare drop | 2-6 s, one phrase, ends on a held chord |
| **Through-composed** | cutscenes | follows a list of beats and lengths you give it |

**Variation tricks on repeats** so the loop doesn't get boring: change the instrument on the melody,
drop the drums for 2 bars, move the melody up an octave, reharmonise the second time through.

**Intensity layers:** every arrangement can be rendered at 3 levels (calm → full → pinch), which match
the MusicDirector's `intensity` parameter.

### 7.6 Motif transformations (the leitmotif toolkit)

LINE ZERO's audio plan is built on motifs that are changed across the game. These transformations are
built in, and each one is one click:

| Transform | What it does | LINE ZERO use |
|---|---|---|
| Transpose / change mode | major ↔ minor ↔ Dorian | `city_night` (S in minor) |
| **Inversion** | flip every interval (up becomes down) | **T, the Timetable = the Hum inverted** |
| **Rigid quantise** | 100% grid, no swing, no expression | T's mechanical feel |
| Augmentation / diminution | notes twice as long / half as long | slow reveal versions; battle riffs |
| Retrograde | play it backwards | the dark element tail, the "wrong" Stop 4 |
| Fragment | keep only the first or a chosen part | stings, H fragments in the Ward |
| **Drop notes** | remove a chosen % of notes, lowest-weight first | the "forgetting" motif with missing notes |
| Meter change | 4/4 → 3/4 (stretch or remove the 4th beat of each bar, then re-phrase) | the `lost_car` waltz |
| Re-rhythm | put the same notes into a style's rhythm cell | turning H into a battle riff |

### 7.7 How variety is produced (so it isn't the same song every time)

The same clip set + the same style pack can produce many results, because the engine makes several
choices at each step and you can lock what you like:

- harmonisation: top 3 different chord paths;
- bass cells, drum overlays, voicings: chosen at random among the style's options (with a seed, so
  every result can be reproduced exactly);
- form and variation tricks;
- a "**surprise**" slider: low = safe choices from the style; high = borrowed chords, modulations,
  unusual instruments.

**Lock and reroll:** you lock the parts you like ("keep these chords and this bass") and reroll the rest.
That loop (generate → lock → reroll) is the main way you work with the tool, always through the
suggestion controls in §7.10, never by editing.

**It learns your taste:** your ratings shift each style's internal weights. If you always reroll away
from tritone substitutions, they appear less often.

### 7.8 Choosing the instruments

Each style pack lists, per role, a **first choice and alternatives** (for example lead: muted trumpet /
flute / clean guitar / Rhodes). An instrument is only picked if it passes these checks:

- **Range:** the part must fit the instrument's playable range (a trumpet can't play below about E3).
  If it doesn't fit, try moving the part an octave; if it still doesn't fit, try the next instrument.
- **Idiom (can a player actually do this?):** wind instruments need breaths (no 32 bars without a rest),
  fast wide leaps suit piano and synths but not trumpet or cello, guitars have chord shapes. A part that
  breaks its instrument's idiom sounds fake even when the notes are right.
- **Contrast:** lead and chords must not be the same sound family in the same octave, or the melody gets
  lost (Rhodes melody over Rhodes chords = mud). Each role gets its own register and colour.
- **Licence:** every instrument in the library has a licence note (§11.1). Instruments without a
  game-use licence can't be picked for a final render.

The arranger shows *why* it picked each instrument, and "swap instrument" is one of the reroll options.

### 7.9 Pairing beats and melodies: the production rules

Getting the key and tempo right is not enough. These rules make a beat and a melody actually sound
like one song:

- **Line up the "1".** A melody often starts before the bar line (a pickup note). The downbeat
  found in §D2 is matched to the beat's downbeat, not the first note.
- **Kick and bass lock together.** Bass notes start on or near kick hits; where they can't, the bass
  leaves room (sidechain, §11.3). This is the single biggest thing that makes a groove sound
  professional.
- **Snare backbeat stays clear.** Melody accents that fight the snare on 2 and 4 are moved off or
  softened.
- **Busy vs calm.** When the melody is busy, the drums simplify (fewer hats, no fills); when the melody
  holds a long note, the drums or a counter-line fill. This is "call and response".
- **Fills point forward.** Drum fills go in the last beat of a phrase, never under the melody's
  important notes.
- **No clashing notes.** A check flags a minor 2nd (or minor 9th) between melody and chord voicing on a
  strong beat and revoices the chord.

**A "music lint" runs on every arrangement** and lists problems it finds: clashes, parts out of range,
kick and bass fighting, melody buried, loop click. Like a code linter, but for music.

### 7.10 How you steer it (suggestions only, no editing)

You never touch a piano roll or a mixer. Everything you do is a creative suggestion:

- **A brief (optional, before generating):** "something sad for a rainy rooftop", "battle theme with my
  Tuesday hum and today's beat". The brief picks the style pack, the mood target (calm ↔ intense,
  sad ↔ happy) and which clips to use. If you give no brief, the tool proposes one from the clip.
- **Three finished options at a time**, already through the critic (§7.11). Each one shows a one-line
  explanation ("D major, 96 BPM, city-pop day, your melody on muted trumpet").
- **Reactions:** love / OK / no, plus **direction chips** that each map to concrete changes:

  | Chip | What changes |
  |---|---|
  | darker / brighter | mode (major → Dorian → minor), chord colours, instrument brightness, EQ tilt |
  | more / less energy | tempo ±, drum density, bass rhythm, intensity layer |
  | busier / simpler | number of parts, note density, fills, voicing size |
  | more groove | swing, ghost notes, syncopated bass, laid-back timing |
  | jazzier / plainer | 7th/9th/13th chords, tritone subs, passing chords ↔ triads |
  | melody buried | lead louder and brighter, chords thinned and carved around it |
  | wrong instrument | reroll the lead (or the part you point at) from the pack's alternatives |
  | too repetitive | more variation on repeats, a new B section |
  | too Persona / more our own | pushes away from the pack's "signature moves", raises the surprise slider |
  | not what I hummed | offers the next-best reading of your melody (rhythm or notes) |

- **"This bit" markers:** while it plays, tap *love this part* or *this part is off*. The tool keeps the
  loved parts locked and regenerates only around the bad moment.
- **A/B picks:** sometimes it asks "which of these two?" Pairwise picks are the most reliable way to
  learn taste, and they train the critic (§7.11).
- **Free-text suggestions:** a text box ("make the bass walk more in the B section"). Version 1 maps
  keywords to the chips above. Later, optionally, a Claude API call could turn free text into parameter
  changes (opt-in; it sends only your text, never audio).

Every result keeps its full recipe (clips, pack, seed, all choices), so any version can be rebuilt or
reverted.

### 7.11 The critic: weeding out bad ideas before you hear them

The engine makes **many candidates** (about 20 to 40 per request: it's fast, since it's mostly MIDI until
the final render) and the critic decides which **3** you see. The full rulebook is
[`MUSIC_KNOWLEDGE.md`](MUSIC_KNOWLEDGE.md). In short:

1. **Hard rejects** (any one fails the candidate): notes clashing on strong beats, parts outside their
   instrument's range or idiom, kick and bass fighting, a buried melody, clipping, a click at the loop
   point, a red originality result, a mix that disappears on a phone speaker.
2. **Scores** on the written rules, each 0-1 and weighted per style:
   - *melody:* shape and climax, steps vs leaps, a recognisable motif with variation, phrase endings;
   - *harmony:* chord-melody fit, progression flow, cadences, voice leading;
   - *rhythm:* groove fit for the style, kick-bass lock, syncopation in the style's range;
   - *form:* contrast between sections, energy curve, smooth loop;
   - *arrangement:* clear foreground, register spacing, no more than about 3 things competing;
   - *mix:* balance, frequency masking between parts, tonal balance against the style's target,
     loudness, dynamics, mono and phone translation;
   - *game fit:* loop length, listening fatigue, room for dialogue and sound effects.
3. **Listening models on the rendered audio:** a style-match score from a text-audio model (LAION CLAP:
   how well it matches "acid jazz battle music"), and a production-quality score from an audio aesthetics
   model (Meta's Audiobox Aesthetics **[verify licence]**). These only *rank*; they can't override a
   hard reject.
4. **Your taste:** a small model trained on your love / no reactions and A/B picks. It starts with a weight
   of zero and grows as your feedback builds up.
5. **Variety:** the 3 shown must differ meaningfully (different chord paths, instruments or feel), not
   be three versions of the same thing.

**It shows its work.** Under the 3 options: "made 30, rejected 19 (11 clashes, 5 buried melody,
3 too close to a known song), showing the best 3 of the rest". If everything fails, it says why and
asks a question instead of showing something weak.

**Honest limit:** these checks reliably catch *bad*; they can't guarantee *great*. That's what your
reactions are for, and why the taste model grows over time.

### 7.12 The tool's own additions (when something is missing)

A song needs more than one hum and one beat, so the tool may compose and add material itself. The rule:
**your idea stays the centre, additions support it.**

**What it may add:**
- **New musical parts:** chords, bass, counter-melodies, intros and outros, a **B section or bridge** when
  you only hummed an A section, transitions, drum parts and fills when there's no beatbox clip.
- **Sound design:** risers and sweeps into new sections, impacts and reverse cymbals, ambient beds
  (rain, city, room tone), and **railway sounds as rhythm** (AUDIO_PLAN §3.1: wheels on joints, the
  split-flap, the ticket punch). Sources: free CC0 sample packs (Freesound CC0, Sonniss GDC bundles
  **[verify each year's licence]**, Kenney) and sounds synthesised by the tool. Each sample has a licence
  note, like the instruments.
- **Production touches:** vinyl crackle, tape wobble, filter sweeps, vocal-like synth chops.

**How new melodies are written:** first by **developing your own motifs** (§7.6: sequence a bar up a
step, invert the answer phrase, augment it for the bridge), so new material sounds related to yours.
Only when that isn't enough does it write fresh material from the style's melodic rules. Every added
melody goes through the originality check (§10) and the critic (§7.11) like everything else.

**You stay in control of the balance:**
- each option shows what's yours and what was added ("your melody and beat; added: chords, bass,
  B section, rain bed");
- a **"how much is mine"** setting: *mostly mine* (additions only fill the gaps) → *collaborate*
  (default) → *run with it* (your hum is a starting seed, the tool writes more);
- direction chips include **"more of my idea"** and **"add something"** ("needs a hook", "needs a
  bridge", "needs atmosphere").

### 7.13 Lyrics and vocals (Phase 6)

For songs that should have real vocals (in LINE ZERO: the main theme, Soren's song and the finale,
per AUDIO_PLAN), the tool suggests lyrics, guides you through singing them and cleans up the vocal.
You still only steer: you pick lyrics and sing; you don't edit.

**1. Fitting the lyric to the melody (before any words are written).** The melody becomes a
"syllable map": for each phrase, how many notes (= syllables), which notes fall on strong beats (=
stressed syllables), which notes are long (= open vowels like "ah", "oh", "day"), and where the
rhymes go (phrase ends). Melismas (one syllable over several notes) are allowed where the style uses
them.

**2. Writing the lyrics.** A language model writes the words, because that's what it's good at:
- **Input:** the syllable map, the song's brief ("Soren's song: a busker who keeps forgetting the last
  bar; hopeful, a little lonely"), the mood, the rhyme scheme (for example ABAB verses, AABB chorus) and
  the house rules (English, clean for a teen audience, no real song lyrics, no brand names).
- **Which model:** either the **Claude API** (best lyrics; opt-in; costs a few cents per request; sends
  only the brief and syllable map, never audio) or a **local model** on your RX 7900 XT (its 20 GB of
  video memory runs a mid-size open model through llama.cpp's Vulkan backend; free and offline, but
  weaker lyrics). Decision open (§15).
- **Output:** 3 lyric options per section, each with a one-line idea ("the chorus turns the forgotten
  bar into a promise").

**3. Checking the lyrics** (the critic, rules in MUSIC_KNOWLEDGE.md §9b): syllable counts match the
notes; stressed syllables land on strong beats (checked with the CMU Pronouncing Dictionary); long and
high notes get open vowels; rhymes are real rhymes (or deliberate near-rhymes); the hook line is short
and repeatable; no lines that match known lyrics. You see the best 3; the chips work here too ("more
hopeful", "simpler words", "less cheesy", "rhyme less").

**4. Fitting the song to your voice.** A 1-minute range test (sing low to high on "ah") finds your
comfortable range. The whole song is moved to a key where the melody sits in it. A song written for a
very different voice isn't forced through pitch-shifting (that sounds fake); the key moves instead.

**5. Recording (a deliberate mode, not background capture).**
- Headphones on, so the backing track doesn't leak into the mic; pop shield in front; keyboard
  untouched.
- The backing track plays with a count-in and a guide melody, and the lyrics scroll karaoke-style.
- Sing each section 3-5 times. The tool also asks for a **double** (the same part again) and, where
  it fits, a **harmony** line (it plays you the harmony notes to follow). Real doubles and harmonies
  sound far better than copies made by pitch-shifting one take.

**6. Cleanup (automatic).**
- **Comping:** each phrase is scored on pitch accuracy, timing, tone and noise, and the best take per
  phrase is joined with short crossfades at breaths.
- **Timing:** each syllable is found (forced alignment with a speech model such as wav2vec2/WhisperX),
  then nudged toward the grid, gently, keeping the style's feel.
- **Pitch correction:** each note is pulled toward its target with natural speed and vibrato kept, a
  formant-preserving pitch shifter so it doesn't sound robotic (amount per style: light for neo-soul,
  tighter for J-pop). A hard "auto-tune effect" only if a pack asks for it.
- **Cleanup chain:** noise removal, breath reduction (lowered, not deleted), de-essing, plosive control,
  EQ, compression, then the style's reverb and delay sends.
- **Mix:** the vocal sits on top; the arrangement is carved around it (the lead melody instrument drops
  out or moves under the vocal).

**7. Checking the vocal:** pitch within about ±20 cents on held notes, timing within the style's pocket,
and **intelligibility**: a speech recogniser (Whisper) transcribes the mixed song back, and if it can't
make out the words, the vocal is buried or mumbled and the mix is fixed.

**Not the default: singing-voice synthesis** (a computer voice singing the lyrics). Open-source options
exist (DiffSinger, NNSVS), but quality and voice licences vary. It could make **guide vocals** so you hear
the lyric before singing it; a final vocal should be yours (or a singer you work with).

---

## 8. Style packs, starting with the Persona-inspired family

### 8.1 What a style pack is

A style pack is a **data file** (one JSON or TOML per style), not code. Adding a style means writing a
file. Each pack has:

```
name, description
tempo range, preferred tempo, swing amount, groove template
meters allowed
chord vocabulary (chord types, borrowed chords allowed)
progression table (chord-to-chord likelihoods, cadence types)
melody tensions allowed (which non-chord tones are "good")
bass cells (rhythm + slot patterns)
drum patterns + overlays (ghost notes, fills, crash rules)
instrument roles (which instrument plays lead / harmony / bass / texture) + voicing rules
forms allowed + variation tricks
mix chain (EQ, compression, reverb, saturation, stereo width) + loudness target
"signature moves" (small idioms: a brass stab on the "and" of 4, a chromatic run into the chorus)
"avoid" list (things that would make it a copy, §8.3)
```

### 8.2 The Persona-inspired family

What makes Persona soundtracks feel like Persona is mostly **genre and production**, which nobody owns:
groove-first rhythm sections, jazz and soul chords inside pop songs, strong bass lines, and a city-at-night
mood. The packs below capture *those genres*. Combined with your own melodies they give the vibe without
copying any track.

Each row is a separate style pack. The "Line Zero cue" column says where it fits in AUDIO_PLAN §3.2.

| Pack | Inspired by (genre, not a track) | Tempo / feel | Harmony | Rhythm section | Lead colours | Line Zero cue |
|---|---|---|---|---|---|---|
| **City-pop day** | 80s Japanese city pop, J-funk | 92-104, light swing | maj7, m7, 9ths; the IVmaj7 → V7 → iii7 → vi7 movement common in J-pop; secondary dominants | finger bass with octave pops, tight kit with open hat on the "and", cutting 16th guitar | Rhodes, chorused clean guitar, flute | `city_day`, `school`, `shop` |
| **Neon night** | neo-soul, lo-fi hip-hop | 84-92, heavy swing, laid back | m9, m11, 13 chords; Dorian minor; ii-V loops | boom-bap kit, behind the beat; sub bass | Wurlitzer, muted trumpet, vinyl and rain texture | `city_night`, `hideout`, `bond` |
| **Acid-jazz battle** | acid jazz, jazz-funk, breakbeat (AT67 decided 150-170 BPM) | 150-172, straight 16ths | dominant 7#9, tritone subs, chromatic chord slides | **your beatbox as the break** + funk ghost notes; walking/slap-style bass with chromatic approaches | overdriven guitar riff, Rhodes stabs, brass stabs on anticipations, vocal chop hook | `battle`, `battle_ambush` |
| **Half-time battle** | hip-hop and breakbeat battle themes | 85-92 (feels 170) | minor, Aeolian/Dorian, power chords on the hook | heavy boom-bap, 808 or synth bass | piano riff, strings, vocal chop | alt `battle` |
| **Dread boss** | orchestral rock, trailer hybrid | 140-150 | minor with bII (Phrygian), diminished passing chords | big toms, double-time hats, distorted bass | choir pad, low brass, distorted guitar | `battle_boss`, `battle_final` |
| **Velvet waltz** | jazz waltz, French café | 66-76, 3/4 | maj7/m6 chords, chromatic inner lines | brushed kit, upright bass on beat 1 | muted trumpet, celesta, accordion-like pad | `lost_car` |
| **Empty room** | ambient piano | 60-72, rubato | sparse, open 5ths and sus chords | none, or very soft pulse | solo piano + big reverb, music box | `stop1`, `sad_soft`, `ward` |
| **Arcade** | chiptune / city-pop synths | 128-140 | the same chords as city-pop day | 8-bit noise kit, square-wave bass | pulse-wave lead, arpeggios | `stop3`, `arcade_minigame` |
| **Forgetting** (a *filter pack*, not a genre) | tape wear, degraded memory | inherits the source cue's tempo | inherits, with notes dropped | inherits, thinned | low-pass, bit-crush, ±10 cent wobble, high sine | `city_drained`, `departure_0000` |
| **Victory sting** | jazz-funk ending | quantised to the battle tempo | I → IV → V → Imaj9 (or bVI → bVII → I) | one fill + crash | muted trumpet lick + Rhodes chord (**not** a sax jingle, per AUDIO_PLAN) | `victory`, `bond_rankup` |

**Same melody, different pack:** because the melody is the constant and the pack changes everything
around it, one hum can become the field theme, its night version and its battle version. That is exactly
how Persona-style soundtracks hang together, and exactly what AUDIO_PLAN's "Var" cues need.

### 8.3 Staying on the right side of "inspired by"

Copyright protects specific melodies, lyrics and recordings, not genres, tempos, instruments or common
chord progressions. AUDIO_PLAN §3.1 adds a stricter **house rule**: avoid Persona's exact fingerprints.
Each pack's **avoid list** enforces it:
- no saxophone as the lead identity in battle packs (that's P5's fingerprint);
- no rap vocal as the battle signature (P3's);
- no sampled breaks from records (for example the Amen break): your beatbox *is* the break, which is both
  legally clean and more original;
- the originality check (§10) runs on every melody, bass line and riff the packs generate, not only on
  your hums.

### 8.4 Building the packs

1. Write each pack by hand from music theory for that genre (chord vocabularies and progression tables
   are well documented in jazz and pop theory books).
2. Tune it by ear: generate 20 results from a few test hums, rate them, adjust.
3. Optional later: learn rough statistics (tempo, chord-type frequency) from a **broad** genre dataset
   (hundreds of songs, so no single track dominates). Never from a handful of Persona tracks: that would
   pull the output toward copying them.

---

## 9. Worked example: one hum, six LINE ZERO cues

You hum an 8-bar melody while coding. It's detected, cleaned to **D major, 94 BPM, 4/4, slight swing
(58%)**, range A3 to F#5, mostly stepwise with a leap up in bar 5.

| Request | What the engine does | Result |
|---|---|---|
| **City-pop day** | keeps 94 BPM and the swing; harmonises with maj7/m7 chords (e.g. Gmaj7 - A7 - F#m7 - Bm7 under bars 1-4); finger bass with octave pops; your beatbox loop as the kit plus open hats | `city_day` |
| **Neon night** | moves to B minor (relative minor) or D Dorian; slows to 88; m9 voicings on Wurlitzer; melody moved to muted trumpet; boom-bap kit laid back | `city_night`, same length and form so the MusicDirector can swap at a phrase and keep its place |
| **Acid-jazz battle** | doubles to 164 BPM; re-rhythms the first 2 bars into a syncopated riff for overdriven guitar; tritone subs in the B section; walking bass with chromatic approaches; your beatbox doubled up as the break + ghost notes; pinch layer adds brass stabs | `battle` + `battle` pinch |
| **Velvet waltz** | converts to 3/4 at 72; Rhodes becomes celesta, trumpet carries the tune | `lost_car` (if this hum becomes H) |
| **Timetable (T)** | inverts the melody, quantises to a rigid click, strips the swing, plays it on a ticking music box over a drone | the Stationmaster's theme |
| **Forgetting** | the city-pop day render with 25% of notes dropped (weakest first), low-pass 2.5 kHz, tape wobble | `city_drained` (or done live by the MusicDirector's DSP) |

Plus: a **victory sting** from the first 5 notes, and a **Bond-rank sting** from the same 5 notes on
trumpet. Every one of them is the same idea, so the soundtrack feels connected.

**Your own Hum can literally be the Hum.** AUDIO_PLAN's motif H is "a 6-8 note lullaby-like phrase", and
the bridge of Soren's song is H. MouthMixer is a natural way to write it: hum candidates for a week,
keep the best idea thread, and the motif table in §7.6 produces T (inverted), the forgetting version and
the Lost Car version from it.

---

## 10. Stage G: the originality check

### 10.1 Why normal song recognition won't work

Shazam-style fingerprinting (Chromaprint, AcoustID) matches *recordings*. Your hum of a song is a
different recording, so it never matches. What's needed is **melody similarity**, the technology behind
"hum to search".

### 10.2 How it works

1. **Make the melody key- and tempo-proof.** Turn notes into a list of (interval to next note in
   semitones, duration ratio to next note). "C-E-G" and "F-A-C" become the same list.
2. **Reference database.** Turn every melody in a reference set into the same lists:
   - the **Lakh MIDI Dataset** (about 176,000 MIDI files) with melody tracks found automatically;
   - extra sets for game and anime music;
   - **your personal "danger list"** (most important, see 10.3).
3. **Fast search.** Index short runs of intervals (5-note n-grams) so a query only compares against
   melodies that share some runs (like a search engine). This keeps it fast on a laptop.
4. **Careful comparison.** For each candidate, align the two melodies with dynamic time warping, allowing
   small rhythm and ornament differences, and measure the **longest closely matching run** in beats and
   an overall similarity score.
5. **Also check:** bass lines, and melody + chords together (a melody that matches *and* sits on the
   same chords is a much stronger warning).

### 10.3 The personal danger list (the Persona problem)

You listen to a lot of Persona music right now. Those are the songs you are **most likely to recreate
by accident**, because they are stuck in your head. So:
- **You build a list of what you listen to a lot.** Add MIDI or transcriptions of those songs. The check
  weights matches against this list higher.
- **Automatic help:** the loopback stream (§3 B3) can be fingerprinted against your *own* music files
  (Chromaprint works here because it's the actual recording), so the tool can log "you listened to track
  X today". A hum that matches anything on today's or this week's listening log gets checked harder.
- MIDI files for comparison are only used locally to check against, never shipped or used as material.

### 10.4 What it shows you

| Result | Rule (starting values, to be tuned) | Shown as |
|---|---|---|
| Clear | no matching run of more than 4 notes | green |
| Common phrase | a 4-6 note match found in many songs (it's a stock phrase, e.g. a scale run) | grey "common phrase", no action needed |
| Look at this | 7+ notes matching closely in rhythm and pitch with one specific song | amber: shows both melodies side by side, plays both |
| Too close | 10+ notes or 2+ bars, or melody + chords both match | red: blocked from export until you change it or override it |

**Fix-it helpers** for amber/red: suggest which notes to change (the ones that make the match), try a
different rhythm on that bar, or a different harmonisation.

**Honest limits:** no database has every song, and this is not legal advice or clearance. It catches the
common case (an accidental recreation of a known tune) and makes you look twice at anything close.

---

## 11. Stage H: rendering and export to Roblox

### 11.1 Rendering

- **Quick previews:** FluidSynth with free, permissively licensed SoundFonts (GeneralUser GS, FluidR3).
  Fast and good enough to judge ideas.
- **Final renders:** Spotify's **pedalboard** or **DawDreamer** (Python) can load real VST instruments and
  effects, for example the free **Vital** synth, **Dexed** (FM electric pianos) and **Spitfire LABS**.
  Check each instrument's licence allows game use (most free ones do; check the small print).
- **Humanise:** the expression kept in C1 (bends, vibrato, dynamics) is applied to the lead instrument.
  Velocity and timing get small random variation within the style's groove.
- **Mix:** each style's mix chain (EQ, compression, reverb, saturation). Master to a consistent loudness
  (about -14 LUFS integrated, true peak below -1 dB) so all cues sit at the same level in game.
- **DAW route (optional):** every arrangement also exports as multi-track MIDI + stems. You don't need
  it (you only steer), but it keeps the music portable if a composer or collaborator ever wants it.

### 11.2 Export for LINE ZERO

- **Files:** OGG (smaller) or WAV, 48 kHz or below, under 7 minutes and 20 MB (AUDIO_PLAN §2.4 limits,
  **[verify]** before relying on them).
- **Seamless loops:** loops are rendered with the reverb tail of the loop end mixed back into the loop
  start, so there's no gap or click when it loops. The export writes `introEnd`, `loopStart`, `loopEnd`
  and BPM, which match `PlaybackRegion` / `LoopRegion` and the MusicDirector's cue data (AUDIO_PLAN §3.4).
- **Cue data:** a small file per track with the cue id, BPM, beats per bar, loop points and layer names,
  ready to paste into `shared/MusicCues.luau`.
- **Layers vs stems:** AUDIO_PLAN warns several Roblox Sounds may not start in exact sync **[verify]**.
  So the default export is **full-mix versions per intensity level** (calm, full, pinch) of the same
  length, switched at bar boundaries (horizontal switching), which is safe. Separate stems are exported
  too, for when sync is verified.
- **Upload:** Roblox's Open Cloud Assets API can upload audio from a script **[verify the current
  endpoint and quotas]**. If it works, the tool can upload and write the new ids into
  `assets/sounds/sound_ids.csv`. Uploads go through moderation, so the upload quota (about 100 per 30 days
  unverified) means: only upload finished tracks, not drafts.

### 11.3 Mixing rules (automatic, per style)

- **Every role owns a frequency area.** Bass and kick share the lows, so the bass gets a gentle EQ dip
  where the kick is strongest and **ducks a few dB on each kick hit** (sidechain). The lead owns the
  upper mids (about 1-4 kHz) and the chords are carved slightly there to make room. Everything except
  kick and bass gets a high-pass filter so the low end stays clean.
- **Panning map per style:** kick, snare, bass and lead in the centre; hats, guitars, keys and
  counter-lines spread left/right; pads wide.
- **Shared reverb and delay** (two or three effect buses for the whole song, not one reverb per
  instrument), so the instruments sound like they're in one room.
- **Lead first:** the mix is balanced around the melody. It must be clearly audible without being loud.
- **Phone-speaker check.** Many Roblox players are on phones, where everything below about 150 Hz
  disappears. The tool previews the mix through a "phone speaker" filter and checks the bass line is
  still heard; if not, it adds harmonics to the bass (light saturation) so the ear still hears it.
- **Mono check:** wide stereo tricks can cancel out on mono speakers; checked automatically.
- **Loudness:** about -14 LUFS, true peak below -1 dB (§11.1), so every cue sits at the same level.

---

## 12. Problems and risks, with solutions

| # | Problem | Why it happens | Solutions |
|---|---|---|---|
| 1 | **Keeps junk** (talking, "hmm", sighs) | talking has pitch; short hums of thought sound musical | three-stage gate (§3); minimum 1.5 s + 2 s of "musical voice"; strict start; the inbox's "not music" button trains the personal classifier |
| 2 | **Keeps other sound** (TV, YouTube, Spotify, other people) | the mic hears the room | speaker check (enrolment); WASAPI loopback correlation drops playback; headphones recommended; auto-pause while media plays (optional) |
| 3 | **Misses ideas** | thresholds too strict, very quiet hums | 30 s ring buffer + pre-roll; instant-replay hotkey; weekly report of hotkey saves to loosen thresholds |
| 4 | **Privacy** (an always-on mic hears everything) | it's a microphone | 100% local, no network except the optional Roblox upload; non-music never leaves RAM; the buffer is overwritten every 30 s; visible tray state; one-click pause; auto-pause when Discord, Zoom, Teams etc. are using the mic; schedules ("never record after 22:00"); a "forget today" button |
| 5 | **Slows the PC** (bad when also gaming or running Studio) | ML models on audio | only the tiny VAD runs constantly; the classifier runs only on candidate sound; transcription and cleanup are queued for idle time; a "game mode" that pauses heavy work when CPU is busy or a fullscreen game runs |
| 6 | **Poor mic** (laptop mic, fans, keyboard noise) | noise creates fake notes | DeepFilterNet/RNNoise first; a mic check in setup; recommend a cheap USB or headset mic; the pitch tracker's confidence drops noisy frames |
| 7 | **Off-pitch hums** | nobody hums perfectly | probabilistic key-aware snapping (§D4); pitch from 2 trackers; deliberate chromatic notes kept and marked |
| 8 | **Tempo drift** | people speed up when excited | tempo curve + warp before quantise (§D1); half/double-time question in the inbox |
| 9 | **Beatbox misclassified** | everyone's sounds differ | 3-minute personal calibration; kNN on your examples; every correction retrains |
| 10 | **Fragments, not songs** | ideas come in 3-second pieces | idea threads join takes over days (§6); the arranger builds sections from 2-bar ideas by repetition and variation; the counter-line generator fills gaps |
| 11 | **Robotic results** | over-quantising and plain MIDI | 70% quantise default; swing and groove kept; expression curves reapplied; humanise; real VST instruments |
| 12 | **Generic results** ("sounds like stock music") | rule-based styles can be bland | the melody is yours and stays central; motif transformations; surprise slider; lock-and-reroll; taste learning from ratings |
| 12b | **Weak ideas reach you** | you don't edit, so every bad option costs your time | the critic (§7.11) with hard rejects, scored rules, listening models and your taste model; it shows only 3 and says what it filtered |
| 13 | **Accidental copying** | songs you love get stuck in your head | melody-similarity check + personal danger list + listening log (§10); runs on generated parts too |
| 14 | **Too close to Persona's style** | the packs aim at a vibe | packs model genres, not tracks; avoid lists (§8.3); never train packs on a few Persona tracks; AUDIO_PLAN's city-pop/neo-soul direction is the house sound |
| 15 | **Licensing of sounds** | SoundFonts/VSTs/samples have licences | keep a licence record per instrument; prefer CC0/permissive; no record samples; the AI-generation route stays off (AUDIO_PLAN §3.1) |
| 16 | **Roblox playback limits** | stem sync, upload quota, moderation | full-mix intensity versions by default; upload only finished cues; loudness-normalised; instrumental and original content, so moderation is low risk |
| 17 | **Scope creep** (it's a big project) | many stages | strict phases (§14); each phase is useful alone; MIDI export from Phase 2 means a DAW can do everything later stages don't do yet |
| 19 | **Weak or awkward lyrics** | words that don't fit the notes or sound cheesy | syllable maps + stress and vowel checks (§7.13); 3 options; chips like "less cheesy" |
| 20 | **The vocal sounds processed** | heavy pitch correction | key moved to your range first; real doubles and harmonies; gentle, formant-preserving correction |
| 18 | **Losing the library** | a local folder on one PC | library folder in a synced location (OneDrive) or a separate git repo with Git LFS for audio; the SQLite database can be rebuilt from the files |

---

## 13. Architecture and tech choices

**Platform:** Windows first (you're on Windows; WASAPI loopback is Windows-native). Python for the whole
prototype, because nearly every audio/music library needed is a Python library.

```
mouthmixer/
  listener/     background service: mic + loopback capture, ring buffer, VAD, classifier gate
  analysis/     noise reduction, pitch tracking, onsets, beatbox classifier, tempo, key, cleanup
  library/      SQLite database + audio/MIDI files, idea threads, search
  arrange/      style packs, compatibility, harmonisation, bass/drums/voicings, forms, motif transforms
  originality/  melody index, reference sets, danger list, listening log
  render/       FluidSynth previews, pedalboard/VST final renders, mixing, loudness, loops
  export/       WAV/OGG/MIDI/stems, cue data, Roblox Open Cloud upload
  app/          the window: inbox, library, arranger, settings (local web UI in the browser, or PySide6)
  styles/       *.toml style packs
```

**Main libraries:**

| Job | Library |
|---|---|
| audio in/out (incl. WASAPI loopback) | `sounddevice` or `soundcard` |
| voice activity | `silero-vad` |
| sound classification | YAMNet (TensorFlow Lite) or PANNs (PyTorch) |
| speaker check | `resemblyzer` or SpeechBrain ECAPA |
| noise suppression | DeepFilterNet or RNNoise |
| pitch / notes | `basic-pitch`, `crepe` (or `torchcrepe`), `librosa.pyin` |
| onsets, tempo, beats | `librosa`, `madmom` |
| MIDI and theory | `pretty_midi`, `music21`, `mido` |
| fingerprinting (listening log) | Chromaprint (`pyacoustid`) |
| rendering | `pyfluidsynth`, `pedalboard`, `DawDreamer` |
| loudness | `pyloudnorm` |
| lyrics | Claude API (opt-in) or a local model via llama.cpp (Vulkan); CMU Pronouncing Dictionary (`pronouncing`) |
| vocal timing / intelligibility | WhisperX or wav2vec2 forced alignment; Whisper |
| vocal pitch correction | a formant-preserving shifter (Rubber Band library or WORLD vocoder via `pyworld`) |
| tray app | `pystray` |
| database | SQLite |

**Your hardware (Ryzen 9 7900 + RX 7900 XT).** The 12-core CPU runs everything comfortably; the GPU is a
bonus. Because it's AMD, the models are run through **ONNX Runtime** (Basic Pitch, CREPE, YAMNet, PANNs,
CLAP all export to ONNX) with the **DirectML** provider on Windows, which works on Radeon cards, and the
CPU provider as the fallback. Nothing may require CUDA. (PyTorch on AMD under Windows exists but is still
patchy **[verify at build time]**, so it's not relied on.)

**Process layout:** the listener is a small separate process (so a crash in the heavy parts never stops
listening, and it stays light). It writes kept clips to an "incoming" folder; the analysis worker picks
them up. The app reads the library.

**Where it lives:** its own repository, `magnuswilliam/mouthmixer` (decided). LINE ZERO keeps only a
pointer to it.

**Packaging later:** PyInstaller for a one-folder Windows app, with a start-with-Windows option.

**The shortcut:** a desktop and Start-menu shortcut starts the listener (if it isn't running) and the
local web server, then opens the page in an **app window** (Edge or Chrome `--app=http://localhost:PORT`
mode: its own window, no tabs or address bar, so it feels like a normal program). The tray icon's menu
has "Open MouthMixer" too.

**How it gets built and tested (important).** The build sessions run in a cloud container with **no
microphone and no speakers**: Claude can't hear the results. So:
- Every stage gets automated tests on **synthetic audio** (generated hums with wobble, drift and
  vibrato; generated beatbox-like hits) where the right answer is known.
- **Your Phase 0 recordings** (only the clips you choose to share, see §14) are the real-world test set.
- Claude checks the numbers (detection rates, pitch accuracy, loudness, clashes from the music lint),
  but **you are the ears**: every phase ends with you running it on your PC and listening.
- A one-command setup script for Windows installs everything and makes the shortcut.

---

## 14. Build phases, with "done when" tests

Each phase is useful on its own.

**Phase 0: collect test data (before writing any real code; a few days).**
- Run a plain recorder while you work for 2 or 3 normal days (with the privacy rules above in mind,
  for example only while you're alone).
- Mark the musical moments by hand (a simple list of times and "hum / beatbox / sing").
- *Done when:* you have about 2 hours of real-life audio with labelled musical moments. Every later
  stage is tuned and tested against this set, so we know the numbers instead of guessing.
- You choose what to share with the build session: the musical moments plus a handful of non-musical
  examples (typing, talking to yourself, background noise) that you're comfortable sharing. Nothing
  private is needed.

**Phase 1: capture.** Listener, VAD, classifier gate, speaker check, loopback rejection, hotkey,
tray icon, inbox (play, keep, toss).
- *Done when:* on the Phase 0 audio, it catches **at least 85%** of the labelled musical moments and
  **at most 1 in 5** kept clips is junk, at under 3% average CPU.

**Phase 2: transcription and cleanup.** Noise reduction, melody transcription, beatbox calibration and
classification, tempo warp, key, quantise, tidy; MIDI export.
- *Done when:* played back, the cleaned version of your hum sounds like what you meant, **without you
  fixing anything** (when it's wrong, "not what I hummed" offers the next-best reading and gets it within
  2 tries); beatbox hits are right at least 90% of the time after calibration.

**Phase 3: library and originality.** Tags, idea threads, search, the melody index (Lakh MIDI), danger
list, listening log, amber/red warnings.
- *Done when:* humming 4 bars of a well-known song (deliberately) is flagged red, and your own ideas
  mostly come back green; repeated takes of the same idea land in one thread.

**Phase 4: the pairing engine, the critic and the first style packs.** Compatibility scores, harmonisation, bass
cells, drum overlays, voicings, forms, motif transforms, lock-and-reroll. Start with 3 packs:
**city-pop day**, **neon night**, **acid-jazz battle**.
- *Done when:* from one hum you can produce a day, night and battle version in under 10 minutes that you'd
  be happy to use as a placeholder in LINE ZERO.

**Phase 5: rendering and game export.** VST rendering, mixing, loudness, seamless loops, intensity
versions, cue data, (optional) Roblox upload.
- *Done when:* an exported loop plays in Studio with no click at the loop point, at the same loudness as
  other cues, and the MusicDirector can switch day → night at a phrase without losing its place.

**Phase 6: lyrics and vocals** (§7.13). Syllable maps, lyric writing and checking, range test, the
recording mode, comping, timing and pitch correction, the vocal chain and the intelligibility check.
- *Done when:* you can pick lyrics, sing 3 takes of a verse and chorus, and get back a clean, in-tune,
  understandable vocal sitting well in the mix, without touching anything.

**Phase 7: the rest of the packs and polish.** The other packs from §8.2, taste learning, the surprise
slider, packaging as a Windows app.

**Build status (2026-10-12): Phases 1-2, first version, built.**
- Built: listener (segmenter with pre-roll and 30 s ring buffer, hotkey, tray icon with states, mute
  detection, auto-pause for call apps and quiet hours, retry when the mic is missing); the music gate
  (hand-written features from §3 B2 only); melody transcription (pYIN + hysteresis note cutting); beatbox
  transcription with rule classifier and per-user kNN calibration; tempo with linear drift, swing,
  downbeat, quantising with strength, key/mode with tuning offset and probabilistic scale snap, note
  tidying, phrases; MIDI and preview export; the inbox app (keep / toss / not music / "not what I
  hummed" readings, calibration, mic test, upload) and the Windows setup + shortcut.
- Results on synthetic audio: the gate sorts all test clips (hums, beatbox, talking, typing); beatbox
  hits 100% on 8 test patterns; 33 of 36 drifting, off-pitch hums note-perfect (the 3 misses read
  72 BPM as 144; the "half tempo" reading fixes them).
- Not built yet from Phases 1-2: Silero VAD and the YAMNet/PANNs classifier (B1), the speaker check and
  loopback check (B3), the personal classifier trained on inbox answers, noise suppression
  (DeepFilterNet), Basic Pitch/CREPE as second pitch tracker, idea threads (Phase 3).
- **Next:** the user's first real hums and Phase 0 recordings; tune the gate and transcription on them.

**Build status (2026-10-12, later): songs before the inbox (parts of Phases 4-5, at the user's request).**
- The user asked that nothing reach the inbox until it's inside a full, polished arrangement, with many
  instruments, clip combinations, effects, and rule-based checks for unsure clips; and for a mic picker.
- Built: `arrange/` with six style packs (city-pop day, neon night, acid-jazz battle, orchestral
  adventure, arcade, dream) and 60 instruments plus 8 drum kits from GeneralUser GS (bundled in
  `assets/soundfonts`, free for commercial music); harmonisation by beam search; bass, comping, pad,
  arpeggio, guide-tone counter-line, drums (from the user's beatbox when there is one), timpani;
  form Intro/A/A'/B/A''/Ending with a B section grown from the motif (or another clip's melody);
  rendering through TinySoundFont, effects through pedalboard, sidechain, reverb/delay buses, mono lows,
  -14 LUFS master with a look-ahead limiter; the critic (MUSIC_KNOWLEDGE rules H1, H2, H6, A4, B3, M1-M15,
  X1, X4, X7, X10, X11 and §10 weights); the songwriter (14 candidates per clip, render the best 4, keep
  3 versions, rotate styles); clip quality Q1-Q6 and the listener's second opinion; songs inbox with a
  multi-part score view, versions, another version / different style; mic picker with a live level.
- Measured on synthetic clips: 78 of 80 candidates pass the critic; every rendered mix at -14 LUFS with
  peaks at or under -1 dBFS; talking and typing never rescued.
- Not yet: the user's taste model, direction chips, loops for the game (§11.2), stems export,
  the originality check (Phase 3).

**Build status (2026-10-13): mixer, more sounds, lyrics and vocals (parts of Phases 4-6, at the user's
request).**
- Research written up: [`PERSONA_STYLE.md`](PERSONA_STYLE.md) (genres per game, tempos, harmony, rhythm
  section, brass, catchiness, vocals, fingerprints vs traits), [`ARRANGING.md`](ARRANGING.md) (layers,
  register slots, 36 instrument pairings, mood palettes, vertical layering) and [`VOCALS.md`](VOCALS.md)
  (recording, clean-up, timing, tuning, the 13-step chain, 7 presets, the Sing screen, lyric rules,
  quality gates).
- Sounds: 131 instruments (all checked in the soundfont) plus 10 drum kits and 4 generated textures;
  three new packs (heist funk, bright pop-rock, moonlit hip-hop) with a 2-bar keyboard/brass riff (the
  hook) from A' on and a 2.5 kHz carve on chords and pads so the melody stays clear.
- **Mix tab** (`arrange/catalog.py`, `arrange/mixer.py`): 69 part types in 11 categories, generated to fit
  the song's chords and form; suggestions ranked by vibe (12 vibes), pairings (about 56, with reasons),
  missing layers and crowding; parts render to cached stems so switching is instant in the browser; save
  bakes a mastered, critic-checked new version. Swapping a chord part's sound re-checks it against the
  melody (H1).
- **Lyrics tab** (`arrange/lyrics.py`): syllable map of the melody (lines split where a singer breathes),
  Claude writes 3 options from a brief (structured output, adaptive thinking), or type your own; every
  option is checked (syllable counts, stress, closed vowels on long high notes, hook repeats, clean
  language) and aligned to notes for karaoke.
- **Sing tab** (`app/static/studio.js`, `arrange/vocals.py`): section loop with count-in and clicks in
  quiet bits, guide-melody and music volume, live pitch lane (green/yellow/red at 25/50 cents), karaoke
  wipe, mic picker, sync test for latency, takes with per-line scores; "Tune, time & mix my vocals" comps
  the best take per line, cleans (high-pass, noise reduction from the count-in, plosives), corrects timing
  and pitch with the WORLD vocoder (natural or hard), lowers breaths, runs the preset chain (de-esser, two
  compressors, presence/air, saturation, riding, doubles, harmonies, plate reverb, dotted-1/8 delay with
  throws) and sits the vocal against the music (level per preset, 1-4 kHz pocket, your hummed lead
  ducked). The vocal becomes a "Your vocals" part in the mixer.
- Measured on synthetic singing: onsets found within ~5 ms; average pitch error 11 → 4 cents with 97% of
  frames in tune (bright-pop preset); the singer's lateness kept as feel within 2 ms of the truth; mixes
  with vocals at -14 LUFS and passing the critic.
- Not yet: the range test and key transpose, the intelligibility check (speech recognition), real doubles
  and harmonies from separate takes, the mixer's preview of the lead ducking (it's applied on save).
- **Next:** the user listens: songs with the new packs, the mixer, and a first sung verse (run the sync test
  first). Rerun setup: new dependencies.

**Fix (2026-10-13): frozen mic.** The user's three hotkey saves were identical and not what they had
just done: the mic had stopped calling back (USB drop-out or sleep) while the listener kept running, so
the 30 s memory froze. Now: a watchdog reopens the mic after 3 s without audio; a save with no fresh
audio is refused (and reopens the mic); two identical hotkey clips are never both written; a crash in
the audio thread is logged and skipped; the status bar says when the mic has gone quiet or was
reconnected.

**Build status (2026-10-13, later): Make, the purposeful workflow.**
- `studio/starters.py`: 10 starter beats in 5 moods, each with a main loop (A) and bridge loop (B) and
  generated beat, bass, chords and pad; two new styles (tense dungeon, boss rock).
- `studio/transcribe.py`: booth recordings read straight onto the known grid (tempo, key, bar 1 and the
  piece's length are known): hums to notes (snapped to the key), beatbox to drums or percussion; every
  pass round the loop is a scored take.
- `studio/project.py`: pieces, takes, one-note fixes, simpler/busier, octave, key change; pitched pieces
  remember the chords they were sung over and follow other chords by scale steps (a bassline follows
  the bridge); accent stabs become 3-note chord hits; booth loops render seamlessly per piece; the song
  board builds a full song into the Songs list (rebuilds add versions), with vocal chops as audio parts.
- `app/make.py`, `app/static/make.js`: the Make tab (starters, Incredibox-style piece row with instant
  on/off, recorder with count-in and pass counter, notes strip with fix buttons, song board, build).
- Measured on synthetic audio: hooks hummed over a loop come back note-perfect (also with 90 ms latency
  removed); every starter builds a song with no clashes or range problems; the full browser flow
  (record a hook through a fake mic, build, open in Mix) works.
- Not yet: a range check before recording, chords from hummed roots (the starter's loops are used),
  more starters per mood, arrangement suggestions on the board.
- **Next:** the user tries Make with the QuadCast: one starter, a beat, a bassline and a hook.

**Fix (2026-10-13): updates and Windows file locks.** The user's setup run showed two problems. (1) Windows
refuses to replace a file another program has open; the listener's status file is read by the app every
second, so the listener's control loop could crash. Replacing now waits and retries (then copies), and
one failed control step no longer stops the loop. (2) The starter beats didn't show: the MouthMixer
started before the update was still running and served the new page without the new features. The app
and listener now report a code fingerprint; the launcher replaces an out-of-date copy (stopping whatever
holds the port if it's too old to understand), setup stops a running MouthMixer before installing, and
the Make tab says so plainly if the starters can't load.

**Build status (2026-10-13, evening): songs with real structure, voices, songbook.**
- Section **feels** on the song board (flashy intro, verse, build-up, chorus lift, rap pocket, breakdown,
  final chorus, outro): the starter parts change per section (open hats and crashes in a chorus, half-time
  boom-bap under a rap, drums out in a breakdown, a snare roll into a build, intro hits), plus risers into
  big sections and a three-note **station chime** (LINE ZERO's motif) in intros and outros.
- **Paste lyrics with [Section] headers** in Make and the board is laid out from them (lengths from line
  counts, feels from names, the bridge on the bridge chords); the words go to the Sing teleprompter.
- **Vocals without a hummed melody**: comped per section, tuned to the key (rap, spoken and whispered
  sections untuned). **Vocal tracks** (Lead, Rap, Gang, Backing, Harmony, Ad-libs, Announcer, Whisper) and
  **voice characters** (female, alto, deeper male, octave down, younger, raspy, breathy, whisper, gang
  shout, choir, PA announcer); research in VOCALS §11. Gang/backing tracks stack every take.
- **Band hits on vocal accents** (Mix): drum hits and brass stabs on the hardest-hit words.
- **Favourites**: save any recorded piece (a beat, a vocal chop...) and reuse it in other tracks, moved
  to the new key and tempo.
- **Starters for the LINE ZERO song list**: fast jazz-rock battle, night jazz (brushes, tenor sax), rainy
  bossa, piano ballad, choir boss (+ saxophones), and the **songbook** (`assets/songbook/`, docs/LYRIC_CRAFT.md):
  8 songs with lyrics, base beat and voice plan, startable from Make.
- Speed: vocal processing ~3x faster (pitch tracking only where there's sound, O(n) smoothing, one WORLD
  analysis shared by every character voice).
- Not yet: hearing a character before processing (preview), per-section characters within one track.
- **Next:** the user records "Last Train, First Light" from the songbook.

**Build status (2026-10-13, night): ready-made parts, recording timing, voice tweaks.**
- **Recording lag fixed.** Make subtracted only the Sing screen's sync-test value, which is 0 until that test
  has run, so every booth take landed late by the whole headphone-and-mic delay (a 16th late in the test
  that reproduces it). Now a take uses the browser's own latency estimate until the sync test has measured
  the real delay, the sync test sits on the Make recorder too, and takes recorded on the estimate are
  re-timed on Sing once it's measured. New "Whole piece ◀ earlier / later ▶" nudges fix pieces recorded
  before the fix. Booth loops now loop at exactly their bar length, so they can't drift apart.
- **Ready-made parts** (`studio/presets.py`): 20 beats, 13 basslines, 10 chord rhythms, 12 groove combos,
  and 38 phrases (riffs, stabs, answer lines, intro motifs, hooks, percussion, fills), all generic
  figures of their styles. Grooves replace the starter's pattern but keep the section feels (intro build,
  freeze, chorus lift, rap pocket, breakdown, three-hit ending). Phrases are written in chord tones and
  laid on the main chords, then behave like recorded pieces. Simpler/busier now also works on grooves
  (5 levels).
- **Voice tweaks** (VOCALS §12): pitch in notes of the key, tone, breathiness, grit, warmth, tuning style,
  doubling, a harmony voice that follows the key, echo, space, and effects (radio, megaphone, phone, robot,
  lo-fi tape), saved per vocal track; plus an 8-second **preview** of a voice without the band.
- Not yet: auditioning a ready-made part before adding it (adding plays it; delete or swap if it's wrong);
  per-section voice tweaks within one track.
- **Next:** the user runs the sync test in Make, builds "Last Train, First Light" from a combo and a few
  ready-made parts, and tries voices with Preview.

**Rough size:** Phases 1-2 are the biggest technical risk and should come first. Phases 4-5 are the
biggest amount of work.

---

## 15. Open questions for you

Answered 2026-10-12: own repo (`mouthmixer`), mic (QuadCast 2 + pop shield, headphones, boom arm for the
loud keyboard), app (browser page with a shortcut), LINE ZERO (only after the tool is proven), PC
(Ryzen 9 7900 + RX 7900 XT), free instruments, steer-only (no editing), MIDI downloads OK, first packs
(city-pop day, neon night, acid-jazz battle), lyrics and vocals (yes), lyrics model (Claude API). Still open:

1. **The Hum:** try writing LINE ZERO's motif H with the tool once it works (no commitment until you
   approve it for the game)?
