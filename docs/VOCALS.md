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
- **Noise reduction:** spectral gating with the profile taken from the pre-roll, at most 6-10 dB, skipped
  when the noise floor is already under -65 dBFS; heavier settings cause "musical noise". [V/U]
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

**How:** the WORLD vocoder (pyworld: harvest, cheaptrick, d4c) changes pitch with the spectral envelope kept,
so the voice keeps its character (formants) [S]. WORLD can buzz in unvoiced sounds, so only voiced frames are
resynthesised and the original is crossfaded back in for consonants and breaths [U].

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
