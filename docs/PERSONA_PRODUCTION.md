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

