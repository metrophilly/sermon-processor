"""
Build the exported transcript (DT-247) from raw word timings.

Pure functions, no speech engine needed. The raw input is a list of
`(start_seconds, end_seconds, text, confidence)` tuples, one per word, taken
from the audio file that the times belong to. The result is the `raw` layer: the
machine text, never edited. Edits and corrections live in a separate layer
(DT-256) that points at these word IDs.

Word IDs are `w000001`, `w000002`, ... in order, and paragraph IDs are `p001`,
... Rebuilding from the same raw words always gives the same IDs. The audio
file's SHA-256 is stored so a changed file can be detected.
"""

SCHEMA_VERSION = 1
MIN_WORDS = 150  # a paragraph may end at a pause once it has this many words
TARGET_WORDS = 200  # ...or at any sentence end once it has this many
MAX_WORDS = 250  # hard stop
PAUSE_SECONDS = 0.6
SHORT_TAIL_WORDS = 50  # a shorter last paragraph is merged into the one before

SENTENCE_END = (".", "?", "!")


def clean_words(raw_words):
    """Raw tuples -> word dicts with integer milliseconds, in order, no empty words."""
    words, prev_start, prev_end = [], 0, 0
    for start, end, text, confidence in raw_words:
        text = (text or "").strip()
        if not text:
            continue
        start_ms = max(round(float(start) * 1000), prev_start)
        end_ms = max(round(float(end) * 1000), start_ms)
        words.append(
            {
                "id": f"w{len(words) + 1:06d}",
                "start_ms": start_ms,
                "end_ms": end_ms,
                "text": text,
                "confidence": round(min(1.0, max(0.0, float(confidence))), 3),
            }
        )
        prev_start, prev_end = start_ms, end_ms
    return words


def split_paragraphs(words):
    """Groups of about 150 to 250 words, ending at a sentence end after a pause."""
    groups, current = [], []
    for i, word in enumerate(words):
        current.append(word)
        if i + 1 == len(words):
            break
        gap = (words[i + 1]["start_ms"] - word["end_ms"]) / 1000.0
        sentence_end = word["text"].endswith(SENTENCE_END)
        count = len(current)
        if (
            count >= MAX_WORDS
            or (count >= TARGET_WORDS and sentence_end)
            or (count >= MIN_WORDS and sentence_end and gap >= PAUSE_SECONDS)
        ):
            groups.append(current)
            current = []
    if current:
        if groups and len(current) < SHORT_TAIL_WORDS:
            groups[-1].extend(current)
        else:
            groups.append(current)
    return groups


def _paragraph(index, group):
    confidences = [w["confidence"] for w in group]
    return {
        "id": f"p{index:03d}",
        "index": index,
        "start_ms": group[0]["start_ms"],
        "end_ms": group[-1]["end_ms"],
        "text": " ".join(w["text"] for w in group),
        "word_count": len(group),
        "avg_confidence": round(sum(confidences) / len(confidences), 3),
        "min_confidence": min(confidences),
        "words": group,
    }


def build_transcript(raw_words, sermon_id, date, audio, model, generated_at=None):
    """
    `audio`: {"file": name, "sha256": hex, "duration_seconds": float}
    `model`: {"engine": ..., "name": ..., "settings": {...}}
    Returns the transcript dict (layer "raw"), ready to write as JSON.
    """
    words = clean_words(raw_words)
    paragraphs = [_paragraph(i + 1, g) for i, g in enumerate(split_paragraphs(words))]
    transcript = {
        "schema_version": SCHEMA_VERSION,
        "layer": "raw",
        "sermon_id": sermon_id,
        "date": date,
        "audio": audio,
        "model": model,
        "word_count": len(words),
        "paragraphs": paragraphs,
    }
    if generated_at:
        transcript["generated_at"] = generated_at
    return transcript


def all_words(transcript):
    return [w for p in transcript["paragraphs"] for w in p["words"]]


def format_vtt_time(ms):
    hours, rest = divmod(int(ms), 3600000)
    minutes, rest = divmod(rest, 60000)
    seconds, millis = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"


def to_vtt(transcript, max_chars=84, max_seconds=7.0, min_chars=40):
    """WebVTT captions from the word list. Cues end at sentence ends where they can."""
    cues, current = [], []
    words = all_words(transcript)

    def flush():
        if current:
            cues.append((current[0]["start_ms"], current[-1]["end_ms"], " ".join(w["text"] for w in current)))
            current.clear()

    for word in words:
        length = sum(len(w["text"]) + 1 for w in current) + len(word["text"])
        too_long = current and (
            length > max_chars or (word["end_ms"] - current[0]["start_ms"]) / 1000.0 > max_seconds
        )
        if too_long:
            flush()
        current.append(word)
        chars = sum(len(w["text"]) + 1 for w in current)
        if word["text"].endswith(SENTENCE_END) and chars >= min_chars:
            flush()
    flush()
    lines = ["WEBVTT", ""]
    previous_end = 0
    for start, end, text in cues:
        start = max(start, previous_end)
        end = max(end, start + 1)
        lines += [f"{format_vtt_time(start)} --> {format_vtt_time(end)}", text, ""]
        previous_end = end
    return "\n".join(lines)
