"""Lyrics (docs/VOCALS.md §8): the melody's "syllable map", lyric writing with Claude, rule checks, and
alignment of syllables to notes for the karaoke display and the vocal guide.

Without a Claude API key you can type your own lyrics; they get the same checks and alignment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

SECTION_ROLES = {"A": "Verse 1", "A'": "Verse 2", "B": "Bridge", "A''": "Final chorus (the hook)"}
NO_WORDS = ("intro", "outro", "ending")


def section_role(name: str) -> str | None:
    """What a section is for in the lyrics, or None for sections without words (intro, outro, ending).
    Generated songs use A/A'/B/A''; songs from the Make tab use names like "Verse", "Hook 2"."""
    if name in SECTION_ROLES:
        return SECTION_ROLES[name]
    return None if name.lower().startswith(NO_WORDS) else name


def is_hook(name: str) -> bool:
    return name == "A''" or name.lower().startswith(("hook", "chorus"))
CLOSED_VOWELS = {"IY", "UW", "IH", "UH"}  # "ee", "oo", "ih", "uh": hard to hold on long, high notes


# --------------------------------------------------------------------------------------------------
# The syllable map: what the words have to fit
# --------------------------------------------------------------------------------------------------

def lead_notes(version: dict) -> list[tuple]:
    return sorted(tuple(n) for t in version["tracks"] if t["role"] == "lead" for n in t["notes"])


def phrases(notes: list, gap: float = 0.75, long: float = 2.0, most: int = 12, fewest: int = 3) -> list[list]:
    """Split one section's notes [(start, length, pitch, ...)] (beats) into sung lines: after a rest of
    `gap` beats or a note of `long` beats; a line over `most` notes is split where the singer would
    breathe (the longest note plus rest, away from the ends); lines under `fewest` notes join a neighbour
    (one-note lines can't carry words). Used by the lyrics and by the vocal comping, so both agree."""
    notes = sorted(notes)
    lines, cur = [], []
    for i, n in enumerate(notes):
        cur.append(n)
        nxt = notes[i + 1] if i + 1 < len(notes) else None
        if nxt is None or nxt[0] - (n[0] + n[1]) >= gap or n[1] >= long:
            lines.append(cur)
            cur = []

    def split(ln):
        if len(ln) <= most:
            return [ln]
        lo, hi = max(fewest, len(ln) // 3), min(len(ln) - fewest, 2 * len(ln) // 3)
        def weight(k):  # a breath after note k: its length plus the rest after it
            rest = ln[k + 1][0] - (ln[k][0] + ln[k][1])
            return ln[k][1] + 2 * max(0.0, rest) + (0.25 if abs((ln[k + 1][0]) % 2) < 0.05 else 0)
        k = max(range(lo - 1, hi), key=weight)
        return split(ln[:k + 1]) + split(ln[k + 1:])

    lines = [part for ln in lines for part in split(ln)]
    out: list[list] = []
    for ln in lines:
        if out and (len(ln) < fewest or len(out[-1]) < fewest) and len(out[-1]) + len(ln) <= most + 2:
            out[-1] = out[-1] + ln
        else:
            out.append(ln)
    return out


def syllable_map(version: dict) -> list[dict]:
    """Per section, the phrases (lines) of the melody: note count, which notes are stressed (beats 1 and 3,
    or clearly long), long notes and high notes (MUSIC_KNOWLEDGE L1-L3)."""
    notes = lead_notes(version)
    if not notes:
        return []
    pitches = [n[2] for n in notes]
    high_cut = np.percentile(pitches, 75)
    out = []
    for sec in version["sections"]:
        if section_role(sec["name"]) is None:
            continue
        a, b = sec["start"] * 4, (sec["start"] + sec["bars"]) * 4
        lines = phrases([n for n in notes if a <= n[0] < b])
        if not lines:
            continue
        out.append({
            "section": sec["name"], "role": section_role(sec["name"]),
            "lines": [{
                "notes": [[round(s, 3), round(l, 3), int(p)] for s, l, p, *_ in ln],
                "count": len(ln),
                # Strong: on beat 1 or 3, or clearly longer than the line's typical note (MUSIC_KNOWLEDGE L2).
                "stress": "".join("S" if (abs(s % 2) < 0.05 or l >= max(1.0, 1.5 * float(np.median([x[1] for x in ln]))))
                                  else "w" for s, l, p, *_ in ln),
                "long": [i for i, (s, l, p, *_) in enumerate(ln) if l >= 1.0],
                "high_long": [i for i, (s, l, p, *_) in enumerate(ln) if l >= 1.0 and p >= high_cut],
            } for ln in lines],
        })
    return out


# --------------------------------------------------------------------------------------------------
# Pronunciation helpers
# --------------------------------------------------------------------------------------------------

def _phones(word: str) -> str | None:
    import pronouncing

    w = re.sub(r"[^a-z']", "", word.lower())
    p = pronouncing.phones_for_word(w)
    return p[0] if p else None


def word_syllables(word: str) -> list[tuple[str, int, str | None]]:
    """[(written chunk, stress 0/1/2, vowel phone)] for one word. Known words use the CMU dictionary;
    unknown words fall back to vowel groups."""
    w = re.sub(r"[^A-Za-z']", "", word)
    if not w:
        return []
    ph = _phones(w)
    vowels = [p for p in ph.split() if p[-1].isdigit()] if ph else []
    n = len(vowels) or max(1, len(re.findall(r"[aeiouy]+", w.lower().rstrip("e") or w.lower())))
    chunks = _split_word(w, n)
    return [(c, int(vowels[i][-1]) if i < len(vowels) else (1 if n == 1 else 0), vowels[i][:-1] if i < len(vowels) else None)
            for i, c in enumerate(chunks)]


def _split_word(w: str, n: int) -> list[str]:
    """Split a written word into n syllable-ish chunks at vowel-group boundaries (for display)."""
    if n <= 1:
        return [w]
    groups = [m.start() for m in re.finditer(r"[aeiouyAEIOUY]+", w)]
    if len(groups) < n:
        size = max(1, len(w) // n)
        return [w[i * size:(i + 1) * size] if i < n - 1 else w[i * size:] for i in range(n)]
    cuts = []
    for g in groups[1:n]:
        k = g
        while k > 0 and w[k - 1] not in "aeiouyAEIOUY" and k - 1 > (cuts[-1] if cuts else 0) and g - k < 1:
            k -= 1
        cuts.append(k)
    parts, last = [], 0
    for c in cuts:
        parts.append(w[last:c])
        last = c
    parts.append(w[last:])
    return [p for p in parts if p] or [w]


def line_syllables(text: str) -> list[dict]:
    out = []
    for word in text.split():
        for chunk, stress, vowel in word_syllables(word):
            out.append({"text": chunk, "stress": stress, "vowel": vowel, "word": word})
    return out


# --------------------------------------------------------------------------------------------------
# Checks (MUSIC_KNOWLEDGE L1-L8)
# --------------------------------------------------------------------------------------------------

BANNED = {"damn", "hell", "shit", "fuck", "bitch", "kill"}


def check(option: dict, smap: list[dict]) -> dict:
    issues, scores = [], []
    for sec, lines in zip(smap, [s["lines"] for s in option["sections"]]):
        for i, (target, line) in enumerate(zip(sec["lines"], lines)):
            syl = line_syllables(line["text"] if isinstance(line, dict) else line)
            n, m = target["count"], len(syl)
            s = 1.0
            if abs(n - m) >= 2:  # L1
                issues.append(f"{sec['role']}, line {i + 1}: {m} syllables for {n} notes")
                s -= 0.5
            elif n != m:
                s -= 0.1
            # L2: a primary-stressed syllable on a weak note while its own word's unstressed one is strong.
            for k in range(min(n, m) - 1):
                a, b = syl[k], syl[k + 1]
                if a["word"] == b["word"] and a["stress"] == 0 and b["stress"] == 1 and \
                        target["stress"][k] == "S" and target["stress"][k + 1] == "w":
                    issues.append(f"{sec['role']}, line {i + 1}: \"{a['word']}\" is stressed on the wrong beat")
                    s -= 0.25
                    break
            for k in target["high_long"]:  # L3
                if k < m and syl[k]["vowel"] in CLOSED_VOWELS:
                    issues.append(f"{sec['role']}, line {i + 1}: \"{syl[k]['text']}\" is a closed vowel on a long high note")
                    s -= 0.1
            text = (line["text"] if isinstance(line, dict) else line).lower()
            if any(w.strip(".,!?'") in BANNED for w in text.split()):  # L8
                issues.append(f"{sec['role']}, line {i + 1}: language not suitable for a teen audience")
                s = 0.0
            scores.append(max(0.0, s))
    # L5: the hook repeats in the final chorus.
    if option["sections"]:
        final = [ln["text"] if isinstance(ln, dict) else ln for ln in option["sections"][-1]["lines"]]
        hook = option.get("title", "").lower()
        reps = sum(1 for ln in final if hook and hook in ln.lower())
        if hook and reps < 2:
            issues.append(f"the hook \"{option.get('title')}\" appears {reps}× in the final chorus (aim for 2-4)")
            scores.append(0.6)
    return {"score": round(float(np.mean(scores)) if scores else 0.0, 3), "issues": issues}


# --------------------------------------------------------------------------------------------------
# Alignment: syllables onto notes
# --------------------------------------------------------------------------------------------------

def align(option: dict, smap: list[dict]) -> list[dict]:
    """Karaoke events: one per note, with the syllable sung on it ("" = held from the previous one).
    Too many syllables: the longest notes are split. Too few: the last syllables stretch (melisma)."""
    events = []
    for sec, lines in zip(smap, [s["lines"] for s in option["sections"]]):
        for li, (target, line) in enumerate(zip(sec["lines"], lines)):
            text = line["text"] if isinstance(line, dict) else line
            syl = [x["text"] for x in line_syllables(text)]
            notes = [list(n) for n in target["notes"]]
            while len(syl) > len(notes) and notes:
                k = max(range(len(notes)), key=lambda j: notes[j][1])
                s, l, p = notes[k]
                if l < 0.5:
                    break
                notes[k:k + 1] = [[s, l / 2, p], [s + l / 2, l / 2, p]]
            for j, (s, l, p) in enumerate(notes):
                if j < len(syl):
                    t = syl[j] if j < len(notes) - 1 or len(syl) <= len(notes) else " ".join(syl[j:])
                else:
                    t = ""  # melisma: keep singing the previous vowel
                events.append({"start": s, "length": l, "pitch": p, "text": t, "line": li, "section": sec["section"],
                               "line_text": text})
    return events


# --------------------------------------------------------------------------------------------------
# Writing with Claude
# --------------------------------------------------------------------------------------------------

@dataclass
class LyricsError(Exception):
    message: str

    def __str__(self):
        return self.message


SYSTEM = """You write song lyrics that fit an existing melody exactly. You are given, per section and
line, the number of notes, which notes are stressed (S) or weak (w), and which notes are long or high.

Rules (follow all of them):
- Exactly one syllable per note in every line (count carefully). At most one extra or missing syllable.
- Put naturally stressed syllables on S notes and unstressed ones on w notes. Never stress a word wrongly.
- On long, high notes use open vowels ("ah", "oh", "ay", "eh"); avoid "ee" and "oo" there.
- Verses tell the story with concrete images (places, objects, actions); avoid clichés.
- The final chorus is the hook: short, chantable, the title in its first and/or last line, repeated 2-4
  times, even line lengths, closed rhymes (AABB or ABAB). The bridge takes a new angle.
- English, clean for a teen audience, no brand names, and never reuse lines from real songs.
- Catchy over clever: the best game-song hooks are short phrases a player can't stop humming."""


def write(brief: str, version: dict, *, n_options: int = 3, api_key: str | None = None) -> list[dict]:
    """Ask Claude for lyric options fitted to the syllable map; return them checked and ranked."""
    import json

    import anthropic
    from pydantic import BaseModel

    smap = syllable_map(version)
    if not smap:
        raise LyricsError("this song has no melody to write words for")

    class Line(BaseModel):
        text: str

    class Section(BaseModel):
        name: str
        lines: list[Line]

    class Option(BaseModel):
        title: str
        idea: str
        sections: list[Section]

    class Options(BaseModel):
        options: list[Option]

    request = {
        "brief": brief or "anything that fits the music",
        "style": version.get("style"), "mood": version.get("describe"), "key": version.get("key"),
        "options_wanted": n_options,
        "sections": [{"name": s["section"], "role": s["role"],
                      "lines": [{"notes": ln["count"], "stress": ln["stress"],
                                 "long_notes": ln["long"], "long_high_notes": ln["high_long"]} for ln in s["lines"]]}
                     for s in smap],
    }
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    try:
        response = client.beta.messages.parse(
            model="claude-opus-5-5",
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            thinking={"type": "adaptive"},  # counting syllables against stress patterns needs care
            system=SYSTEM,
            messages=[{"role": "user", "content": "Write lyric options for this melody. Same number of lines "
                       "per section as given.\n\n" + json.dumps(request)}],
            output_format=Options,
        )
    except anthropic.AuthenticationError:
        raise LyricsError("the Claude API key wasn't accepted; check it in Setup")
    except anthropic.RateLimitError:
        raise LyricsError("Claude is busy (rate limit); try again in a minute")
    except anthropic.APIConnectionError:
        raise LyricsError("couldn't reach Claude; check your internet connection")
    except anthropic.APIStatusError as e:
        raise LyricsError(f"Claude returned an error ({e.status_code})")
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise LyricsError("Claude declined this brief; try describing it differently")
    out = []
    for opt in response.parsed_output.options:
        d = _in_order(opt.model_dump(), smap)
        d["check"] = check(d, smap)
        out.append(d)
    out.sort(key=lambda d: -d["check"]["score"])
    return out


def _in_order(option: dict, smap: list[dict]) -> dict:
    """Sections in the melody's order, matched by name (missing ones empty)."""
    by_name = {s["name"]: s for s in option["sections"]}
    rest = [s for s in option["sections"] if s["name"] not in {m["section"] for m in smap}]
    option["sections"] = [by_name.get(m["section"]) or (rest.pop(0) if rest else {"name": m["section"], "lines": []})
                          for m in smap]
    for sec, m in zip(option["sections"], smap):
        sec["name"] = m["section"]
    return option


def from_text(title: str, sections_text: dict[str, str], version: dict) -> dict:
    """Your own lyrics: one line per melody phrase, per section."""
    smap = syllable_map(version)
    opt = {"title": title, "idea": "your own words", "sections": []}
    for s in smap:
        lines = [ln.strip() for ln in sections_text.get(s["section"], "").splitlines() if ln.strip()]
        opt["sections"].append({"name": s["section"], "lines": [{"text": ln} for ln in lines]})
    opt["check"] = check(opt, smap)
    return opt
