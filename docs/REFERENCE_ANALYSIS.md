# Reference-song analysis

What the songs the user loves have in common, as numbers, so MouthMixer can use their **tendencies** as a
blueprint (never their melodies or riffs: PLAN §8.3, §10). The audio stays on the user's PC (`refrence
audio/` and `*.flac` are git-ignored); results are written to `<library>/analysis/<song>/` (analysis.json and
summary.md).

```
python -m mouthmixer analyse "refrence audio/persona"          # every song in a folder
python -m mouthmixer analyse song.flac --stems                  # with stem separation (needs Demucs, below)
```

## 1. What the tool measures (`src/mouthmixer/reference/analyse.py`)

| Measure | Method | Trust |
|---|---|---|
| Tempo, beat grid | librosa beat tracker (no trimming; grid carried through quiet intros/outros) | good; may read half or double time |
| Downbeat | the beat phase where low-end hits and chord changes land most | fair |
| Key | Krumhansl/Temperley profiles on the song's chroma | good up to relative major/minor |
| Chords | chroma templates (triads, 7, maj7, m7, dim, sus4) every 2 beats, as roman numerals | rough: extensions and inversions read as the nearest template; the "chord every N beats" figure is just the 2-beat grid, not a measurement of harmonic rhythm |
| Sections | novelty on the bar self-similarity matrix (4 bars each side) plus level jumps, 4-bar lines preferred, labels A/B/C by similarity, "chorus?/intro?" guesses | fair |
| Loudness | BS.1770 integrated (pyloudnorm), 3 s short-term range, 4× oversampled true peak, crest | good |
| Tone | each band's share of the energy (sub, bass, low-mid, mid, presence, air) | good |
| Width | side vs mid level | good |
| Groove | where onsets fall inside the beat: off-beat 8th position (0.50 straight, ~0.67 swung), share on 16th off-beats, share off the 16th grid | fair |
| With stems | level of each stem per section (LU against the mix); vocal range, sung share, note rate, tone and how far it stands above the band at 1-4 kHz; bass notes per bar and how often on the chord root; kick/snare/hat 16-step patterns | depends on the separation |

Stems are read from `<library>/analysis/<song>/stems/{vocals,drums,bass,other}.wav`, so stems from any
tool (for example UVR) work too.

## 2. Software and licences (researched 2026-10-15)

| Part | Licence (code / weights) | Windows + AMD | Status here |
|---|---|---|---|
| librosa | ISC | CPU | in use |
| pyloudnorm | MIT | CPU | in use |
| Demucs 4.1 (adefossez fork; facebookresearch repo archived 2025-01) | MIT / Hugging Face card says MIT, but earlier author statements called the weights research-only (MUSDB training data) | CPU only (torch-directml lacks an op Demucs needs); ~1.5× song length on the README's reference CPU | **not installed: needs the user's OK** (PyTorch CPU ~1 GB installed, htdemucs weights ~80 MB downloaded at first use, never bundled) |
| Beat This! (CPJKU) | MIT / MIT | torch CPU | candidate for better beats and downbeats |
| Basic Pitch (Spotify) | Apache-2.0 / included | ONNX Runtime | candidate for notes; its 0.4.0 release targets Python ≤ 3.11, so it needs `--no-deps` plus onnxruntime on 3.12 |
| ByteDance piano transcription | Apache-2.0 / CC BY 4.0 (credit) | torch CPU | optional |
| madmom models | BSD / **CC BY-NC-SA** | | **avoid** (non-commercial) |
| ADTOF drums | **CC BY-NC-SA** | | **avoid**; drums are read by band onsets instead |
| allin1, BTC chords, RoFormer community weights | weights licence unstated | | avoid |

Sources: github.com/adefossez/demucs, huggingface.co/adefossez/HTDemucs (and its discussion #1),
github.com/CPJKU/beat_this, github.com/spotify/basic-pitch, github.com/CPJKU/madmom, github.com/MZehren/ADTOF,
pypi.org/project/torch-directml.

## 3. First findings: nine Persona tracks, full mixes (no stems yet)

Songs: A Way of Life, Burn My Dread, Color Your Night, Full Moon Full Life, It's Going Down Now, Pull the
Trigger, School Days, Signs of Love, When the Moon's Reaching Out Stars -Reload-.

| Song | BPM (as read) | Key (as read) | LUFS | Crest dB | Width dB | Low-mid | Presence | Air | Off-beat 8th | On 16th off-beats | 7th chords |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A Way of Life | 95.7 | D minor | -11.8 | 14.4 | -11.9 | -9.1 | -13.2 | -17.9 | 0.50 | 15% | 78% |
| Burn My Dread | 97.5 | G minor | -10.7 | 14.3 | -6.2 | -9.2 | -11.2 | -14.6 | 0.51 | 37% | 79% |
| Color Your Night | 95.7 | C# major | -9.9 | 11.5 | -9.2 | -7.1 | -17.0 | -19.7 | 0.50 | 7% | 91% |
| Full Moon Full Life | 95.7 | Ab major | -6.8 | 9.5 | -7.7 | -8.2 | -10.2 | -18.4 | 0.51 | 37% | 89% |
| It's Going Down Now | 166.7 | C# minor | -7.9 | 10.3 | -9.3 | -9.3 | -10.8 | -11.9 | 0.50 | 1% | 85% |
| Pull the Trigger | 97.5 | G minor | -10.7 | 13.3 | -8.7 | -7.6 | -12.3 | -17.5 | **0.66** | 4% | 92% |
| School Days | 117.5 | D major | -10.0 | 12.3 | -9.7 | -11.0 | -13.2 | -13.8 | 0.50 | 3% | 99% |
| Signs of Love | 105.5 | Eb major | -10.4 | 12.8 | -11.3 | -10.3 | -14.2 | -13.1 | 0.49 | 6% | 93% |
| Moon's Reaching Out (Reload) | 120.2 | Ab major | -9.8 | 11.8 | -11.5 | -9.1 | -13.7 | -15.1 | **0.65** | 2% | 88% |
| **Median** | | | **-10.0** | **12.3** | **-9.3** | **-9.1** | **-13.2** | **-15.1** | | | **89%** |
| *Last Train v15 (ours)* | 126.0 | F major (= D minor) | *-14.1* | *16.0* | ***-16.6*** | ***-6.4*** | *-13.1* | *-18.6* | 0.54 | 25% | 93% |

Bands are each band's share of the energy in dB (low-mid 250-500 Hz, presence 2-6 kHz, air 6-16 kHz).
BPMs are as read by the tracker; some may be half time. These are the official game mixes: their true peaks sit
at or above 0 dBFS.

**What stands out:**
1. **Seventh chords everywhere** (78-99% of the time; maj7 and m7 on IV, vi, ii, iii, bIII, bVI). The song
   generator already leans this way (ours 93%): keep it.
2. **Two groove families:** straight 16th funk/pop, where about a third of onsets land on 16th off-beats
   (Burn My Dread, Full Moon Full Life), and **swung** jazz feels with the off-beat 8th at 0.65-0.66
   (Pull the Trigger, Reload). Ours sits in between (0.54): neither clearly straight nor swung.
3. **Our mix is narrow and boxy.** Width -16.6 dB against a median of -9.3 dB (the references are about 7 dB
   wider), and 2.7 dB more energy in 250-500 Hz than the median: the "muffled" impression is partly the
   whole mix, not only the voice. Air is 3.5 dB under the median.
4. **Loudness:** the references sit around -10 LUFS (-7 to -12) with about 12 dB crest; ours is mastered to
   -14 LUFS (a streaming/game-safe target) with 16 dB crest. For A/B listening against them, level-match
   first, or ours will always sound "worse" just by being quieter.

**Rules to try (each to confirm by ear before it becomes a critic rule, MUSIC_KNOWLEDGE §13):**
- Mix: aim for side/mid within -12 to -7 dB (wider pads, keys, doubled guitars and backing vocals panned out;
  bass, kick, lead vocal centred); keep 250-500 Hz at most about -8.5 dB of the energy (cut low-mids on
  pads, keys and guitars); air within about 3 dB of -15.
- Groove: pick a lane per song: straight 16ths (busy hats and bass on 16th off-beats) or a real swing near 0.65,
  not the in-between.
- Master: offer a "loud like the references" master (about -10 LUFS) for listening, alongside the -14 game
  master.

## 4. Next

- With the user's OK: install Demucs (CPU) and run `--stems` on the nine songs, for vocal level and tone
  against the band per section, bass movement and drum patterns. Those are the numbers that tell us how loud
  and bright the user's vocal should sit.
- More references that would help most: songs in the moods LINE ZERO needs that aren't covered yet (a
  calm daytime track like "Your Affection" or "Beneath the Mask", a battle track from P5 like "Last Surprise"
  or "Life Will Change", and a slow ballad), plus one non-Persona song whose mix the user loves.
