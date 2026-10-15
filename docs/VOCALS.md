# Vocals: recording, lyrics, processing and mixing

The spec behind `arrange/vocals.py`, `arrange/lyrics.py` and the app's Lyrics and Sing screens. You sing;
MouthMixer cleans, times, tunes, comps, processes and mixes the vocal into the song.

**How this was researched (2026-10-12):** web search across Antares (Auto-Tune), Celemony (Melodyne),
Synchro Arts (VocAlign), iZotope, FabFilter, Sound On Sound, Waves, MathWorks and MDN (latency), mir_eval and
EBU R128 (metrics), UltraStar/Performous/Guitar Hero (singing games), Pat Pattison (lyric prosody) and papers
on singing-voice processing (arXiv 2008.03388 on WORLD, Deep Autotuner). Fetching pages was blocked, so
figures come from search excerpts: **[V]** two or more sources agree, **[S]** one source, **[U]** our
engineering default (tune by ear; log changes in MUSIC_KNOWLEDGE.md §13).

---

## 1. Recording

| Setting | Default | Why |
|---|---|---|
| Mouth to mic | 15 cm, lean back ~5 cm on loud notes | 15-20 cm is the common working distance [S] |
| Pop shield | 5-8 cm from the mic | [V] |
| Levels | loudest peak about -10 dBFS; warn above -3, warn if everything stays under -24 | peaks -12 to -6, average about -18 [V] |
| Format | 48 kHz, 32-bit float | [U] |
| Room noise | measured in a 3 s silent pre-roll; warn above -60 dBFS | [U] |
| Headphones | closed-back, moderate level; soft click (woodblock), muted in quiet bits | headphone bleed [V] |

**Latency.** Browsers only estimate their latency (`AudioContext.outputLatency`), so we measure [V]: the
**sync test** plays clicks, you tap along (or hold the mic near the headphones), and the median offset is
stored per microphone. Tap-along is accurate to about ±10 ms (Rock Band's calibration is similar [V]).

**Takes.** 3-5 takes per section, up to 8 for hard ones [V]. Loop-record a section with a one-bar count-in
[U]. Each phrase of each take is scored; the best phrase per take is comped together with ~5 ms crossfades
placed just before a consonant, never mid-vowel [S].

## 2. Clean-up

- **Breaths** turned down 6 dB (range 3-9), never deleted; the breath right before a phrase only 4 dB, so the
  entry stays natural. Done before compression, which would bring them back up. [V]
- **Noise reduction:** spectral gating with the profile taken from the quietest 300 ms of the count-in above
  100 Hz, light by default (prop_decrease 0.35, about 4 dB; "stronger" is 0.6, about 8 dB), skipped when the
  noise floor is already under -65 dBFS; heavier settings cause "musical noise" and, measured on the user's
  takes, extra level jumps between syllables (§13). [V/U/M]
- **Plosives:** a burst under 150 Hz more than 10 dB above the phrase average, within 40 ms of a voiced
  onset, gets a 40-80 ms high-pass at 120 Hz with 10 ms fades. [S/U]

## 3. Timing

No published tolerances exist (VocAlign works on spectral patterns with a "tightness" control [V]), so:
- Subtract your average lateness first (keeps a consistent "behind the beat" feel), then correct the rest. [U]
- Onsets within ±25 ms of the note: left alone. 40-80 ms: pulled halfway. Over 80 ms: flagged. [U]
- Doubles and harmonies: onsets within ±10-15 ms of the lead. [U]
- Never stretch the middle of a vowel by more than ±20%. [U]

## 4. Pitch

Perception: within about ±10 cents counts as in tune; listeners vary from 10 to 40 cents; vibrato widens
the window by about 10 cents [S]. Auto-Tune's retune speed is 0 ms for the hard effect and 10-50 ms for
natural correction [V]; Melodyne users set correction strength to 60-80% for natural results [V].

**Natural mode (default):**
1. Notes come from the melody we already know.
2. Each note's pitch is the median of its stable middle 60%.
3. Within ±10 cents: left alone (like Flex-Tune).
4. Otherwise the **whole note** is shifted by (target - median) × strength (0.8), so vibrato and expression
   survive (the contour moves, it isn't flattened).
5. Slow drift (< 2 Hz) is halved; vibrato (4-8 Hz) untouched.
6. 30-50 ms easing at note starts; a scoop is corrected at most 50% in its first 30 ms.

**Hard mode** (arcade/hyperpop): instant, 100%, vibrato removed.

**How (since 2026-10-15):** PSOLA (`vocals.psola`): one mark per glottal cycle, two-period Hann grains of the
recording re-spaced to the new period (and, for timing fixes, read from the time-mapped position). Formants
stay where they are because the grains are the voice itself, consonants and breaths are the original, and a
passage that needs no move comes back sample for sample. Tuning **off** skips the tuner entirely. WORLD
(pyworld) is now used only where it is needed: a new tone (formant), grit, whisper, stacked voices and
harmonies. Why: §13.

## 5. The processing chain (in order)

| # | Step | Default |
|---|---|---|
| 1 | High-pass | 0.7 × the lowest sung pitch, clamped to 70-150 Hz, steep [V] |
| 2 | Clean-up EQ | find the strongest resonance in 200-500 Hz; cut 2-4 dB, narrow [V] |
| 3 | De-esser | 5-10 kHz band; only the loudest ~15% of "s" sounds; up to 6 dB (backing vocals 10) [V] |
| 4 | Compressor A (peaks) | 8:1, attack 2 ms, release 50 ms, about 4 dB on peaks [V] |
| 5 | Compressor B (leveling) | 3:1, attack 20 ms, release 120 ms, 3-5 dB average [S] |
| 6 | Presence + air | +2 dB at 3.5 kHz; +3 dB shelf from 10-12 kHz [V/U] |
| 7 | Saturation | light tape/tube colour [U] |
| 8 | Phrase leveling ("riding") | each phrase pulled toward a target, ±6 dB max [V/U] |
| 9 | Doubles | real doubles ±80-100% at -6 to -10 dB; or synthetic ADT: +12 ms/+5 cents and +19 ms/-5 cents, ±30%, -8 dB [V] |
| 10 | Harmonies | -6 dB, high-passed 150-200 Hz, de-essed harder, ±40-70% in pairs [V] |
| 11 | Reverb (send) | plate, 30 ms pre-delay, 1.4 s decay, return 250 Hz - 8 kHz [V] |
| 12 | Delay (send) | dotted 1/8, 20% feedback, 300 Hz - 5 kHz, ducked by the dry vocal; 1/4-note "throws" on line endings [V] |
| 13 | Sit in the song | vocal loudness about equal to the music (pop -1 LU); the music dips up to 3 dB at 1-4 kHz while you sing [S/U] |

## 6. Style presets (deltas from the chain above; mostly [U])

| Preset | Tuning | Compression | Colour | Space | Level vs music |
|---|---|---|---|---|---|
| Soul / city pop | natural, 45 ms, 0.6 | gentle 2-3:1 | warm tape, softer air | plate 1.6 s; real harmonies ±60% | -1 LU |
| Bright pop (J-pop/anime) | 25 ms, 0.85 | firm 4:1 | bright air +3 dB | plate 1.2 s + 1/8 delay; doubles on the hook | 0 to +1 LU |
| Rock / battle | 30 ms | heavy, parallel | more 1-3 kHz bite, drive | short plate 0.9 s, slap 100 ms | -2 LU |
| Cinematic | natural 50 ms, 0.6 | light | neutral | hall 2.5-3 s, 50 ms pre-delay | -3 LU |
| Lo-fi | loose 60 ms | medium | band-pass 300 Hz-4 kHz, tape | short room | -3 LU |
| Arcade / hyperpop | hard 0 ms | heavy | optional +12 st layer | short, heavy doubles | 0 LU |
| Dreamy | 40 ms | light | air +3 dB | long hall, shimmer 10-15% | -3 LU |

Each style pack picks a preset: city-pop day and heist funk → soul; bright pop-rock → bright pop; acid-jazz
battle → rock/battle; orchestral → cinematic; neon night and moonlit hip-hop → lo-fi or soul; arcade → arcade;
dream → dreamy.

## 7. The Sing screen

- Two lines of lyrics: the current one with a **syllable-by-syllable wipe** driven by the note times (a
  constant-speed wipe drifts) and the next one, shown at least 2 s ahead. [S/U]
- A **pitch lane** (SingStar-style): target notes as bars, your live pitch drawn over them, green within
  ±25 cents, yellow to 50, red beyond, with a sharp/flat arrow; any octave counts. [S/U]
- One bar of count-in (two on the first take) with clicks and 3-2-1 dots; guide melody about -12 dB under
  the music, which you can turn down as you get it. [U]
- Loop one section with a one-bar run-in; a take list with a per-phrase strip (pitch, timing) and a score.

## 8. Lyrics

Written by Claude (decided) from a brief and the melody, then checked:
- **Prosody (Pattison):** stressed syllables on strong beats and longer/higher notes. [V]
- **One syllable per note**; a stretched syllable (melisma) only on an open, stressed vowel, at most 3
  notes. Lines off by more than one syllable are flagged. [U]
- **Open vowels** ("ah", "oh", "eh") on long, high notes; closed ones ("ee", "oo") flagged there. [V]
- **Hook:** the title in the first and/or last line of the chorus, repeated 2-4 times; short and chantable
  (the Persona lesson, PERSONA_STYLE §6). [V]
- **Section roles:** verses tell the story; the chorus is the most stable and repeated (even line counts,
  matched lengths, closed rhymes); the bridge brings a new angle. [V]
- Line length: 6-10 syllables in verses, 4-8 in the chorus, couplets within ±2. [U]
- House rules: English, clean for a teen audience, no brand names, no real song lyrics.

## 9. Quality gates

| Check | Default |
|---|---|
| Pitch | per-note median error ≤15 cents good, ≤30 OK, >50 flagged; 90% of note-frames within ±25 cents after correction, with vibrato averaged out (200 ms) and the first 60 ms of each note (the scoop) skipped [V/U] |
| Timing | median onset error < 30 ms, 95th percentile < 60 ms [U] |
| Sibilance | the loudest 5-10 kHz moment no more than 0 dB over the line's median level (all frequencies), +4 dB OK [U] (changed 2026-10-13, see the tuning log) |
| Consistency | phrase loudness spread ≤ 2 LU after riding [U] |
| Noise | raw < -60 dBFS, processed < -70 dBFS [U] |
| Clipping | nothing at or above -0.1 dBFS in the raw take |
| Intelligibility | later: speech recognition on the dry vocal (Whisper struggles with singing, 20-40% error on mixes [S]) |

## 10. How it's built (2026-10-13)

`arrange/vocals.py`, step by step: `Take.from_recording` (latency subtracted) → `score_take` per line →
`comp` (best take per line, cut at the quietest 5 ms before the line, 5 ms crossfades) → `clean` (high-pass
at 0.7 × the lowest note, noisereduce with the count-in as the noise profile at about 8 dB, plosive fix) →
`correct` (DIO + StoneMask voicing for onsets, because Harvest's voicing starts 20-150 ms early on
synthetic singing; Harvest pitch values for resynthesis; per sung passage: CheapTrick + D4C, a
piecewise-linear time map from the onset corrections, `pitch_curve`, WORLD synthesis for voiced frames and
the time-mapped original for consonants and breaths) → `tame_breaths` → `chain` → `sit_in_song`
(the vocal's loudness set against the music's while you sing) → `quality`. The Mix tab then treats the
result as a stem ("Your vocals"), so it can be turned up, down or off and re-saved.

## 11. Voice characters and vocal tracks (2026-10-13)

One singer (you) plays every part. Research (web search, 2026-10-13):
- **What makes a voice read as female or male is mostly the formants, not the pitch** [V]: Praat's "change
  gender" uses a formant ratio of about 1.1 (and 1/1.1 back) [S]; patents and vendors use 15-20% [S].
  https://www.fon.hum.uva.nl/praat/manual/Sound__Change_gender___.html ·
  https://voxbooster.com/blog/male-to-female-voice-changer-tutorial/ ·
  https://unison.audio/formant-shifting/
- **Plain pitch shifting moves the formants too** (the chipmunk sound), so shift formants separately and
  start small [V]. https://www.sageaudio.com/articles/top-7-vocal-formant-and-pitch-techniques ·
  https://emastered.com/blog/formant-shifting
- **WORLD separates pitch, envelope and aperiodicity**, so each can be changed alone; whisper = the envelope
  driven by noise instead of a pitched source; breathiness = more aperiodicity (can sound like added
  noise if overdone); re-running WORLD on processed audio adds artifacts [V/S].
  https://arxiv.org/pdf/2208.07282 · https://assets.amazon.science/05/f9/42b2258b4e16ae4d5c1866e7209f/voice-conversion-for-whispered-speech-synthesis.pdf ·
  https://dev.to/orca_forge/learning-from-failure-why-couldnt-breathiness-be-an-independent-parameter-1i64
- **Width comes from separate real takes**, not copies (copies just get louder or phase); 2-4 unison takes,
  doubles panned out, the lead in the centre, octave layers for size; high-pass gang and backing vocals
  [V]. https://violetrecording.com/how-to-double-track-vocals/ · https://www.sageaudio.com/articles/how-to-stack-vocals ·
  https://blog.soundtrap.com/vocal-layering/ · https://violetrecording.com/how-to-layer-vocals/
- **Phone / PA voice**: 300-3400 Hz band-pass (24 dB/octave), a lift near 1 kHz, light distortion after the
  EQ, level-matched [V]. https://voxbooster.com/blog/telephone-voice-effect ·
  https://www.pastpaperhero.com/resources/edexcel-a-level-music-technology-9mt0-effects-processing-telephone-effect
- **Vocal chops**: formant-shift rather than pitch-shift to avoid the chipmunk sound; hard consonants work
  as percussion [S]. https://blog.native-instruments.com/vocal-chops/

What `vocals.CHARACTERS` does (all values [U] starting points, tune by ear):

| Character | How |
|---|---|
| Female lead | an octave up (stays in key) + formants ×1.17 + a little breath |
| Female, same octave (alto) | formants ×1.15 |
| Deeper male | formants ×0.88 |
| Male, an octave down | octave down + formants ×0.92 |
| Younger / brighter | formants ×1.08 |
| Raspy | aperiodicity bursts above 600 Hz, slight pitch jitter, saturation |
| Breathy | aperiodicity raised above 1 kHz, +2 dB air |
| Whisper | no pitch at all (noise-driven envelope), formants ×1.05, +3 dB above 4 kHz |
| Gang shout | 5 extra voices: formants 0.90-1.09, ±6 cents, 0-27 ms late, panned wide, -7 dB, saturated, high-passed |
| Choir | 4 extra voices including an octave above and below, panned, high-passed |
| Station announcer | 300-3400 Hz at 24 dB/oct, +4 dB at 1.1 kHz, distortion |

Pitch shifts are whole octaves only, so the melody stays in key with the music. In free singing the
character is applied in the same WORLD pass as the tuning (one pass, fewer artifacts).

**Vocal tracks**: each take belongs to a track (Lead, Rap, Gang, Backing, Harmony, Ad-libs, Announcer,
Whisper). Each track is processed on its own (its own voice and style) and becomes its own part in the
mixer, set against the music at the style's level plus a track offset (Lead/Rap 0, Gang -2, Announcer and
Whisper -4, Backing/Harmony -6, Ad-libs -8 dB). **Gang, Backing and Harmony stack every take**: the newest
take of each section is the centre voice and the others are tuned, high-passed and panned around it.

**Free singing** (no hummed melody): comped per section (newest take), tuned to the *key* (nearest scale
note, natural strength and retune time from the style, ±10 cents left alone); rap, spoken and whispered
sections are not tuned. **Band hits on vocal accents**: the mixer finds the hardest-hit syllables (louder
than the phrase around them and on the 16th grid) and adds drum hits and brass stabs there.

## 12. Voice tweaks and preview (2026-10-13, night)

The user asked for more ways to shape the voice. On the Sing screen, under **Make the vocal**, the
**Voice tweaks** panel adds fine controls on top of the chosen character and style. Only the settings you
move are sent. Everything else keeps the character's and style's own value. Tweaks are remembered per
vocal track (in the browser), so the Rap track can be gritty while the Chorus lead stays clean.
`vocals.TWEAKS`, `clean_tweaks`, `tweak_preset`, `character_spec`:

| Tweak | What it does (values [U], tune by ear) |
|---|---|
| Pitch (notes of the key) | moves every sung note up or down by notes of the key (7 = an octave), so the vocal stays in key with the band; the move is smoothed over 60 ms so glides don't step. A plain semitone shift would put a free-sung vocal out of key (measured on synthetic singing: 57% of frames in D minor after +2 semitones, against 77% after +1 key step and 82% before). |
| Tone | the formant ratio, ±30% (left: bigger and darker; right: smaller and lighter), multiplied onto the character's own |
| Breathiness | soft 1.5-9 kHz noise following the voice's own 1-4 kHz envelope while you sing (no resynthesis); with a tone change or grit it is WORLD's aperiodicity instead |
| Grit / rasp | uneven noise bursts above 600 Hz, a little pitch jitter, up to 0.3 saturation |
| Warmth / drive | the chain's saturation, 0-0.7 |
| Tuning | off (exactly as sung), gentle (50%, 60 ms), tight (95%, 20 ms), robot (hard snap); default = the style's |
| Double | synthetic ADT doubles on every line, from -14 dB (a hint) to -5 dB (thick) |
| Harmony voice | a second you, a third above, a fifth above, a third below, or an octave above or below, following the key note by note (the same scale-step walk as Pitch), 9 ms late, panned left, -6 dB, high-passed at 150 Hz |
| Echo | the delay send (0-0.35) with more feedback as it goes up (0.2-0.55); line-end throws on |
| Space | reverb send 0-0.45, room 0.35-0.9, decay 0.6-3.2 s |
| Effect | old radio (400-3200 Hz, +5 dB at 1.5 kHz, drive 12 dB), megaphone (650-2800 Hz, drive 22 dB), phone call (300-3400 Hz, light drive), robot (ring modulation at 60 Hz plus hard tuning), lo-fi tape (300-4000 Hz band, more saturation); all level-matched |

**Preview** (`vocals.preview`, `POST /api/songs/{id}/vocals/preview`): 8 seconds of your newest take on the
chosen track, from its first sung sound, tuned (untuned for Rap, Announcer, Whisper and rap/spoken
sections), re-voiced with the character and tweaks, with a quick reverb and echo and no band. It takes
a few seconds, so you can try several voices before running the full "Make this vocal track".

**Timing**: until the sync test has run, a take is placed using the browser's own estimate of the
delay (output latency + base latency + the mic's reported latency). Before this, it was placed with no
correction, so booth takes came out a 16th late. Takes recorded on that estimate are re-timed with the
measured value once the sync test has run. The sync test is now on the Make recorder too.

**Capture**: the page records on the audio thread (`capture-worklet.js`, an AudioWorklet), so a busy page
can't drop mic audio; each 2048-sample block is placed by its own time, and any gap is filled with silence
and reported. A sync-test value measured with the old main-thread capture isn't reused.

**Choosing takes and timing (2026-10-14)**: each section of a track uses its newest take unless you pick
another (**Use this one**); the pick is sent as `choice` and the comp uses it. The **Timing** tweak moves
the whole track in ms. Takes recorded before the audio-thread capture can sit 50-220 ms late, varying per
take (measured), and are marked "old recorder". Preview can play any take, optionally over the same
seconds of the band.

## 13. Measured on the user's real takes (2026-10-15): muffled and choppy

The first local session measured "Last Train, First Light" (72 takes on 5 tracks, the built song's vocal
stems) before changing anything. Script-level numbers; listening is the user's call.

**Choppy tuning.** WORLD resynthesis with *no* pitch change (strength 0, which is what tuning "off" still ran)
made the level wobble from -8 to +5 dB between 5 ms frames inside sung notes and roughly doubled the abrupt
(> 6 dB) level jumps: verse 340 → 711, rap 250 → 684, the cleaner chorus 63 → 69. 685 of the verse's 711 were
inside voiced sound, not at consonant edges: the pitch tracker's frame jitter (95th percentile 66-126 cents per
5 ms on these takes) changes WORLD's spectral envelope frame by frame. PSOLA at ratio 1 is exact (0.0 dB change
in every band, max sample difference 0.003); tuned with the soul preset it keeps the take's own number of
jumps (verse 341 vs 332 raw, rap 205 vs 224, chorus 62 vs 53) and tunes as far as WORLD did (frames within 25
cents of the key: 0.59 vs WORLD 0.61 on the verse). After the full chain (compression evens the level) the
old and new renders of the three tracks measure within 2% of each other in level jumps and frame-to-frame
spectral change, so how much better it *sounds* in the finished song is for the user's ears.

**Hidden resynthesis.** Small tweaks re-voiced the whole track with WORLD: Breathiness 15 on the Verse lead,
Pitch -1 and Tone -4 on the Rap. Now pitch moves go through PSOLA and breathiness is shaped noise; only Tone,
Grit, Whisper and the female/male characters still use WORLD (their hints say so).

**Muffled.** Not mainly the processing: WORLD lost under 1 dB per band above 3 kHz, the chain adds presence
and air, and the built stems are brighter than the raw takes. The recordings themselves are dark and uneven:
relative to 200-1000 Hz, the chorus and gang takes sit at -28 dB in 3-6 kHz and -51 to -53 dB in 10-16 kHz (the
verse take: -24 and -39), and those two takes peak at -0.3 dBFS (near clipping) with a strong low end. That
pattern fits singing loud and close into the end of the mic: the QuadCast 2 is a side-address mic (sing into
the side with the logo, 10-20 cm away, not into the top). Also measured: libsndfile's default Vorbis quality
is about 130 kbps; stems and mixes are now written at about 280 kbps.

**Room noise.** The "-49 dBFS room noise" warnings were mostly 43-59 Hz rumble (the low cut removes it) plus the
count-in click bleeding from the headphones (2-8 kHz on the verse take). Noise is now measured above 100 Hz in
the quietest 300 ms of the count-in, which also stops noise reduction from learning the clicks as "noise".

**Tone match (with the reference stems, REFERENCE_ANALYSIS §4).** The processed vocal's air above 10 kHz was
about 10 dB under the nine reference vocals. A tone-match step after the EQ lifts presence (4.5 kHz peak) and air
(11 kHz shelf) toward the references' medians (3-6 kHz −18.4, 10-16 kHz −28.2 dB against 200-1000 Hz), capped at
+4 / +8 dB and keeping 6-10 kHz within 2 dB of the references. It is on by default and has its own switch.

**"Still sounds away from the mic" (same day, after the user listened: the new tuning "definitely sounds better").**
- No room echo to remove: WPE dereverberation (nara_wpe, MIT) changed the takes by under 0.2 dB, so the decay
  after notes is the voice itself. It was uninstalled again.
- The chain was lifting the room between words by 16-19 dB (chorus: 45 → 26 dB under the loudest singing):
  compressor A (peak catcher) about 8 dB, compressor B about 10, because B levelled at the median of the
  singing. B now levels at the 90th percentile, and a **downward expander after compression** ("Silence between
  words": 1:2 below the typical singing level −15 dB, at most 18 dB, 3 ms / 120 ms) turns the room back down.
- **Match EQ** replaces the two-knob tone match: 18 third-octave bands (250 Hz-12.5 kHz) moved 80% of the way
  to the nine reference vocals' median curve (they agree within 1.5-3 dB there), ±6 dB (+8 from 8 kHz),
  smoothed across neighbours. On the three Last Train tracks the largest deviation from the references went
  from 9-11 dB to about 5 dB (what's left at 5-6 kHz comes from saturation and doubles after the EQ).
- The likeliest cause is the mic, not the processing: the chorus and gang takes are dull and mid-heavy with weak
  lows, the signature of singing into the top of a side-address mic (off-axis, which also raises the room by
  about 6 dB relative to the voice). A **mic check** after each take now warns about exactly this; on the user's
  takes it flags the chorus and gang takes and passes the verse and rap ones.

**Every step is switchable and listed.** Voice tweaks have a "Processing" group: raw voice (the takes exactly as
recorded, only level and timing), low cut, noise reduction (off / light / stronger), breaths, de-esser,
compression (off / light / style / strong), brightness (off / style / brighter). After "Make this vocal track"
the result lists every step that ran, in order, with its amount.

**One working version.** Making a vocal track (or taking one out of the song) no longer adds a version each
time: the first change makes a **working version**, later ones update it in place, and **Save as a version**
keeps it under a name; the next change starts a new working version from it.


## 14. A convincing female voice: research and verdict (2026-10-15)

**Why the current one fails.** The "female" character is WORLD with the pitch an octave up and the formants
×1.17. That moves the numbers that separate voices on average, but not what makes a voice sound female:
the source (lighter, breathier phonation, head voice), the vibrato and phrasing, the consonant attack. It
reads as "a guy trying to sound like a girl" because that is what it is.

**What can work: singing voice conversion (SVC)** trained on one real female voice. Options checked for this
PC (Windows, RX 7900 XT, no CUDA) and for licences that allow a commercial game:

| Option | Code / weights | AMD on Windows | Verdict |
|---|---|---|---|
| RVC WebUI | MIT / MIT (base model trained on VCTK) | **DirectML build** (rmvpe.onnx) | first choice |
| Applio (RVC fork) | MIT, commercial use stated | not documented | good UI; maintenance mode |
| Seed-VC (singing mode) | GPL-3.0; archived 2025-11 | CPU only | zero-shot audition tool, not for shipping |
| SoulX-Singer-SVC (2026) | Apache-2.0 (as stated on mirrors) | unknown | watch |
| so-vits-svc / fork | AGPL "academic only" / no AMD on Windows | | avoid |
| DDSP-SVC | MIT, but its NSF-HiFiGAN vocoder is CC BY-NC-SA | | avoid for shipping |

**Where the target voice comes from (legally).** Never a real artist without consent. Options: a consenting
singer (the user's girlfriend, only if she wants to: 15-30 min of dry singing and a short written OK covering
the game and training), or **VocalSet** (CC BY 4.0: 11 female singers, ~10 h, credit required; technique
exercises, so the timbre is generic). M4Singer, GTSinger, CSD, Opencpop are non-commercial; avoid.

**How to sing for it** (practitioner settings, unverified): sing lightly in head voice or falsetto near the
target pitch, then shift 0 to +5 semitones rather than a full octave from chest voice; pitch method RMVPE,
index rate ~0.3, protect ~0.33; record dry.

**Verdict (honest).** Convincing is possible in 2026 with RVC, but only with all three: a model trained on
one real female voice, source singing that is already light and high, and moderate settings. An
octave-shifted chest-voice take through any model still tends to read as male, only less obviously.
If it falls short: Synthesizer V Basic (free, commercial use allowed, each voice's own licence applies),
re-key the female parts into the user's range (or a male/female duet with the girlfriend), or use the
female lines as stacked choir/gang textures where a single convincing voice isn't needed.

**Proposed trial (needs the user's OK: RVC is a separate install, several GB with models).** Train a small
RVC model on VocalSet's female singers, convert one Last Train chorus sung lightly in head voice, and A/B it
against the WORLD character. Sources: github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI,
github.com/IAHispano/Applio, github.com/Plachtaa/seed-vc, zenodo.org/records/1442513 (VocalSet),
github.com/svc-develop-team/so-vits-svc, github.com/openvpi/vocoders.
