# Producing a Persona-style song: the blueprint (2026-10-15)

Everything learned before producing the first "real" base track for *Last Train, First Light*: five
YouTube tutorials (transcripts and screenshots), the ATLUS sound-sources sheet, and the nine analysed
reference songs ([`REFERENCE_ANALYSIS.md`](REFERENCE_ANALYSIS.md)). Techniques and tendencies only: no
melody, riff or lyric is copied from Atlus or the video creators (PLAN §8.3, §10).

Sources:
- Videos: Shady Cicada "How to Give Your Song Persona Vibes" (4j0xpJulLVI); Duane "How I Made Music Like
  Persona" (DQLHOrU-Yvw); MineFormer "Composing in the style of Persona 5" (ia1COXiyPXQ, on-screen only);
  zuriel "How To Make A Chill Persona Soundtrack" (KM4NEyxvsII); FnaskiTalks "Why Persona's Music Just Hits
  Different" (5bXPMy69HPw, essay).
- ATLUS Sound Resource Spreadsheet (VGM Resources community; Persona tab).

## 1. The Persona 5 band (what Atlus used, and our free stand-ins)

| Role | Atlus (sheet / MineFormer) | Free stand-in (licence) |
|---|---|---|
| Bass | Spectrasonics Trilian "Clean Fender - Full Range", "used throughout" | Karoryfer Black And Blue Basses fingered (CC0) or FreePats Finger Bass (CC0) |
| Rhodes | Scarbee Mark I, "Pan Cake Kore" (auto-pan, chorus, amp, no distortion), "used throughout" | jRhodes3d, a 1977 Mark I (music made with it is yours; samples not redistributable) + our auto-pan/chorus/amp |
| Drums | BFD3 (room mics up, snare and hats well under the kick) | MuldjordKit (CC-BY 4.0: credit DrumGizmo) |
| Loops / percussion | Stylus RMX: "Festivo", congas, "Ice Brushes" triangle (Last Surprise, Tokyo Daylight) | VCSL congas, bongos, tambourine, shakers, triangle (CC0), played as patterns |
| Organ | NI Vintage Organs B3 "Gimme Some Lovin" / jazz; percussion 3rd, slow Leslie | our tonewheel organ (`synths.organ`) |
| Strings | live strings; Spitfire Chamber Strings disco falls and staccato | Virtual Playing Orchestra strings (commercial music allowed) + a fall at phrase ends |
| Brass / sax | AMG Kick-Ass Brass trumpet; live sax | VPO trumpets/trombones; FreePats tenor sax (CC0) |
| Guitar | Stratocaster through Guitar Rig | FreePats FSBS clean electric (CC0), double-tracked L/R |
| Piano | NI New York Concert Grand | Salamander Grand V3 (CC-BY 3.0) |
| Synth leads (P3/P5 boss) | Massive, Logic ES2 | our analog synth (`synths.synth`) |

Persona 3 (and Reload) swaps the jazz-funk band for hip-hop drums (Best Service Dance Mega Drums loops),
synths and strings; Persona 4 is bright J-pop/rock; Persona 5 is acid jazz (FnaskiTalks: one genre identity
per game).

## 2. Rules (ranked; video sources in brackets)

**Sound**
1. The Rhodes is the signature: comping and lead, auto-pan + chorus + light amp, velocity for mellow (soft)
   or grit (hard) [Shady Cicada, MineFormer].
2. A clean Fender finger bass that keeps moving: octave jumps, muted/open alternation, root-5-8 runs, lock
   the roots to the chord hits and fill before every change [MineFormer, Shady Cicada, Duane]. Double it on
   the Rhodes at two octaves in intros [MineFormer].
3. A roomy live kit with snare and hats well under the kick, plus congas and a constant brushed triangle;
   "just adding a conga groove elevates the feel" [MineFormer]. A layered electronic kit for punch, OTT-style
   drum bus compression [Shady Cicada].
4. Strings: disco falls and staccato stabs on accents; double the vocal in the chorus [MineFormer, Duane].
5. Brass: staccato/marcato stabs, held back until the chorus [Shady Cicada, Duane].
6. Organ: percussion (3rd, fast), slow Leslie; comping with upper structures [MineFormer, zuriel].
7. Clean Strat, simple parts, doubled hard left and right [MineFormer, Shady Cicada].

**Harmony**
8. Extended chords with seconds inside the voicing ("dissonant in the right place, somber but chill")
   [Shady Cicada]; m9/m11 clusters over the root [zuriel].
9. Minor i-bVII-bVI, iv7 into a dominant V7 (harmonic minor) or an altered V7(#5#9) turnaround [Duane, zuriel];
   from our references: bIIImaj7, bVImaj7, v7, the Neapolitan bIImaj7 (REFERENCE_ANALYSIS §3).
10. Comping parts play only upper extensions (no root or third): organ plays a C#m7 shape over F#m11 [zuriel].

**Rhythm and form**
11. 110-140 BPM for the funk/acid-jazz themes (MineFormer's demo 112, Shady Cicada 138, Duane 117; our
    references 95-120 + It's Going Down Now's 167); straight 16ths with a swung lane for jazzier cues.
12. Drum grids: offbeat hats, snare 2 and 4, busy syncopated kick, crash pushes on the "and" of 2/4, a
    descending 16th tom fill every second bar [Duane]; disco 8th hats [Shady Cicada].
13. Verses lean and narrow, choruses wide and full (references: "other" stems 13 dB down and width -13 dB in
    verses, up and -8 dB in choruses).
14. Layers enter one at a time: bass, Rhodes, loop + kit, congas, triangle, organ, strings, guitars
    [MineFormer]; a reverse cymbal into a boom at every section change [Shady Cicada].
15. One short riff/title motif reused across the song (and the game) [FnaskiTalks]; the finale restates the
    opening hook with strings added [Shady Cicada]; an outro that repeats the intro over the chorus groove [Duane].
16. Vocals sit inside the band, with long instrumental riff sections between [FnaskiTalks].

**Mix (REFERENCE_ANALYSIS §3-4)**
17. Width side/mid about -9 dB (ours was -16.6); low-mids at most about -9 dB of the energy; vocal about 5 dB
    over the band at 1-4 kHz; references master around -10 LUFS (we keep -14 for the game and give a loud
    listening master too).

## 3. Last Train, First Light: the plan for the base

Main theme / opening, rap verse plus a contrasting chorus voice: the shape of P5's "Wake Up, Get Up, Get Out
There" and P3's "Burn My Dread". Kept from the current song so the lyrics and takes still line up: 126 BPM,
D minor, the 92-bar layout below.

| Bars | Section | Chords (one per bar unless split) | Band |
|---|---|---|---|
| 1-8 | Intro | Dm9, Bbmaj7, Gm9, A7#5#9 (x2) | station chime motif; bass + Rhodes doubling (bars 1-4), kit + congas + triangle enter bar 5; reverse cymbal into bar 9 |
| 9-16 | Verse 1 | Dm9, Dm9, Bbmaj7, A7sus4-A7, Dm9, Dm9, Gm9, C9 | lean and narrow: kit, busy bass, sparse Rhodes stabs, triangle |
| 17-24 | Pre-chorus | Bbmaj7, C6/9, Am7, Dm9, Bbmaj7, C, Ebmaj7 (bII), A7#5#9 | strings rise, organ pad, snare build, freeze on "here we go!" |
| 25-40 | Chorus | Bbmaj7, C7, Am7, Dm9, Bbmaj7, C7, Fmaj7-Am7/E, Dm9; Gm9, C7, Fmaj7, Bbmaj7, Gm9, Ebmaj7, Asus4, A7alt | full and wide: organ, strings (falls), brass stabs on "Ride, ride, ride", guitars L/R, congas |
| 41-48 | Chorus instrumental | first 8 chorus chords | sax plays the hook motif, brass answers |
| 49-56 | Rap verse | Dm9, Bbmaj7, Gm9, A7 (x2) | half-time hip-hop pocket (kick `..xx..x...x.` style), bass + Rhodes, guitar chops; narrow |
| 57-64 | Chorus 2 | first 8 chorus chords | freeze-and-drop into it |
| 65-68 | Bridge | Bbmaj7, Am7, Gm9, Asus4 | drums out: piano/Rhodes, string pad, rolled chords |
| 69-72 | Bridge build | Bbmaj7, C, Ebmaj7, A7#5#9 | snare roll, toms, riser |
| 73-88 | Final chorus | chorus chords | everything + string counter-line + the opening hook restated |
| 89-92 | Outro | Dm9 vamp | intro motif over the chorus groove, station chime, final hit |

A guide melody for the sung sections is written to the lyrics (syllable by syllable, in the singer's range
G2-G4, chorus peaking at F4-G4) so the Sing screen can play and show it; the singer's own takes drifted too
much in pitch to build the harmony around them.

## 4. First iteration (2026-10-15): what was built and measured

`studio/last_train.py` writes every part by hand on the blueprint above (helpers in `studio/production.py`) and
`add_to_song` adds it to the user's song as **"Last Train, First Light · Persona band (base)"** (version 17),
rendered through the app's mixer, so Mix and Sing work on it (the guide melody plays on the Sing screen).
Instruments: [`INSTRUMENTS.md`](INSTRUMENTS.md).

Checks before anyone listened:
- **Guide melody vs the band:** the first draft had 90 half-step rubs (mostly the 9th of Dm9 or the maj7 of
  Fmaj7, E, against the singer's F). Comping now moves any chord tone a half step from the sung note down to
  the next chord tone (`production.clear_of`): 0 rubs; 18 of 132 strong-beat melody notes are colour tones.
- **Mix against the nine references** (the -10 LUFS listening master; references' median in brackets):
  width -8.4 dB (-9.3), verses narrower and 2 LU quieter than the choruses (as in the references), low-mid
  250-500 Hz -7.2 dB (-9.1; the first draft was -5.5, boxy: the Rhodes, piano and bass carried 65% of it, now cut
  at 300-350 Hz, plus a mix-bus match EQ `render.match_tone`), mid -7.6 (-7.0), presence -12.0 (-13.2),
  air -14.1 (-15.1), crest 12.1 dB (12.3), 7th chords 88% (89%), straight-16th funk groove (35% of onsets on 16th
  off-beats, like Burn My Dread and Full Moon Full Life).
- The app's critic says "the melody is buried": on purpose, the guide sits 9 dB under the band; the singer's
  vocal is the melody.

Not done yet: listening (the user), falls/rips on strings and brass (the player has no pitch bends), a real P3R synth layer, and the user's vocal over it.

## 5. The engine: every songbook song (2026-10-15, later)

The user liked the Last Train base and asked for more songs to sing over (and, later, instrumentals for game
scenes). `studio/engine.py` generalises the hand-written production:
- **Styles** (`engine.STYLES`): city pop (G, 112), night jazz (A minor, 86, swung 0.62), battle rush (E minor,
  158, band hits on shout words), rain bossa (D, 132), boss orchestra (C minor, 150, string ostinato, timpani,
  choir), ending ballad (F, 76, piano left hand, harp), labyrinth pulse (F# minor, 120). Each says how every
  section feel is played: drums, bass style, comping rhythm, and which layers come in.
- **Song specs** (`songbook_productions.SPECS`): chords per section, the song's hook motif, hit words. Return to
  Sender's hook quotes the main theme's "Ride, ride, ride" line; its chorus uses the main theme's chorus chords.
- **The melody writer** (`engine.write_melody`): rhythm from the syllables (stress on beats, held last
  syllable, a breath before the next line, a pickup into verse lines), pitches by beam search (chord tones on
  strong beats, steps preferred, an arch per line, open odd and closed even endings, register by section:
  verse low, chorus up to G4), and repeated words sung the same way so hooks stay hooks.
- `songbook_productions.make(id)` creates the song through Make (so the words, sections and Sing work) and adds
  the engine's production as version 2.

All six measured before going in: 0 half-step rubs between melody and band, guide melodies in A3-G4, and the
-10 LUFS listening masters within reach of the references (width -5.9 to -10.9 dB, low-mid -6.4 to -8.0 dB,
crest 11.9-12.4 dB). They are short (38-56 bars, about a minute to a minute and a half): the songbook wrote
them as game cues.

## 6. Instrumental cues for LINE ZERO (2026-10-15, later)

From LINE ZERO's AUDIO_PLAN 3.2 (read, not changed): the minimum viable set minus what the vocal songs already
cover. `studio/cues.py`, each added to the app as "LINE ZERO cue: ...":

| Cue | Scene | Style | Motifs |
|---|---|---|---|
| Boss battle | every boss | boss orchestra, C minor 150 | L0 (the Line 0 call: falling minor third + the ticket-punch 16th) on trumpet |
| The Lost Car | the Conductor's car | slow swing 72, brushes, upright, Rhodes, a ticking clock | H on harmon-muted trumpet (brass = memory) |
| Victory | after a battle (sting) | Rhodes chord + muted trumpet | B's tail |
| Results | the rank screen | light funk 100 | B |
| Mind the Gap | Stop exploration | labyrinth pulse 120 | T (H inverted, on a click) in pizzicato; H with notes 5-6 missing on celesta |
| Sad (soft) | grief, flashbacks | piano + cello 66 | H slowed to half speed |
| The Hideout | the base | lo-fi Rhodes, vinyl 90 | B |
| The Waiting Platform | a Velvet Room-style space | piano arpeggios, strings, a high wordless soprano 80 | H |
| Stop 3: After Hours | the arcade Stop | chip + city pop 128 | S (Soren's song, from the game code) on a square wave |
| Shop | city shops | swung chip + vibraphone 102 | B, then B at double speed |
| Finale: First Light | the hope finale | band + chip lead 140 | B leads, H answers as a countermelody, S in the verse |

Second batch (same day, later), each with its own small style in `engine.STYLES`:

| Cue | Scene | Sound | Motifs |
|---|---|---|---|
| Bond | hang-outs | soft swing 88, F major | B, then B an octave up |
| Title | title screen | ballad 78, D minor | H; in the chorus a wordless voice sings H high and slow over it |
| Tension | before a reveal | pulse 80, F# minor, two-chord vamps | T on violins at half speed |
| Station | the platform before a dive | night 100, C minor, room tone | a far horn, then L0 an octave down |
| Stop 1: Empty Classroom | Stop 1 | piano and room tone 70 | BELL (the school bell), then B with notes missing |
| Stop 2: Lost and Found | Stop 2 | worn-tape Rhodes 80, tape hiss | HARU |
| Stop 4: Waiting Room | Stop 4 | 60 bpm, fluorescent hum | H bent out of shape on prepared piano; then H clearly on celesta |
| Stop 5: Undertow | Stop 5 | slow swing 66, the sea | H on guitar; a trombone foghorn far off |
| Stop 6: Return to Sender | Stop 6 | radio-through-the-wall piano 84, AM static | B; violins take it in the chorus |
| Stop 7: End of the Line | Stop 7 | builds carriage by carriage, 92 | celesta H with notes missing; flute B; guitar S over cello H; vibraphone B with scratches; trumpet B with H on top |

New engine pieces: ambience tracks (`textures`: sea, hum, room, radio, plus vinyl/rain/wind/tape), instrument
variants (`sfz:rhodes_tape`, `sfz:piano_radio`, `sfz:piano_old` detuned 22 cents per note, `sfz:piano_prepared`), and
`theme_by_section` so one theme moves between instruments (a "Theme: <instrument>" track each).

**H and B are drafts** (the audio plan leaves both to the user); they live in `cues.MOTIFS` and change everywhere at
once. Still to make: menu, game over, line0_ride, ward, assault_sting; loop-point export for Roblox (the cues end on a
chord that leads back to bar 1, but the files still have a mastering fade).

## 7. Distinct Persona sounds, longer songs, softer night jazz (the user's notes)

- **"The drums on Wrong Side of Midnight are too overpowering":** three alternatives, all 2:00+: soft brushes
  (a brushed kit 7 dB down, walking upright bass, piano), a piano trio (no drums), lo-fi (a quiet kit 9 dB down,
  Rhodes, vibraphone, vinyl).
- **"Vocal songs at least 2 minutes":** `songbook_productions.extended_lyrics` keeps the words and lengthens the
  form (8-bar intro, instrumental Solo sections with the hook on the lead instrument, the chorus again, an 8-bar
  outro); `make` now does it for every new song.
- **"More distinct Persona sounds":** four new styles and four new songs with original lyrics built on the audio
  plan's hook drafts (assets/songbook 09-12):
  - *Second Platform*: Persona 3 urban (boom-bap, piano loop, string stabs, record scratches; B minor 96)
  - *Hold the Door*: Persona 4 J-pop rock (piano 8ths, crunchy guitars, synth strings, the royal-road chorus; E 120)
  - *Off the Rails*: Persona 5 battle rock (organ, distorted guitar, brass, 16ths; G minor 166)
  - *Punch the Ticket*: the anthem (band, organ, strings, choir on the hook; A minor 140)
- New sounds: record scratches (a brass stab dragged on a turntable curve), distorted power chords, broken-chord
  piano.

## 8. Undertale (Toby Fox) influence

Research (sources in the session's research report; techniques only): Fox made the score in FL Studio with free
soundfonts and SNES-era samples, said "made using free soundfonts and synths"; strong short motifs reused across
many tracks (the main theme leads 13 tracks) and transformed (slower and simpler for sad, double speed for battle,
swing for comedy, one theme's notes in another's rhythm); minor-modal loops (i-iv-VII-III), borrowed bVI/bVII in
major; chip voices layered over real instruments; a final "hope" theme that stacks the earlier motifs.
Applied: chip voices (pulse, square, a 16-step triangle, a noise-channel kit) in `arrange/synths.py`; the shop
cue swings the Bond theme and doubles it at double speed; Stop 3 puts Soren's song on a square wave over a city-pop
band; the finale stacks B over H; every cue quotes the same small set of motifs, the way Fox's score does.

## 9. Songs inspired by the reference folder (2026-10-15, late)

The user: "make some songs inspired by the ones I attached". Each takes its reference's measured fingerprint
(`mouthmixer analyse --stems`, REFERENCE_ANALYSIS.md): tempo, straight or swung, drum and bass density, favourite
chord moves. Chords, hooks and words are new: no melody, lyric or progression is copied. Songbook 13-19, each over
two minutes, with a quiet guide melody to sing over:

| Song | Inspired by | What it borrows |
|---|---|---|
| 13 Hollow Hour | Burn My Dread | trip-hop at 98, piano loop and strings, sub bass; the flat-II major seventh (Gb in F minor), iv7 to bvii7 |
| 14 Paint the City | Color Your Night | four kicks a bar at 96, funk bass, Rhodes, sax; chords every two beats, vi7 to V, ii7 to iii7, IV to II7 |
| 15 High Tide | Full Moon Full Life | straight 16ths at 96, piano and guitars; iii7 to VI7 to ii7, bVImaj7 to vi7 |
| 16 Down to the Wire | It's Going Down Now | 166 acid-jazz battle, organ, brass; bIIImaj7, bVImaj7 to v7, the half-step slide IImaj7 to bIIImaj7 |
| 17 Safety Off | Pull the Trigger, A Way of Life | swung boom-bap (0.64) at 94, worn-tape Rhodes, harmon trumpet; bIII to IIsus4 to i; Imaj7 and bVImaj7 in the outro |
| 18 Lunchbell | School Days, Signs of Love | four on the floor at 118, an octave disco bass (about 12 notes a bar; School Days measured 14); major sevenths stepping up, Vmaj7 to iii7 |
| 19 Reach for the Stars | When the Moon's Reaching Out Stars | swung shuffle (0.65) at 120, piano, jazz organ, vibraphone; ii7 and iii7 into IVmaj7, IIsus4 to vi7, bVIImaj7 |

Engine additions: a `disco` bass; 8th-note basses follow a split bar's second chord; `skank` and `clav` comping;
each style's `refs` makes the master match EQ aim at those references' band balance (`render.ref_bands`; the
analyses stay on the user's machine, and without them it falls back to the nine-song median). After matching,
the mixes sit within about 2 dB of their reference in every band, except the sub on 16 and 19 (+4 dB, at the
EQ's 4 dB limit).

