# MouthMixer music knowledge: the critic's rulebook

This is the music theory and production knowledge MouthMixer uses to **judge** its own output before
the user hears it (the critic, PLAN.md §7.11) and to **steer** the arranger. It's written as rules the
code can check. Every rule has a reason, a way to measure it and a severity.

**Severity:**
- **REJECT:** fails the candidate outright.
- **PENALTY:** lowers the score; several small problems add up.
- **STYLE:** the rule depends on the style pack (a jazz pack allows what a pop pack penalises). Each pack
  sets its own value or turns the rule off.

The numbers are **starting values**. They are tuned against real results and the user's reactions, and
each change is logged at the bottom of this file.

**Ground truth:** these rules catch *bad* reliably and describe *good* reasonably. They are not taste.
Breaking a rule on purpose can be great; that's why most rules are penalties, not rejects, and why the
user's reactions (the taste model) can outweigh them over time.

---

## Contents

1. Melody
2. Harmony
3. Bass
4. Rhythm and groove
5. Form and energy
6. Arrangement and orchestration
7. Mixing
8. Game music
9. Originality
10. How the critic adds it up
11. Instrument reference (ranges and idioms)
12. Further reading (the sources these rules come from)
13. Tuning log

---

## 1. Melody

What makes a melody good is mostly **shape, memorability and resolution**.

| # | Rule | Why | How it's measured | Start value | Severity |
|---|---|---|---|---|---|
| M1 | **Range fits the role.** | Singable/hummable lines feel natural; huge ranges feel aimless | highest − lowest note of the lead | ≤ 15 semitones per section (an octave + a minor 3rd); ≤ 19 for instrumental leads | PENALTY, REJECT above 24 |
| M2 | **Mostly steps, some leaps.** | Stepwise motion is smooth; leaps give interest. Pop and folk melodies are mostly steps | share of intervals ≤ 2 semitones | 55-85% | PENALTY outside |
| M3 | **Gap-fill:** a leap larger than a 4th is followed by motion in the opposite direction (usually a step) | Listeners expect a large leap to be "filled in" (Meyer, Huron); unfilled leaps sound unfinished | for each leap > 5 semitones, is the next interval opposite in direction? | ≥ 70% of big leaps | PENALTY |
| M4 | **No chains of big leaps in one direction** unless outlining a chord | Sounds random and is hard to follow | 2+ consecutive leaps > 4 semitones, same direction, not chord tones of the current chord | 0 | PENALTY |
| M5 | **Avoid awkward intervals:** augmented 2nd, tritone, major 7th, and leaps over an octave, unless the style uses them | Hard to sing, sound like mistakes in pop | interval classes in the lead | style-set | STYLE |
| M6 | **One climax per phrase or section:** the highest note appears once (or twice), roughly 55-80% of the way through | Gives the melody a direction and a peak; a peak repeated everywhere has no impact | position and count of the max pitch per section | count ≤ 2, position 0.55-0.8 | PENALTY |
| M7 | **A recognisable motif.** A short idea (2-5 notes, its rhythm and contour) that comes back | Memorability comes from repetition | self-similarity of 1-2 bar windows (interval + rhythm) | some window repeats ≥ 2 times per 8 bars | PENALTY if none |
| M8 | **Repetition with variation**, not copy-paste | Too little repetition = no identity; too much = boring | share of bars that exactly repeat an earlier bar | 25-60% exact; plus varied repeats | PENALTY outside |
| M9 | **Phrases have shape:** 2, 4 or 8 bars, often question then answer | Gives breath and structure | phrase lengths from rests/long notes | mostly 2/4/8 bars | PENALTY |
| M10 | **Question-answer:** the first phrase ends unstable (on 2, 5 or 7, over V), the answer ends stable (on 1 or 3, over I) | The "period" form; the strongest sense of completion | scale degree + chord at phrase ends | at least one stable ending per section | PENALTY |
| M11 | **Strong beats mostly on chord tones** | Non-chord tones on strong beats sound like wrong notes unless they're deliberate tensions that resolve | chord-tone share on beats 1 and 3 (with allowed tensions counted per style) | pop ≥ 70%, jazz ≥ 50% (tensions count) | STYLE |
| M12 | **Non-chord tones resolve:** passing tones, neighbours, suspensions and appoggiaturas move by step to a chord tone | Unresolved dissonance sounds like a mistake | each non-chord tone followed by a step to a chord tone | ≥ 80% | PENALTY |
| M13 | **Leading tone and 4th tend to resolve** (7 → 1 up, 4 → 3 down) at cadences | The strongest pull in tonal music | cadence notes | at final cadences | PENALTY |
| M14 | **Rhythmic identity:** the melody reuses a few rhythm cells, not all different | Rhythm is half of memorability | number of distinct 1-beat rhythm cells / total | ≤ 0.5 | PENALTY |
| M15 | **Breathing room:** rests or long notes at least every 2-4 bars | Wall-to-wall notes tire the ear and leave no room for answers | longest run without a rest or a note ≥ 1 beat | ≤ 4 bars | PENALTY |
| M16 | **Note density fits the tempo** | Fast tempos with 16th-note melodies are frantic; slow tempos with whole notes are static | notes per second | about 1.5-5 per second for a lead | STYLE |
| M17 | **Doesn't double the bass in octaves for long** | The two lines merge and lose independence | parallel octave runs between lead and bass | ≤ 2 beats | PENALTY |
| M18 | **Pickups and phrase starts land well:** a phrase starting just before a downbeat (pickup) is fine; starting on a random off-beat in the middle of a bar is not | Unclear phrasing | phrase start positions | — | PENALTY |

**Good-melody signs (bonuses):** a hook that's still recognisable when hummed alone; a contour that's
an arch or a wave; a climax that's also the most rhythmically emphasised note; a motif that comes back
at a different pitch (sequence).

---

## 2. Harmony

| # | Rule | Why | How it's measured | Start value | Severity |
|---|---|---|---|---|---|
| H1 | **No strong-beat clashes between melody and chord:** no minor 2nd or minor 9th between the melody and a chord tone; no natural 11 (perfect 4th) held over a major or dominant chord; no b9 over a major or minor chord | The textbook "avoid notes": they sound wrong, not spicy | interval of each strong-beat melody note against the voiced chord | 0 | **REJECT** (≥ 1 beat long), PENALTY (shorter) |
| H2 | **Functional flow:** tonic → pre-dominant (ii, IV) → dominant (V) → tonic, with common variations | The expected pull in Western tonal music; random order sounds aimless | likelihood of the chord sequence under the style's progression table | above a style threshold | PENALTY |
| H3 | **Cadences at phrase and section ends:** authentic (V-I) at section ends, half (→ V) mid-section, deceptive (V-vi) for "keep going" | Endings create structure | chord pair at each phrase end | each section ends with a cadence (or a loop turnaround) | PENALTY |
| H4 | **Steady harmonic rhythm**, often speeding up toward a cadence | Erratic chord changes feel unsteady | chord change positions | changes on beats 1 or 3, consistent within a section | PENALTY |
| H5 | **No chord change on a weak off-beat**, except as a deliberate anticipation (pushed chord) the style allows | Sounds like a mistake | change positions | style-set | STYLE |
| H6 | **Voice leading:** hold common tones; other voices move by the smallest step | Smooth, professional-sounding chords | total semitone movement between consecutive voicings | ≤ about 7 semitones total for 4 voices, on average | PENALTY |
| H7 | **No parallel 5ths or octaves between outer voices** in jazz, soul and orchestral textures | They thin the sound and stick out | outer voices | 0 | STYLE (off in rock/power-chord packs) |
| H8 | **Low interval limits:** no 3rds below about C3, no 2nds below about C4; wide intervals at the bottom, close at the top | Close intervals low down sound muddy | lowest intervals of each voicing | — | PENALTY, REJECT if extreme |
| H9 | **Chord vocabulary matches the style:** maj7/m7/9ths in city pop and neo-soul; triads and power chords in rock | Style identity | share of chord types | per pack | STYLE |
| H10 | **Colour chords used with intent:** secondary dominants, borrowed chords (iv, bVI, bVII), tritone subs resolve where they should | Spice that doesn't resolve sounds lost | each colour chord followed by its target (or a known substitute) | ≥ 80% | PENALTY |
| H11 | **Not too static and not too busy:** at least 2 chords per 4 bars (unless a modal vamp style), at most 2 chords per beat | Static harmony bores; too fast blurs | changes per bar | style-set | STYLE |
| H12 | **The key is clear** (or the modulation is clear) | Tonal confusion sounds amateur unless intended | key-profile confidence per section | ≥ style threshold | PENALTY |
| H13 | **Modulations are prepared:** by a pivot chord, a dominant of the new key, or a direct jump at a section boundary | Random key changes jar | modulation points | at section boundaries or with a pivot | PENALTY |
| H14 | **Loop turnaround:** the last bar leads back to the first chord (e.g. V or a ii-V into bar 1) | The loop point should feel like "again", not "the end" | last chord → first chord likelihood | high | PENALTY (game loops) |

**Common progressions the packs use** (all generic; nobody owns a progression):
- I-V-vi-IV and its rotations (pop);
- ii-V-I, iii-vi-ii-V (jazz, city pop);
- IVmaj7-V7-iii7-vi7 (common in J-pop and city pop);
- i-bVII-bVI-V (minor, "Andalusian" feel);
- i-iv-v / i-bVI-bIII-bVII (minor pop/rock);
- vamps: Dorian i7-IV7, Mixolydian I-bVII;
- turnarounds: I-vi-ii-V, I-VI7-ii-V, tritone-sub turnaround (I-bIII7-bVI7-bII7).

---

## 3. Bass

| # | Rule | Why | Measure | Start | Severity |
|---|---|---|---|---|---|
| B1 | **Roots (or chord tones) on the downbeat of each chord change** | Defines the harmony | bass note at each change | ≥ 75% root; inversions only with stepwise bass motion | PENALTY |
| B2 | **Inversions have a reason:** they make a stepwise bass line | Random inversions weaken the harmony | inversion followed/preceded by steps | — | PENALTY |
| B3 | **Kick-bass lock:** bass note starts align with kick hits, or the bass deliberately avoids them (fills between) | The core of a tight groove | onset coincidence ± 30 ms | ≥ 60% of kicks have a bass note or the style pattern says otherwise | PENALTY |
| B4 | **Range:** mostly E1-G3 (bass guitar range), centred around A1-D3 | Too low = inaudible rumble; too high = fights the chords | pitch range | — | PENALTY, REJECT if mostly outside |
| B5 | **Approach notes resolve:** chromatic or scale approach notes land on the next chord's root or 5th | Walking-bass logic | — | ≥ 90% | PENALTY |
| B6 | **Bass and lead move in contrary or oblique motion more than parallel** | Independence between the outer voices | motion types | contrary + oblique ≥ 50% | PENALTY |

---

## 4. Rhythm and groove

| # | Rule | Why | Measure | Start | Severity |
|---|---|---|---|---|---|
| R1 | **The beat is clear:** a listener can tap along | Groove needs a clear pulse | beat-tracker confidence on the render | above threshold | REJECT if no clear pulse (except ambient packs) |
| R2 | **Backbeat:** snare (or clap) on 2 and 4 in 4/4 pop/funk/hip-hop; on 3 in half-time | Genre convention | snare positions | style-set | STYLE |
| R3 | **Swing is consistent across parts:** every part swings the same amount | Mixed swing sounds sloppy | swing ratio per part | within ±3% | PENALTY |
| R4 | **Syncopation in the style's range** | Too little = stiff; too much = no pulse | Longuet-Higgins & Lee syncopation score per bar | per pack | STYLE |
| R5 | **Velocity shapes the groove:** accents ~100-120, normal ~70-95, ghost notes ~20-45; hats have an accent pattern | Flat velocity = machine | velocity spread per part | std dev ≥ 8 | PENALTY |
| R6 | **Micro-timing:** small human offsets (±5-15 ms); a laid-back snare (+10-25 ms) in neo-soul/hip-hop; tight in funk | Feel | offsets per part | per pack | STYLE |
| R7 | **Fills at the end of phrases** (last beat or bar of 4/8 bars), bigger before new sections, not under the melody's key notes | Signposts the form | fill positions vs phrase ends and melody | — | PENALTY |
| R8 | **Parts don't all hit together all the time:** some interlock (hats between kicks, guitar on off-beats) | Interlocking parts = groove; everything on the beat = march | onset overlap between parts | overlap ≤ about 60% | PENALTY |
| R9 | **Density matches energy** | Calm cues with busy drums (or the reverse) feel wrong | onsets per bar vs the cue's target energy | — | PENALTY |

---

## 5. Form and energy

| # | Rule | Why | Measure | Start | Severity |
|---|---|---|---|---|---|
| F1 | **Sections contrast:** each new section changes at least 2 of: density, register, instrumentation, harmony, rhythm, dynamics | Without contrast a song is one long section | feature deltas between sections | ≥ 2 changed | PENALTY |
| F2 | **Energy curve has a shape:** builds toward a peak; for loops, the end leads back smoothly to the start energy | Direction keeps attention | RMS + density + register per section | not flat; loop end within reach of start | PENALTY |
| F3 | **No identical 8 bars more than twice in a row** | Fatigue | exact repeats | ≤ 2 | PENALTY |
| F4 | **The hook arrives early:** within the first 8-16 bars in game cues | Players may only hear the first 30 s | first appearance of the main motif | ≤ 16 bars | PENALTY |
| F5 | **Intros are short** in games (2-8 bars) and play once | The loop is what's heard most | intro length | ≤ 8 bars | STYLE |
| F6 | **Section lengths are regular** (4, 8, 16 bars) unless the style uses odd lengths on purpose | Predictability is part of pop/game music | section lengths | — | PENALTY |
| F7 | **Transitions are prepared:** a fill, riser, drop or chord leads into each new section | Abrupt changes sound like edits | something happens in the bar before a boundary | — | PENALTY |

---

## 6. Arrangement and orchestration

| # | Rule | Why | Measure | Start | Severity |
|---|---|---|---|---|---|
| A1 | **One clear foreground:** only one lead at a time; counter-lines move when the lead rests | Two leads compete and both lose | overlapping "lead-like" parts | — | PENALTY |
| A2 | **At most about 3 things competing for attention** at once (lead, a counter-line, a rhythmic hook) | The ear can follow about 3 streams | active foreground parts | ≤ 3 | PENALTY |
| A3 | **Register spacing:** parts sit in different octaves or the arranger separates them; no two sustained parts in the same octave with the same rhythm (unless a deliberate doubling) | Masking: parts in the same space blur | pitch overlap between parts over time | — | PENALTY |
| A4 | **Instrument range and idiom** (see §11): winds breathe, strings don't do piano leaps, guitars play guitar voicings, trumpet range E3-C6 | Unplayable parts sound fake even with good samples | per instrument | — | **REJECT** for out of range, PENALTY for idiom |
| A5 | **Contrast of colour:** lead and chords from different families (e.g. trumpet over Rhodes, not Rhodes over Rhodes in the same octave) | Separation | instrument families by register | — | PENALTY |
| A6 | **Entrances and dropouts:** parts come in and leave at section boundaries, not randomly mid-phrase | Arrangement tells the form | entrance positions | at boundaries | PENALTY |
| A7 | **Textures support, don't distract:** pads, ambience and FX stay below the lead in level and brightness | Background should stay background | level and spectral centroid vs lead | — | PENALTY |
| A8 | **Additions don't bury the user's idea** (PLAN §7.12): the user's melody or beat is the most prominent element in its role | The user's idea is the centre | relative loudness and presence of user-sourced parts | user part prominent in ≥ 80% of its sections | **REJECT** in "mostly mine" mode, PENALTY otherwise |

---

## 7. Mixing

Measured on the rendered audio (and per stem where useful).

| # | Rule | Why | Measure | Start | Severity |
|---|---|---|---|---|---|
| X1 | **No clipping** | Distortion | sample peaks and true peak | true peak ≤ -1 dBTP | **REJECT** |
| X2 | **Loudness target** | Every cue at the same level in game | integrated LUFS | -14 ± 1 LUFS (game cues may sit lower; set per project) | auto-fixed, then checked |
| X3 | **Not over-compressed** | Squashed mixes are tiring, especially on loop | peak-to-loudness ratio (PLR) | ≥ 8 dB | PENALTY |
| X4 | **The melody is audible** | The point of the track | lead stem loudness vs the rest in its band (1-4 kHz) | lead ≥ the strongest other part in that band, in most frames | **REJECT** if buried |
| X5 | **Frequency masking is low** | Clarity | per-band overlap between stems (e.g. 24 critical bands) | below threshold per band; kick vs bass handled by sidechain | PENALTY |
| X6 | **Tonal balance near the style's target** | Too bright = harsh, too dull = muffled, too much low-mid = muddy | long-term average spectrum vs the pack's target curve (overall the slope of commercial mixes falls roughly 3-5 dB per octave) | within ±3 dB per octave band | PENALTY |
| X7 | **Low-mid mud check** (200-500 Hz) | The most common amateur problem | energy in 200-500 Hz relative to neighbours | below threshold | PENALTY |
| X8 | **Harshness check** (2-5 kHz peaks) | Ear fatigue, especially in long loops | peak energy and spectral flatness there | below threshold | PENALTY |
| X9 | **Lows are mono**: below about 120 Hz, the left and right channels match | Phase problems, club/phone translation | low-band side/mid ratio | ≈ 0 | auto-fixed |
| X10 | **Mono compatible** | Phones and some speakers are mono | stereo correlation; level drop when summed to mono | correlation ≥ 0, drop ≤ 3 dB | PENALTY, REJECT if strongly negative |
| X11 | **Phone-speaker translation:** after a ~150 Hz high-pass and small-speaker curve, the bass line and kick are still heard and the lead is still clear | Many players are on phones | bass harmonics present; lead still dominant | — | **REJECT** if the bass disappears |
| X12 | **Reverb doesn't wash out the groove** | Too much reverb blurs rhythm | direct-to-reverb ratio on drums and bass | per pack | PENALTY |
| X13 | **Stereo image is balanced** | Lopsided mixes distract | left/right energy | within ±1.5 dB | PENALTY |

**Production quality models** (rank only, never override a rule): an audio aesthetics model (production
quality, content enjoyment) and a CLAP style-match score.

---

## 8. Game music

| # | Rule | Why | Measure | Start | Severity |
|---|---|---|---|---|---|
| G1 | **Seamless loop:** no click, no gap, reverb tail wrapped into the start, same energy across the loop point | A broken loop is heard every 2 minutes | sample-level discontinuity, RMS jump at the loop point | none | **REJECT** |
| G2 | **Loop length suits the cue:** field 1.5-3 min, battle 1-2 min, menus 0.5-1.5 min, stings 2-6 s | Too short = fatigue; too long = wasted size | length | per cue type | PENALTY |
| G3 | **Listening fatigue:** no piercing repeated high elements, no constant busy lead in field music, vocals rare | Players hear field music for hours | high-frequency energy, lead density | per cue | PENALTY |
| G4 | **Leaves room for dialogue and SFX:** field and menu cues keep the 1-4 kHz band less crowded than a standalone song | UI sounds and text blips live there | band energy | per cue | STYLE |
| G5 | **Mood matches the cue:** energy and brightness targets (calm ↔ intense, sad ↔ happy) | Function first | estimated arousal and valence vs target | within range | PENALTY |
| G6 | **Variants stay compatible:** day/night/battle versions share tempo family, key family, length and form, so the music system can swap at a phrase | The MusicDirector switches without losing its place | metadata comparison | exact for "Var" cues | **REJECT** if mismatched |
| G7 | **Intensity layers** (calm → full → pinch) are the same length and line up | Smooth switching | lengths and bar grid | exact | **REJECT** |

---

## 9. Originality

Covered in PLAN §10. In the critic:
- a **red** result (10+ closely matching notes, 2+ bars, or melody + chords both matching a known song)
  = **REJECT**;
- **amber** = a big PENALTY and a visible flag;
- checked on the user's melody, **every added melody and bass line**, and recognisable riffs;
- the personal danger list (songs the user listens to most) is weighted higher.

---

## 10. How the critic adds it up

1. **Hard rejects first.** Any REJECT → out. Reasons are counted for the "made 30, rejected 19 because..."
   line.
2. **Section scores** (each 0-1) from the PENALTY and STYLE rules in that section:
   melody, harmony, bass, rhythm, form, arrangement, mix, game fit.
3. **Weighted total** with weights per style pack (a groove pack weights rhythm higher; a ballad weights
   melody and harmony). Default weights: melody 0.20, harmony 0.15, bass 0.08, rhythm 0.15, form 0.10,
   arrangement 0.12, mix 0.12, game fit 0.08.
4. **Listening models** add a small bonus (style match, production quality).
5. **Taste model:** trained on the user's reactions and A/B picks (a pairwise model such as
   Bradley-Terry over the features above). Its weight grows with the number of reactions, from 0 up to
   about 0.5 of the total.
6. **Pick 3 that differ:** best first, then the best one that differs meaningfully from it (chords,
   instruments or feel), and so on.
7. **Nothing good enough?** If even the best is below the pack's minimum, show nothing and ask a question
   ("this melody is hard to harmonise in city pop; try neon night, or allow jazzier chords?").

---

## 11. Instrument reference (ranges and idioms)

Written pitch ranges, comfortable part in brackets. Middle C = C4.

| Instrument | Range | Comfortable | Idiom notes |
|---|---|---|---|
| Electric bass / finger bass | E1-G3 | A1-D3 | octave pops, ghost notes, slides; no chords |
| Upright bass | E1-D3 | G1-C3 | walking quarters, slower lines |
| Synth bass / 808 | C1-C3 | — | long glides OK; keep the fundamental audible on phones (add harmonics) |
| Rhodes / Wurlitzer | E1-E7 (73-key) | C3-C6 | rootless voicings, comping on off-beats, tremolo; avoid dense low clusters |
| Acoustic piano | A0-C8 | — | anything, but voicing rules (H8) still apply |
| Clean electric guitar | E2-E6 | — | chord shapes (max 6 notes, stretch limits), muted 16th cutting, double-stops |
| Overdriven guitar | E2-E6 | — | power chords and riffs; avoid full extended chords (they turn to mush with distortion) |
| Trumpet / muted trumpet | E3-C6 | G3-G5 | needs breaths (rest every 2-4 bars); fast wide leaps are hard |
| Flugelhorn | E3-B5 | G3-F5 | warm, slower lines |
| Trombone | E2-F5 | A2-D5 | slides; slow chromatic lines |
| Saxophone (alto) | Db3-Ab5 (sounding) | — | **avoided as lead in battle packs** (originality house rule) |
| Flute | C4-C7 | D4-A6 | breaths; light, airy; weak low register |
| Clarinet | D3-Bb6 (sounding) | — | breaths; warm low register |
| Violin | G3-E7 | G3-A6 | long lines, no piano-style leaps across many strings fast |
| Cello | C2-A5 | C2-E5 | singing middle register; slow leaps |
| Strings section (pad) | C2-C7 | — | sustained voicings, swells |
| Celesta / glockenspiel / music box | C4-C8 | — | short sparkly notes, high register only |
| Vibraphone | F3-F6 | — | 4-mallet voicings max 4 notes, soft dynamics |
| Choir pad | C3-C6 | — | sustained vowels, slow harmony |
| Chiptune pulse / square | any | — | arpeggios instead of chords, fast runs fine |

---

## 12. Further reading (the sources these rules come from)

- **Harmony and voice leading:** Kostka & Payne, *Tonal Harmony*; Aldwell & Schachter, *Harmony and
  Voice Leading*.
- **Jazz harmony, voicings, tensions, substitutions:** Mark Levine, *The Jazz Theory Book* and
  *The Jazz Piano Book*.
- **Pop harmony and melody statistics:** Hooktheory's *Hooktheory I & II* and its chord-progression data.
- **Form (sentence, period, phrase):** William Caplin, *Classical Form*; for songs, Jack Perricone,
  *Melody in Songwriting*.
- **Expectation, gap-fill, why melodies work:** David Huron, *Sweet Anticipation*; Leonard Meyer,
  *Emotion and Meaning in Music*; David Temperley, *Music and Probability* (key-finding profiles).
- **Rhythm and syncopation:** Longuet-Higgins & Lee's syncopation measure; Witek et al. on syncopation
  and groove.
- **Orchestration and ranges:** Samuel Adler, *The Study of Orchestration*.
- **Mixing:** Mike Senior, *Mixing Secrets for the Small Studio*; Bob Katz, *Mastering Audio* (loudness,
  dynamics); EBU R128 / ITU-R BS.1770 for loudness measurement.
- **Game music:** Winifred Phillips, *A Composer's Guide to Game Music*; Karen Collins, *Game Sound*.

---

## 13. Tuning log

Every change to a rule's value or severity is logged here with the reason (for example "M2 range widened
to 50-85%: the user loved three options that were rejected for leaps").

| Date | Rule | Change | Why |
|---|---|---|---|
| 2026-10-12 | all | first version | written from the sources in §12 |
