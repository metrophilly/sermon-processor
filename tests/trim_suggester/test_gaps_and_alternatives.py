import pytest

from app.trim_suggester.suggest import format_transcript, validate_and_snap
from app.trim_suggester.transcribe import Segment, Word


def _words(start, tokens, step=0.4):
    return [Word(start + i * step, start + i * step + 0.3, t) for i, t in enumerate(tokens)]


def test_silence_between_segments_is_marked():
    segments = [
        Segment(0.0, 5.0, "Amen."),
        Segment(250.0, 255.0, "Welcome back."),
    ]
    text = format_transcript(segments)
    assert "(no speech for 4:05: likely music or singing)" in text
    assert text.splitlines()[-1] == "[0:04:10] Welcome back."


def test_one_segment_spanning_a_song_is_split_at_its_gap():
    # Whisper glued "let's sing" and the speech after a 4 minute song into one segment.
    words = _words(100.0, ["Let's", "all", "stand."]) + _words(340.0, ["Friends,", "welcome", "back."])
    segments = [Segment(100.0, 342.0, "Let's all stand. Friends, welcome back.", words)]

    lines = format_transcript(segments).splitlines()

    assert lines[0] == "[0:01:40] Let's all stand."
    assert "no speech for 3:59" in lines[1]  # measured from the last word's end
    assert lines[2] == "[0:05:40] Friends, welcome back."


def test_a_segment_without_gaps_keeps_its_original_text():
    words = _words(0.0, ["Hello", "there."])
    assert format_transcript([Segment(0.0, 2.0, "Hello there.", words)]) == "[0:00:00] Hello there."


def _service():
    return [
        Segment(100.0, 110.0, "Today's scripture reading comes from the book of Exodus."),
        Segment(4640.0, 4650.0, "We pray all the things in Jesus' name, Amen."),
        Segment(4900.0, 4910.0, "That is my prayer for you this week."),
    ]


RAW = {
    "start_seconds": 100,
    "start_quote": "Today's scripture reading comes from the book of Exodus",
    "end_seconds": 4649,
    "end_quote": "We pray all the things in Jesus' name, Amen.",
    "confidence": "medium",
    "reasoning": "x",
}


def test_alternatives_are_placed_on_their_real_words():
    raw = dict(RAW, alternatives=[{
        "which": "end", "seconds": 4909, "quote": "That is my prayer for you this week.",
        "note": "preacher speaks again after the song",
    }])
    result = validate_and_snap(raw, _service(), 5000.0)

    assert len(result.alternatives) == 1
    alt = result.alternatives[0]
    assert alt["which"] == "end"
    assert alt["time"] == pytest.approx(4910.0 + 2.0)
    assert "after the song" in alt["note"]


def test_unverifiable_or_malformed_alternatives_are_dropped():
    raw = dict(RAW, alternatives=[
        {"which": "end", "seconds": 4909, "quote": "words that are not in the transcript at all"},
        {"which": "middle", "seconds": 100, "quote": "x"},
        {"seconds": 5},
        "nonsense",
    ])
    assert validate_and_snap(raw, _service(), 5000.0).alternatives == []


def test_missing_alternatives_is_fine():
    assert validate_and_snap(RAW, _service(), 5000.0).alternatives == []
    assert validate_and_snap(dict(RAW, alternatives="none"), _service(), 5000.0).alternatives == []
