# Song shapes: what makes the Persona vocal songs hit, and the rules we build with

The user listened closely to five Persona songs and described what happens in them (2026-10-13). This file
lines those observations up with music theory and research, and says where each rule lives in MouthMixer.
Song names are used only to point at examples; nothing here copies their melodies, lyrics or riffs.

## What the user heard

| Song | Observation |
|---|---|
| "Wake Up, Get Up, Get Out There" | Starts with few instruments and adds more; when the vocal enters, the supporting parts stay and the distracting ones leave; just before the chorus the band freezes while the first chorus words are sung, then the beat drops and everything comes back: the epic moment. |
| "It's Going Down Now" | Starts fast and intense with low, fast rap; builds to a contrasting, higher sung chorus with new instruments and longer held notes and a shouted action phrase; one slow, thoughtful part; then straight back to the chorus. |
| "Color Your Night" | A catchy bass-and-chords loop that never disappears; low rap on the beat, then the singer and all instruments come in; the low voice also gets a sung part; a third voice switches it up; lots of vocal stims ("ayyy"); voices hand off immediately and sometimes overlap; the elegant voice brings piano and elegant instruments, the rapper doesn't. |
| "Take Over" | Opens with full band (guitar, drums, strings); drops to the beat when the singer enters; ramps back up to the chorus; repeats down-rise-chorus; an instrumental break leads to a singer-and-piano part that changes the vibe; builds again; ends on three dramatic full-band hits. |
| Across them | Low voices carry most of the song, the high singing voice is saved for the grand choruses; some songs build into the chorus, some pivot into it hard. |

## Cross-check: does it hold up?

Yes, these are real, well-documented techniques. In order:

1. **Building the arrangement by adding layers** (additive arrangement, "vertical layering"). Standard
   arranging; ARRANGING.md R3 (layers enter over time so each new one is noticed). **Holds.**
2. **Making room for the voice**: when a vocal enters, parts that compete for the same frequencies and
   attention (busy melodies and riffs in roughly 1-4 kHz) drop out; supporting parts (beat, bass, held
   chords) stay. Standard practice (MUSIC_KNOWLEDGE X4, ARRANGING R2). **Holds.**
3. **The freeze and the drop** (a "stop" or "break" before the chorus, then everything at once). Music
   psychology: chills and strong emotions tend to come at sudden changes, especially *after* a passage
   with little activity (Grewe et al. 2007), at new instruments or voices entering (same), and at sudden
   changes of loudness (Sloboda 1991) [S, via secondary sources]. Expectation theory (Huron, *Sweet
   Anticipation*, 2006): holding back what the listener expects builds tension, and delivering it is the
   reward [S]. **Holds; this is the core of the "epic moment".**
4. **A chorus contrasts with the verse** in texture and colour more than in anything else: in a large pop
   corpus, *timbre* and *variety of timbres* separate choruses from verses better than pitch height (Van
   Balen et al. 2013); older work found choruses louder, with heavier instrumentation, more vocals and the
   highest sung note [S]. So "new instruments + a different (higher) voice in the chorus" is right; the
   new *colour* matters even more than the height. **Holds, with that nuance.**
5. **Low rap / high sung chorus** is a register and timbre contrast (point 4), plus call and response
   between two "characters" (PERSONA_STYLE §7). **Holds.**
6. **A loop that never disappears** (bass + chord instrument) keeps the identity while voices and layers
   change on top: repetition makes a track recognisable and lets contrast elsewhere stand out. **Holds**
   (LYRIC_CRAFT: repetition drives memorability).
7. **Voices that overlap at hand-offs** keep the energy continuous (no gap for attention to drop). Common
   in duet and rap-sung writing [U]. **Holds.**
8. **Each voice has its own instrument palette** (piano and strings with the elegant singer; beat and bass
   with the rapper): "timbral association", the same idea as leitmotifs, a sound that comes with a
   character. **Holds** [U].
9. **A slow, thoughtful section** before the last chorus (bridge/breakdown) is the classic contrast before
   the final peak; the peak lands harder after it (point 3). **Holds.**
10. **Three big hits to end**: a strong, unmistakable ending (a "button") instead of a fade; three is
    the usual number because it groups as a gesture (tension, tension, end). **Holds** [U].

Sources: Grewe et al. 2007 and Sloboda 1991 via https://musicscience.net/2017/03/17/now-thats-what-i-call-chills-a-growing-playlist-for-chills-music/
and https://www.ellendissanayake.com/publications/pdf/EllenDissanayake-Tracking_Musical_Chills.pdf ·
Van Balen et al. 2013 https://archives.ismir.net/ismir2013/paper/000180.pdf and https://archives.ismir.net/ismir2023/paper/000093.pdf ·
Huron 2006 https://mtosmt.org/issues/mto.09.15.3/mto.09.15.3.aversa.php

## The rules we build with (and where they live)

| Rule | In MouthMixer |
|---|---|
| **Energy shape**: low → build → peak, then down → rise → peak again, highest at the final chorus | Section feels on the song board: intro, verse, build-up, chorus lift, rap pocket, breakdown, final chorus, ending (`studio/starters.py` FEELS). Every song from lyrics gets this shape automatically. |
| **Building intro**: chords, then bass, then drums, then hits into the verse | "Building intro" feel (default) |
| **Big intro**: the full band at once, then strip down for the voice | "Big intro" feel (pick it on the board) |
| **Verses ramp up**: held chords first, rhythm half way, more in the build-up | "Verse" and "Build-up" feels |
| **Room for the voice**: in sections with words, busy pieces (melodies, riffs, answer lines, chops, percussion, stabs) stay out of verses, rap and build-ups by default; beat, bass and chords stay | `Project._default_sections` |
| **Freeze, then drop**: the first bar of a chorus after a build-up is the voice alone, a riser swells through it, then crash + kick and everything comes in | "freeze" option per section (default 1 bar after a build-up) |
| **Chorus = new colours**: open hats, crashes, higher chord voicings, pad shimmer an octave up, extra parts switched on | "Chorus lift" / "Final chorus" feels; add stabs and chops in chorus columns |
| **Rap pocket**: half-time beat, long low bass, sparse chords, no pad (the base loop stays) | "Rap pocket" feel |
| **Singer-and-piano moment**: drums out, soft broken piano chords, then a build | "Breakdown" feel + the starter "Piano for the quiet parts" + "Build-up" |
| **Low verses, high chorus**: sing verses in your own voice on the Verse lead track, choruses on the Chorus lead track with a higher character (Female lead, an octave up), rap on the Rap track (Deeper male) | Vocal tracks and voice characters (VOCALS §11) |
| **Voices overlap at hand-offs** | Each vocal track is recorded over the whole section, so the next voice can start on the last word of the previous one |
| **Vocal stims** ("ayyy", "hey!") | The Ad-libs track, or Vocal chop pieces in Make |
| **Band hits with the hardest words** | Mix → "Add hits" (drum hits and brass stabs on vocal accents) |
| **Big ending**: three full-band hits, then silence | "Big ending" feel (default for battle and boss songs) |
| **One motif everywhere**: the station chime | Starter "Station chime" in intros and outros |
