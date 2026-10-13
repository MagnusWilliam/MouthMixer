# Lyric craft: catchy words for game songs

How the songbook (`assets/songbook/`) lyrics are written, and what the Lyrics checks look for. Research
(2026-10-13) from web search; **[V]** two or more sources agree, **[S]** one source, **[U]** genre knowledge
or our default.

## What the research says

- **Earworms** (Jakubowski et al. 2016, 3,000 people, 83 melodic features): catchy tunes have a *common*
  overall contour (rise then fall), but *unusual* interval patterns (more or larger leaps), and faster
  tempos than non-earworms. Generic shape, one surprising jump. [S]
  https://gold.ac.uk/news/scientists-find-key-to-writing-catchy-pop-hits ·
  https://livescience.com/56739-what-makes-an-earworm-so-catchy.html
- **The title in the chorus**, where it's recognisable by position and repetition: bookending (first and last
  line of the chorus) is the most common pattern; 2-4 repeats. Don't let another line repeat more than the
  title, or it steals the hook. [V]
  https://www.taxi.com/music-business-faq/songwriting/songstructure/chorusconstruction ·
  https://www.bmi.com/news/entry/the-best-place-for-your-song-title ·
  https://rhymebook.com/guides/how-to-write-a-chorus
- **A short pause before the hook** draws attention to it. [S, anecdotal]
- **Persona specifically**: the music is written first and the words fitted to it (Lotus Juice on working
  with Meguro); English lyrics, sometimes "Engrish", which fans treat as part of the identity; one theme's
  melody gets new words elsewhere in the game (reused motif). [S]
  https://www.animeherald.com/2024/05/23/mass-destruction-a-conversation-with-lotus-juice/ ·
  https://megatenwiki.com/wiki/Burn_My_Dread_-Reincarnation:_Persona3- ·
  https://phansite-archive.onrender.com/thread/12308
- No source analysed *why* Persona's lyrics are catchy; the patterns below are genre knowledge [U].

## The patterns we use

1. **A 2-6 word hook that is also the title**, first and/or last line of the chorus, 2-4 times. ("Off the
   clock, off the clock", "Rain delay, rain delay", "Hey! Pull the brake!")
2. **Imperatives and shouts** for battle songs: a command plus "Hey!" is chantable by a crowd and gives the
   band a hit point. [U]
3. **Simple, international English**: short common words, big feelings in the chorus (light, home, ride,
   heart), concrete pictures in the verses (platform, ticket, umbrella, coffee). [U]
4. **Open vowels on long notes**: "ride", "night", "home", "go", "away", "grey", "stay". Avoid "ee/oo" on
   held high notes (the Lyrics check L3). [V, VOCALS §8]
5. **Verses tell, choruses repeat**: verses change every time, the chorus never does (except the final
   chorus's last line, the payoff: "here comes the first light"). [V]
6. **Pre-choruses get shorter**: lines shrink (8 → 4 syllables) so the energy rises into the chorus. [U]
7. **Call and response**: leave gaps after hook lines for an answer (brass stab, sax, "Hey!", a backing
   "ooh"). [U, PERSONA_STYLE §7]
8. **One motif for the whole game**: the train-door chime (three notes) in intros and outros, and the main
   theme's hook melody hummed slowly in the ending song. [U]
9. **Loop songs say less**: daytime and rain themes are heard hundreds of times, so one short verse and a
   chorus, then long instrumental stretches. [U]
10. **Rap verses**: 8 lines, about one bar per line at battle tempo, internal rhymes and a punch word at the
    end of each line for the band to hit with the vocal accent. [U]


## Marking who sings (2026-10-14)

In the lyrics you paste (or a songbook file), a header can name the singers and a length, and a line can
name who joins in. The app shows these on the Make board and the Sing screen.

```
[Intro, 8 bars, spoken, Announcer]
[Chorus, Chorus lead + Gang]
Gang: Ride, ride, ride on the last train,
```

Singer names are the vocal tracks: Lead, Verse lead, Chorus lead, Rap, Gang, Backing, Harmony, Ad-libs,
Announcer, Whisper. A line starting with anything else before a colon ("Note: …") stays as written.

**Endings that hand off.** End each section on a line that leads into the next: the pre-chorus ends rising
("here we go!") into the chorus freeze, the chorus ends on its shout ("hold the gate!"), the rap ends on a
punchline into the chorus, and a quiet bridge line makes room for the build.
