"""
Proposes where the sermon starts and ends in a full-service recording.

The LLM only reads text. It answers with timestamps *and* the exact words at
each boundary. We then find those exact words in the transcript near the claimed
time and place the cut on the real word, so a hallucinated or slightly-off
timestamp is caught or corrected instead of trusted.
"""

import difflib
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List

from app.trim_suggester.errors import SuggestionError
from app.trim_suggester.transcribe import Segment, transcribe
from app.utils.timestamps import format_timestamp

START_PAD = 1.0  # begin a little early so the first word is never clipped
END_PAD = 2.0  # end a little late so the last word is never clipped
SEARCH_WINDOW = 120.0  # how far from the claimed time to look for the quote
PHRASE_WORDS = 7
MIN_SERMON_SECONDS = 10 * 60
# A transcript segment longer than this has unreliable edges (singing, music),
# so its start/end are not used as a cut point.
MAX_TRUSTED_SEGMENT = 30.0
# If the final cut is further than this from the model's own time, say so.
MAX_SNAP_SHIFT = 30.0
# Silence longer than this inside the transcript is shown to the model as a gap.
GAP_SECONDS = 45.0
# A pause this long in the middle of a quoted phrase means the quote spans two
# separate utterances (e.g. "Thank you." ... [pause] ... "Today's scripture...").
LONG_PAUSE = 3.0

GUIDANCE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "config",
    "trim_guidance.md",
)
DEFAULT_GUIDANCE = (
    "The recording is a full church service. We want only the sermon: from the "
    "preacher's first words of the message to their last, excluding worship "
    "songs, announcements and the offering."
)

SYSTEM = (
    "You find where a sermon starts and ends inside a recording of a full church "
    "service. You reply with a single JSON object and nothing else."
)

USER_TEMPLATE = """\
Below is an automatic, timestamped transcript of a full church service. Words may be misheard. Find where the sermon starts and ends.

{guidance}

Transcript, one line per stretch of speech as "[H:MM:SS] text". A line such as "(no speech for 4:01: likely music or singing)" marks a stretch where nobody is speaking.

{transcript}

The start_quote must begin with the very first word that belongs in the clip, and the end_quote must end with the very last word that belongs in it. Never begin start_quote with the previous speaker's closing words (such as "Thank you."), and never end end_quote with the next speaker's opening words.

If the start or end could reasonably be somewhere else (for example the preacher speaks again after a song, or you are unsure which of two prayers closes the sermon), choose the most likely one for the main answer and list the other under "alternatives". Use an empty list when you are sure.

Reply with only this JSON object:
{{"start_seconds": <number>, "start_quote": "<the first words of the sermon, copied exactly from the transcript>", "end_seconds": <number>, "end_quote": "<the last words of the sermon, copied exactly from the transcript>", "confidence": "high" | "medium" | "low", "reasoning": "<one sentence>", "alternatives": [{{"which": "start" | "end", "seconds": <number>, "quote": "<exact words at that boundary>", "note": "<why this is possible>"}}]}}
"""


@dataclass
class TrimSuggestion:
    start: float
    end: float
    start_quote: str
    end_quote: str
    confidence: str
    reasoning: str
    verified: bool
    warnings: List[str] = field(default_factory=list)
    model: str = ""
    # Other plausible cuts the model offered: dicts with which/time/quote/note.
    alternatives: List[dict] = field(default_factory=list)
    # The transcript this was based on, so the cut preview can show the words
    # around each cut. Not saved in the run record.
    segments: list = field(default_factory=list, repr=False)


def words_around(segments, seconds, before_seconds=6.0, after_seconds=6.0, count=10):
    """
    Returns (heard before the cut, heard after the cut) as text, covering only
    what will actually be audible in the cut preview: the words spoken in the
    `before_seconds` leading up to the cut and the `after_seconds` following it.
    If nobody speaks in a window, says so and says what comes next, so the
    screen never promises words the clip does not play.
    """
    items = []  # (start, end, text), one per word (or per segment without words)
    for segment in segments:
        if segment.words:
            items.extend((w.start, w.end, w.text) for w in segment.words)
        else:
            items.append((segment.start, segment.end, segment.text))

    earlier = [i for i in items if i[1] <= seconds + 0.05]
    later = [i for i in items if i[0] >= seconds - 0.05]

    def words(chosen):
        return " ".join(text for _, _, text in chosen)

    heard_before = [i for i in earlier if i[1] > seconds - before_seconds][-count:]
    heard_after = [i for i in later if i[0] < seconds + after_seconds][:count]

    if heard_before:
        before_text = ("..." if len(earlier) > len(heard_before) else "") + words(heard_before)
    elif earlier:
        gap = seconds - earlier[-1][1]
        before_text = f'(quiet. The last words were {gap:.0f}s earlier: "...{words(earlier[-6:])}")'
    else:
        before_text = ""

    if heard_after:
        after_text = words(heard_after) + ("..." if len(later) > len(heard_after) else "")
    elif later:
        gap = later[0][0] - seconds
        after_text = f'(silence for {gap:.0f}s, then: "{words(later[:6])}...")'
    else:
        after_text = ""
    return before_text, after_text


def _pieces(segment):
    """
    Splits a segment wherever its own words have a long silent gap. Whisper can
    glue speech before and after a song into one "segment" spanning minutes.
    """
    if not segment.words:
        return [(segment.start, segment.end, segment.text)]
    runs, current = [], [segment.words[0]]
    for word in segment.words[1:]:
        if word.start - current[-1].end > GAP_SECONDS:
            runs.append(current)
            current = [word]
        else:
            current.append(word)
    runs.append(current)
    if len(runs) == 1:
        return [(segment.start, segment.end, segment.text)]
    return [(r[0].start, r[-1].end, " ".join(w.text for w in r)) for r in runs]


def format_transcript(segments):
    """One line per stretch of speech, with a marker wherever nobody is speaking."""
    lines, last_end = [], None
    for segment in segments:
        for start, end, text in _pieces(segment):
            if last_end is not None and start - last_end > GAP_SECONDS:
                lines.append(
                    f"[{format_timestamp(last_end)}] (no speech for "
                    f"{_length(start - last_end)}: likely music or singing)"
                )
            lines.append(f"[{format_timestamp(start)}] {text}")
            last_end = end
    return "\n".join(lines)


def _length(seconds):
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes}:{secs:02d}"


def load_guidance(path=GUIDANCE_FILE):
    try:
        with open(path) as handle:
            return handle.read().strip() or DEFAULT_GUIDANCE
    except OSError:
        return DEFAULT_GUIDANCE


def build_prompt(segments, guidance):
    return USER_TEMPLATE.format(guidance=guidance, transcript=format_transcript(segments))


# --- LLM backends -----------------------------------------------------------


def _call_anthropic(system, user):
    import requests

    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    headers = {"anthropic-version": "2023-06-01", "content-type": "application/json"}
    if os.environ.get("ANTHROPIC_API_KEY"):
        headers["x-api-key"] = os.environ["ANTHROPIC_API_KEY"]
    else:
        headers["authorization"] = f"Bearer {os.environ['ANTHROPIC_AUTH_TOKEN']}"
    model = os.environ.get("SERMON_LLM_MODEL", "claude-haiku-5-5")
    response = requests.post(
        f"{base}/v1/messages",
        headers=headers,
        json={
            "model": model,
            "max_tokens": 600,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=300,
    )
    if response.status_code != 200:
        raise SuggestionError(
            f"The language model call failed ({response.status_code}): "
            f"{response.text[:300]}"
        )
    blocks = response.json().get("content", [])
    return "".join(b.get("text", "") for b in blocks), model


def _call_claude_cli(system, user):
    """Uses the local `claude` command (Claude Code), so no API key is needed."""
    model = os.environ.get("SERMON_LLM_MODEL", "haiku")
    result = subprocess.run(
        ["claude", "-p", "--model", model],
        input=f"{system}\n\n{user}",
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise SuggestionError(f"`claude` failed: {result.stderr.strip()[:300]}")
    return result.stdout, f"claude-cli:{model}"


def default_llm():
    chosen = os.environ.get("SERMON_LLM_PROVIDER", "").strip().lower()
    has_key = bool(
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    )
    if chosen == "claude-cli" or (not chosen and not has_key and shutil.which("claude")):
        return _call_claude_cli
    if chosen == "anthropic" or has_key:
        return _call_anthropic
    raise SuggestionError(
        "No language model is set up for auto-trim. Set ANTHROPIC_API_KEY, or "
        "install Claude Code (the `claude` command), or pass --start and --end."
    )


# --- parsing and verification ------------------------------------------------


def parse_json_object(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise SuggestionError("The model did not return JSON.")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        raise SuggestionError("The model returned JSON that could not be read.")


def _norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(text).lower())).strip()


def _word_stream(segments):
    """Every transcribed word as (token, start, end), in time order."""
    stream = []
    for segment in segments:
        for word in segment.words:
            for token in _norm(word.text).split():
                stream.append((token, word.start, word.end))
    return stream


def _phrase_tokens(phrase, position):
    tokens = _norm(phrase).split()
    return tokens[:PHRASE_WORDS] if position == "head" else tokens[-PHRASE_WORDS:]


def _find_in_words(phrase, stream, around, position):
    """
    Finds the exact words of `phrase` in the word stream, nearest the claimed
    time. Returns (first_index, last_index) into the stream, or None.
    """
    tokens = _phrase_tokens(phrase, position)
    if not tokens:
        return None
    n, best, best_distance = len(tokens), None, None
    for i in range(len(stream) - n + 1):
        if stream[i][1] < around - SEARCH_WINDOW - 60:
            continue
        if stream[i][1] > around + SEARCH_WINDOW + 60:
            break
        if all(stream[i + k][0] == tokens[k] for k in range(n)):
            reference = stream[i][1] if position == "head" else stream[i + n - 1][2]
            distance = abs(reference - around)
            if distance <= SEARCH_WINDOW and (best is None or distance < best_distance):
                best, best_distance = (i, i + n - 1), distance
    return best


def _find_phrase(phrase, segments, around, position):
    """
    Segment-level search, used when the transcript has no word timing. Returns
    the segment index where `phrase` begins (head) or ends (tail), or None.
    """
    needle = " ".join(_phrase_tokens(phrase, position))
    if not needle:
        return None
    candidates = [
        i for i, s in enumerate(segments) if abs(s.start - around) <= SEARCH_WINDOW
    ]
    for i in candidates:  # phrase inside one segment
        if needle in _norm(segments[i].text):
            return i
    for i in candidates:  # phrase straddling two segments
        if i + 1 < len(segments):
            joined = _norm(segments[i].text + " " + segments[i + 1].text)
            if needle in joined:
                return i if position == "head" else i + 1
    best, best_ratio = None, 0.0  # transcript wording can differ slightly
    for i in candidates:
        ratio = difflib.SequenceMatcher(None, needle, _norm(segments[i].text)).ratio()
        if ratio > best_ratio:
            best, best_ratio = i, ratio
    return best if best_ratio >= 0.75 else None


def _drop_across_pause(stream, hit, position, warnings):
    """
    If the quoted words contain a long pause, they are two separate utterances.
    Keep only the side that is the real boundary: for a start, the words after
    the last pause; for an end, the words before the first pause. Says so.
    """
    first, last = hit
    if position == "head":
        for k in range(last, first, -1):
            gap = stream[k][1] - stream[k - 1][2]
            if gap > LONG_PAUSE:
                warnings.append(
                    f"The start words had a {gap:.0f}s pause in the middle, so the cut "
                    f"was placed after it, at \"{stream[k][0]}\". Listen to it."
                )
                return k, last
    else:
        for k in range(first + 1, last + 1):
            gap = stream[k][1] - stream[k - 1][2]
            if gap > LONG_PAUSE:
                warnings.append(
                    f"The end words had a {gap:.0f}s pause in the middle, so the cut "
                    f"was placed before it, at \"{stream[k - 1][0]}\". Listen to it."
                )
                return first, k - 1
    return first, last


def _word_cut(stream, first, last, position):
    """
    Places a cut on a real word with a safety pad, but never inside the
    neighbouring word: if the next word on the far side is closer than the pad,
    the cut goes halfway into the gap instead.
    """
    if position == "head":
        edge = stream[first][1]
        cut = edge - START_PAD
        if first > 0 and cut < stream[first - 1][2]:
            previous_end = stream[first - 1][2]
            cut = previous_end + (edge - previous_end) / 2
        return cut
    edge = stream[last][2]
    cut = edge + END_PAD
    if last + 1 < len(stream) and cut > stream[last + 1][1]:
        next_start = stream[last + 1][1]
        cut = edge + (next_start - edge) / 2
    return cut


def _snap(quote, claimed, segments, stream, position, warnings):
    """
    Returns (cut_time, found). The cut sits on the real word when word timing is
    available, else on a trustworthy segment edge, else on the model's own time.
    """
    label = "start" if position == "head" else "end"
    pad = -START_PAD if position == "head" else END_PAD

    if stream:
        hit = _find_in_words(quote, stream, claimed, position)
        if hit:
            first, last = _drop_across_pause(stream, hit, position, warnings)
            return _word_cut(stream, first, last, position), True

    index = _find_phrase(quote, segments, claimed, position)
    if index is None:
        warnings.append(f"Could not find the {label} words near the claimed time.")
        return claimed + pad, False

    segment = segments[index]
    if segment.end - segment.start > MAX_TRUSTED_SEGMENT:
        warnings.append(
            f"The {label} words sit in a long stretch of transcript with no precise "
            f"timing, so the model's time was used. Listen to this cut."
        )
        return claimed + pad, True
    edge = segment.start if position == "head" else segment.end
    return edge + pad, True


def validate_and_snap(raw, segments, duration, model=""):
    try:
        claimed_start = float(raw["start_seconds"])
        claimed_end = float(raw["end_seconds"])
        start_quote = str(raw.get("start_quote", ""))
        end_quote = str(raw.get("end_quote", ""))
    except (KeyError, TypeError, ValueError):
        raise SuggestionError("The model's answer was missing start or end times.")

    warnings = []
    stream = _word_stream(segments)
    start, start_found = _snap(start_quote, claimed_start, segments, stream, "head", warnings)
    end, end_found = _snap(end_quote, claimed_end, segments, stream, "tail", warnings)
    quotes_found = start_found and end_found  # "verified": the words exist where claimed

    start = max(0.0, start)
    end = min(duration, end)
    if end <= start:
        raise SuggestionError("The suggested end is not after the suggested start.")

    for label, cut, claimed, pad in (
        ("start", start, claimed_start, -START_PAD),
        ("end", end, claimed_end, END_PAD),
    ):
        shift = abs(cut - (claimed + pad))
        if shift > MAX_SNAP_SHIFT and cut not in (0.0, duration):
            warnings.append(
                f"The {label} cut is {shift:.0f}s away from the time the model gave. "
                f"Listen to it before trusting it."
            )
    if end - start < MIN_SERMON_SECONDS:
        warnings.append(
            f"That is only {format_timestamp(end - start)} long, shorter than a "
            f"typical sermon."
        )

    return TrimSuggestion(
        start=start,
        end=end,
        start_quote=start_quote,
        end_quote=end_quote,
        confidence=str(raw.get("confidence", "unknown")),
        reasoning=str(raw.get("reasoning", "")),
        verified=quotes_found,
        warnings=warnings,
        model=model,
        alternatives=_snap_alternatives(raw.get("alternatives"), segments, stream, duration),
    )


def _snap_alternatives(raw_alternatives, segments, stream, duration):
    """Places each alternative cut on its real words; drops ones that can't be found."""
    alternatives = []
    if not isinstance(raw_alternatives, list):
        return alternatives
    for item in raw_alternatives[:3]:
        try:
            which = str(item["which"]).lower()
            claimed = float(item["seconds"])
            quote = str(item.get("quote", ""))
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if which not in ("start", "end"):
            continue
        position = "head" if which == "start" else "tail"
        time, found = _snap(quote, claimed, segments, stream, position, [])
        if found:
            alternatives.append(
                {
                    "which": which,
                    "time": min(max(time, 0.0), duration),
                    "quote": quote,
                    "note": str(item.get("note", "")),
                }
            )
    return alternatives


def suggest_trim(
    audio_path,
    duration,
    cache_dir="cache/transcripts",
    segments=None,
    llm=None,
    guidance=None,
    progress=print,
    bar=None,
):
    """
    Transcribes the audio (cached) and asks a language model where the sermon
    starts and ends. `segments` and `llm` can be injected for testing; `bar` is
    an optional progress bar shown while transcribing.
    """
    if segments is None:
        segments = transcribe(audio_path, cache_dir=cache_dir, progress=progress, bar=bar)
    guidance = guidance if guidance is not None else load_guidance()
    llm = llm or default_llm()

    progress("Asking the language model where the sermon starts and ends...")
    text, model = llm(SYSTEM, build_prompt(segments, guidance))
    suggestion = validate_and_snap(parse_json_object(text), segments, duration, model)
    suggestion.segments = segments
    return suggestion
