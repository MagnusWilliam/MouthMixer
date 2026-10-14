# Arranging with layers: the rules MouthMixer follows

How a song gets full without getting cluttered: layer roles, register slots, rhythmic interlock, timbre
pairings, mood palettes, ear candy, and vertical layering for games. These rules drive the arranger, the
mixer's suggestions (`arrange/catalog.py`) and the critic.

**How this was researched (2026-10-12):** web search across orchestration texts (Rimsky-Korsakov's
*Principles of Orchestration*), mixing and arranging writers (Mike Senior / Sound On Sound, FabFilter,
Audient, Premier Guitar), music cognition (Bregman's auditory scene analysis, Huron's *Tone and Voice*,
Plomp & Levelt, Juslin & Lindström) and game-audio sources (CRI, Game Developer, bugnet). Page fetches were
blocked by the build machine's proxy, so **[S]** claims rest on search-result excerpts of the cited pages;
**[C]** marks standard arranging convention that wasn't checked against a page. [C] values are starting
defaults: tune them with the user's ears and log changes in MUSIC_KNOWLEDGE.md §13.

---

## 1. Layer roles and density

Roles (one part per role per section): **foundation** (bass/sub), **rhythm** (drums + a percussion topper),
**harmony** (pad, comping keys or guitar), **lead** (your melody), **counter-melody**, **ear candy /
texture** (FX, risers, arpeggios). Incredibox groups its loops the same way (beats, effects, melodies,
voices) and designs every loop to interlock so any combination works. [S]
https://en.wikipedia.org/wiki/Incredibox

- **R1.1 Three things up front.** Listeners follow about three foreground streams; pass the spotlight
  instead of stacking (Walter Murch's "no more than 3 foreground streams", echoed by Mike Senior). [S]
  https://cloud.wikis.utexas.edu/wiki/spaces/rtf318/pages/80022410 — *Encoded:* at most 3 foreground roles
  (lead, counter, a rhythmic hook); total active parts 2-3 sparse, 4-5 normal, 6-7 climax, warn above 7. [C]
- **R1.2 Every new part needs a job** (a new idea, more energy, or contrast), not "it feels empty". [S]
  https://drolez.com/blog/music/loop-to-track-reference-structure.php
- **R1.3 Arrangement masking beats EQ.** Two parts in the same register *and* the same rhythmic job mask
  each other (a guitar and an arp both on 16ths): mute one. [S]
  https://mastering.com/subtractive-production-the-power-of-muting-for-a-professional-sound/ — *Encoded:*
  suggestions are penalised for a role already playing; the mixer warns on same role + register + grid.
- **R1.4 Build the climax first, subtract for the other sections.** [S] drolez
- **R1.5 Energy in waves**, each peak higher; after a peak, strip to one element for about 4 bars. [S]
  drolez; https://deviantnoise.net/education/music-production/arrangement/
- **R1.6 Novelty decays.** Copy-pasted loops feel saturated yet empty; when a part enters, drop an old one;
  change at least one layer every 4-8 bars. [S] https://www.soundonsound.com/techniques/mix-rescue-strong-arrangements
- **R1.7 Section templates.** Intro: pad + texture or drums alone. A: bass + drums + harmony + lead. B:
  add a riser and a percussion topper, thin the last 1-2 bars. Climax: everything, lead doubled an octave
  up. Breakdown: pad + lead. Outro: remove in reverse order of entry. [C]
- **R1.8 Distinct identity.** Many similar synth layers blur into "an indistinct mass": emphasise what
  makes each part unique. [S] https://discussion.cambridge-mt.com/printthread.php?tid=289

## 2. Register and frequency slots

- **Streaming (Bregman):** two lines separate more easily the further apart in pitch and the faster they
  move; the two trade off, so a fast part needs less register gap than a slow one. [S]
  https://en.wikipedia.org/wiki/Auditory_scene_analysis
- **Huron, *Tone and Voice* (2001):** voice-leading rules follow from toneness, temporal continuity,
  minimum masking, tonal fusion, pitch proximity and co-modulation; spread energy evenly across critical
  bands (which are wider in the bass); unison, octave and fifth fuse most. [S] https://muse.jhu.edu/book/47915
- **Spacing:** composers use wider intervals in the bass; close intervals low down fall inside one
  critical band and sound rough (Plomp & Levelt 1965). [S]
  https://www.math.miami.edu/~armstrong/592sp15/Plomp_Levelt_1965.pdf
- **R2.1** Below MIDI 48 (C3): octaves and fifths only; 48-55: thirds and wider; seconds only above ~60.
  [C, approximating low-interval limits] — already enforced by `theory.voice` (MUSIC_KNOWLEDGE H8).
- **R2.2 Bands:** 20-50 Hz felt more than heard; kick and bass fundamentals meet at 50-125 Hz; 250-500 Hz
  turns muddy; harshness at 2.5-4 kHz. [S] https://www.fabfilter.com/learn/equalization/frequency-range-characteristics/
- **R2.3 Pads stay out of the lead's way:** arrange around the clash first (drop the pad while the lead is
  busy), then high-pass and dip the pad around 1-4 kHz. Thin-and-bright over warm is complementary; two
  warm sounds in one register compete. [S] https://beatkitchen.io/guides/electronic-music/07-sound-selection/
- **R2.4** High-pass everything but bass and kick (ear candy ~50-60 Hz, pads/keys 120-200 Hz, leads
  150-250 Hz). [S/C] https://audient.com/tutorial/ear-candy-production-tips/ — *Encoded* in `render._fx`.
- **R2.5 One sub owner:** only the bass or 808 lives below ~80 Hz; sidechain it to the kick. [S] —
  *Encoded:* bass parts "replace" each other in the mixer; sidechain in `render`.

| Role | MIDI | Notes |
|---|---|---|
| Sub / bass | 28-52 | fundamentals mostly 40-120 Hz |
| Harmony / pad body | 48-72 | |
| Lead (sung or hummed) | 55-84 | |
| Counter-melody | an octave below the lead (48-67) or a 3rd-6th above in another colour | |
| Sparkle (glock, celesta, bells) | 72-108 | |
| Shaker / hats | unpitched | energy 6-12 kHz |

- **R2.6 Octave doubling for clarity** (flute an octave above violin is the classic); literal unison
  doubling of everything sounds "heavy and gray" (Belkin). [S] https://alanbelkinmusic.com/orchestration-basic-notions-pt-2/
- **R2.7** Don't split a sampled section into octaves without another colour reinforcing it
  (Rimsky-Korsakov). [S] https://www.gutenberg.org/files/33900/33900-h/33900-h.htm

## 3. Rhythmic complementarity

- **R3.1 Busy against sustained:** of two parts sharing a register, one moves and one holds. A long held
  note is the counter-melody's window. [S] https://violetrecording.com/what-is-a-countermelody/ —
  *Encoded* in the "answer phrases" generator.
- **R3.2 Interlock (the funk jigsaw):** guitar stabs on the upbeats between drum and bass hits; bass and
  guitar "teeter-totter". [S] https://www.premierguitar.com/lessons/digging-deeper-developing-a-funk-guitar-orchestra
- **R3.3 Call and response:** two bars of rest, two of melody. [S] Premier Guitar
- **R3.4 Contrary motion**, consonant intervals on strong beats, no parallel fifths/octaves against the lead
  (they fuse). [S] counter-melody sources
- **R3.5** One part holds the grid; at most one or two syncopated layers against it. [C]
- **R3.6 Hat rolls** at phrase ends, after a bar or two of plain hats. [S] https://emastered.com/blog/trap-drum-patterns
- **R3.7 Builds** shorten the gaps between snare hits (8ths → 16ths → 32nds). [S] drolez

## 4. Timbre pairings (used for "goes well with…" suggestions)

Rimsky-Korsakov: violin + trumpet, viola + horn, cello + horn blend; brass doubled by woodwinds in pairs
gives a "magnificent and uniform tone"; mixed woodwinds in octaves are "not to be recommended" without
strings. Celesta and glockenspiel double a melody's important notes but never carry it alone. [S]

1. Flute + violin (unison or octave above): brightens and lifts a melody. [S]
2. Horn + cello: soft, blended, warm tenor line. [S]
3. Horn + viola: an even middle. [S]
4. Trumpet + violin: brilliant edge. [S]
5. Brass chords + woodwinds in pairs: uniform tutti. [S]
6. Celesta/glockenspiel + flute or harp, an octave up: sparkle on a clear carrier. [S]
7. Horn + celesta in high octaves (*Boléro*): a new fused colour. [S]
8. Piano + string pad: attack plus sustain. [C]
9. Pluck + pad: short over long. [S]
10. Rhodes + muted trumpet: mellow cool-jazz colour. [C]
11. Rhodes + upright bass + brushes: the jazz trio blend. [C]
12. Lo-fi Rhodes/piano + muffled drums + vinyl: the lo-fi sound. [S] https://splice.com/blog/lo-fi-hip-hop-beat-10-minutes
13. Acoustic guitar + shaker. [C]
14. 808 + hi-hat rolls: extreme register and density separation. [S]
15. 808 + kick on the same hits: they read as one instrument. [S]
16. Brass stabs + funk guitar offbeats: interlock. [S]
17. Funk guitar + slap/synth bass ("teeter-totter"). [S]
18. Harp + flute: pastoral, fantasy. [C]
19. Pizzicato + bassoon/clarinet: whimsical, "sneaky". [C]
20. Marimba + pan flute / steel drum: tropical. [S]
21. Ukulele + glockenspiel + light percussion: cozy (cf. Animal Crossing's band). [S partly]
22. Accordion + acoustic guitar: town / folk warmth. [C]
23. Spiccato strings + low brass + taiko: epic. [S] https://shockwave-sound.com/browse/production-type/epic-trailers
24. Choir pad + strings: epic or sad bed. [C]
25. Piano + cello: sad duo in different registers. [S]
26. Synth pad + arpeggio + gated snare: synthwave. [S] https://violetrecording.com/how-to-make-synthwave/
27. Pulse lead + triangle bass + noise drums + fast arpeggios: chiptune. [S]
28. Low drone + sparse high bell / music box: eerie. [C]
29. Tremolo strings + prepared piano: horror. [S] https://www.clrn.org/how-to-make-scary-music/
30. Shimmer pad + soft piano: dreamy. [S]
31. Organ + Rhodes or guitar: gospel / soul bed. [C]
32. Vibraphone + upright bass: smooth jazz, noir. [C]
33. Distorted riff + synth bass + driving drums: battle (bass doubles the riff an octave down). [C]
34. Lead + itself an octave up at -10 dB: chorus lift. [S]
35. Legato strings + woodwinds at the octave: soft and warm. [S]
36. Clap/snare + tambourine on 2 and 4: brighter backbeat. [C]

**Avoid:** two warm sounds holding chords in one register (pad + Rhodes at C3-C5); two parts with the
same rhythm, register and job; glockenspiel or celesta alone on the melody; two subs at once; unison
doubling of everything; two different melodies in one octave in different leads; heavy reverb on bass.

## 5. Mood palettes ("what kind of sound are you going for?")

Juslin & Lindström (2010): musical cues add up, predicting 77-92% of listeners' emotion ratings; importance
runs mode > tempo > register > dynamics > articulation > timbre. Major reads positive, minor negative;
loud/high/fast reads high-arousal; slow/soft reads sad or tender. [S] https://pmc.ncbi.nlm.nih.gov/articles/PMC3726864/

| Vibe | Instruments | BPM | Chords | Feel | Production |
|---|---|---|---|---|---|
| Chill / lo-fi | Rhodes or piano, muted bass, dusty drums, soft guitar, vinyl | 70-90 [S] | maj7, m7, 9ths, 2-4 chord loops [S] | swung, laid back [S] | tape, wow/flutter, low-pass, crackle [S] |
| Epic | spiccato strings, low brass, horns, taiko, choir, impacts | 100-120 [S] | minor, i-VI-III-VII | driving ostinato | big hall [S] |
| Cozy | ukulele, guitar, pizzicato, glock/celesta, accordion, clarinet, upright | 90-120 | major, add6/add9 | bouncy | small room, dry |
| Dark / mysterious | low pads, harp/celesta motifs, low clarinet, sparse piano, drones | 60-90 | minor, m(add9), Dorian/Phrygian | sparse | long dark reverb |
| Eerie | drones, tremolo strings, prepared piano, reversed sounds [S] | free/slow | clusters, unresolved [S] | irregular | huge reverb, silence [S] |
| Battle | driving drums, distorted guitar/synth bass, brass stabs, ostinato, arps | 140-180 | minor, i-bVI-bVII | 16th drive | saturation, tight reverb |
| Retro / arcade | pulse lead, triangle bass, noise drums [S] | 120-160 | chords as fast arpeggios [S] | straight 16ths | dry, echo by delayed copies [S] |
| Jazzy | Rhodes, upright, brushes, vibes, muted trumpet | 80-140 swing | ii-V-I, 9/11/13 | swing, walking bass | plate/room |
| Sad | solo piano, cello, quartet, soft pad [S] | 55-75 [S] | minor, vi-IV-I-V, suspensions | rubato | big warm hall |
| Dreamy | shimmer pads, felt piano, bells, delayed guitar | 60-90 | maj7, add9, sus2, slow changes [S] | long notes | long modulated reverb [S] |
| Groovy / funky | slap or synth bass, chicken-scratch guitar, clav, brass stabs | 95-115 | dom7/9/13, m7 vamps | 16th interlock [S] | dry, compressed |
| Tropical | marimba, steel pan, pan flute, plucks, light four-on-the-floor [S] | 100-115 [S] | major, add9 | off-beat plucks | bright |

## 6. Ear candy (when and how much)

- **Risers** 1-4 bars, only into a louder section, one per transition; **impact** on the downbeat after. [S]
  https://audient.com/tutorial/ear-candy-production-tips/
- **Reverse cymbal / reverse reverb** 1 bar (or 2 beats) before a section. [S]
- **Fills** as their own element on the last beat/bar of a 4- or 8-bar phrase; bigger at section ends. [S/C]
- **Drop-outs:** one element alone for up to 4 bars, or one beat of silence before a downbeat. [S]
- **Toppers** (shaker, tambourine, ride) in B and climax sections. [C]
- **Octave doubler** on the lead in the climax only. [S]
- **Sub layer** in choruses, saturated so phones hear it. [S]
- **Counter-melodies** from the second statement on, not the first. [C]
- Cap: about one ear-candy event per 2 bars outside transitions; high-pass all of it. [C]

## 7. Vertical layering for games (the mixer works this way)

- Synchronised stems share tempo, key and timeline and fade in and out to change intensity; they always
  run together, even muted. [S] https://blog.criware.com/index.php/2020/04/20/dynamic-music-with-adx2-part1-vertical-layering/
- **Every combination must sound good:** each layer is a complete musical thought; the bass or harmony
  layer carries the chord roots. [S] https://www.departuremusic.com/adaptive-music-implementation-indie/
- Toggles land on the next bar (or phrase), with a 1-beat to 1-bar fade. [S] https://bugnet.io/blog/adaptive-music-a-beginners-guide
- Seamless loops: fold the reverb tail of the end back onto the start; loop points on bar lines. [S]
  https://bugnet.io/blog/how-to-loop-game-music-without-pops
- Avoid heavy master processing on stems; process per bus. [S]
- Loop lengths 2, 4 or 8 bars; layers ordered texture < harmony < rhythm < counter < toppers so one
  "energy" control maps onto them. [C]

## 8. What MouthMixer encodes today

- Suggestions (`catalog.suggest`): vibe match, research pairings (§4), empty registers or missing rhythm
  (§1, §2), and a penalty for a role that's already playing (R1.3, R1.1).
- Generators: answer phrases in rests and long notes (R3.1, R3.3), octave doubles (R2.6), risers and hits
  into sections (§6), percussion toppers, interlocking stabs and off-beat chops (R3.2).
- Not yet: the 7-part clutter warning in the UI, R1.6's "drop an old part when a new one enters"
  automation, per-subset layer testing for game loops (§7), and loop rendering with folded tails.


## Making brass sound played (2026-10-14)

The user found the trumpets flat. Brass and saxophones (`render.PLAYED`) now get what players do and
sample playback doesn't (all values [U], tune by ear):

- **Scoop:** each phrase start begins 40 cents flat and rises to pitch over 60 ms (pitch bend).
- **Delayed vibrato:** on notes of half a second or more, 5.4 Hz vibrato starts after a quarter of the
  note and grows to about ±18 cents (measured on a rendered trumpet: ~30 cents flat at the attack, ~37
  cents peak-to-peak in the held part; a piano stays within 2).
- **Phrase shape:** the first note and the top note of each phrase are leaned on (+6 / +8 velocity), a
  short last note is lighter (-8). Velocity also changes the sample layer, so this changes the tone too.
- **A second player** on single lines (trumpet, trombone, muted trumpet, saxes): the same part 7 cents sharp
  and 14 ms late, 5 dB down, the two spread left and right. Chord stabs aren't doubled.
- **EQ:** -2.5 dB at 380 Hz (boxiness), light saturation for bite, +2 dB shelf above 7 kHz.

Fills no longer land in breakdowns (the drums are out) or build-ups (they have their own snare roll).
