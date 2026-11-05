"""
Where exactly a cut lands relative to the neighbouring words. Based on a real
failure: the start cut fell inside "slash events" because the model's quote began
with the presider's "Thank you." and the 1 second pad reached back into the
previous word.
"""

import pytest

from app.trim_suggester.suggest import END_PAD, START_PAD, validate_and_snap
from app.trim_suggester.transcribe import Segment, Word

DURATION = 5000.0


def _w(text, start, end):
    return Word(start, end, text)


# Real timings (seconds) from the transcript around the start of the reading.
ANNOUNCEMENTS_THEN_READING = [
    _w("slash", 3050.3, 3050.7), _w("events.", 3050.7, 3051.1),
    _w("Thank", 3051.5, 3051.6), _w("you.", 3051.6, 3051.8),
    # 8.7 seconds of quiet
    _w("Today's", 3060.5, 3061.2), _w("scripture", 3061.2, 3061.3), _w("reading", 3061.3, 3061.7),
    _w("comes", 3061.7, 3062.1), _w("from", 3062.1, 3062.5), _w("the", 3062.5, 3062.8),
    _w("Book", 3062.8, 3063.0), _w("of", 3063.0, 3063.1), _w("Exodus.", 3063.1, 3063.5),
]
# ...and the prayer's end, with the worship leader starting 1.5 seconds later.
PRAYER = [
    _w("in", 4629.0, 4629.2), _w("Jesus'", 4629.2, 4629.4), _w("name.", 4629.6, 4629.8),
    _w("Amen.", 4630.2, 4630.4), _w("Let's", 4631.9, 4632.3), _w("all", 4632.3, 4632.4),
]


def _segments(*word_groups):
    return [Segment(g[0].start, g[-1].end, " ".join(w.text for w in g), g) for g in word_groups]


def _raw(start_quote, end_quote, start=3050, end=4630):
    return {"start_seconds": start, "start_quote": start_quote,
            "end_seconds": end, "end_quote": end_quote, "confidence": "high"}


def test_a_start_quote_spanning_a_long_pause_starts_after_the_pause():
    segments = _segments(ANNOUNCEMENTS_THEN_READING, PRAYER)
    raw = _raw("Thank you. Today's scripture reading comes from the Book of Exodus.",
               "in Jesus' name. Amen.")

    result = validate_and_snap(raw, segments, DURATION)

    # Starts at "Today's" (minus the pad), not at "Thank you.".
    assert result.start == pytest.approx(3060.5 - START_PAD)
    assert any("pause in the middle" in w and "start" in w for w in result.warnings)


def test_a_start_quote_without_a_pause_is_untouched():
    segments = _segments(ANNOUNCEMENTS_THEN_READING, PRAYER)
    raw = _raw("Today's scripture reading comes from the Book of Exodus.", "in Jesus' name. Amen.")

    result = validate_and_snap(raw, segments, DURATION)

    assert result.start == pytest.approx(3060.5 - START_PAD)
    assert not any("pause in the middle" in w for w in result.warnings)


def test_the_cut_never_lands_inside_the_previous_word():
    # "Thank you." directly after "events." with only 0.4s between them.
    segments = _segments(ANNOUNCEMENTS_THEN_READING, PRAYER)
    raw = _raw("Thank you.", "in Jesus' name. Amen.", start=3051)

    result = validate_and_snap(raw, segments, DURATION)

    previous_end, first_start = 3051.1, 3051.5
    assert result.start == pytest.approx(previous_end + (first_start - previous_end) / 2)
    assert previous_end < result.start < first_start  # in the gap, not in "events."


def test_the_end_cut_never_runs_into_the_next_speakers_first_word():
    segments = _segments(ANNOUNCEMENTS_THEN_READING, PRAYER)
    raw = _raw("Today's scripture reading comes from the Book of Exodus.", "in Jesus' name. Amen.")

    result = validate_and_snap(raw, segments, DURATION)

    amen_end, lets_start = 4630.4, 4631.9
    assert result.end == pytest.approx(amen_end + (lets_start - amen_end) / 2)
    assert result.end < lets_start  # the full 2s pad would have reached 4632.4


def test_plenty_of_room_means_the_full_pad_is_used():
    words = [_w("Amen.", 100.0, 100.4), _w("Later", 160.0, 160.4)]
    start_words = [_w("Hello", 10.0, 10.4), _w("everyone", 10.4, 10.9)]
    segments = _segments(start_words, words)
    raw = {"start_seconds": 10, "start_quote": "Hello everyone",
           "end_seconds": 100, "end_quote": "Amen.", "confidence": "high"}

    result = validate_and_snap(raw, segments, DURATION)

    assert result.end == pytest.approx(100.4 + END_PAD)


def test_an_end_quote_spanning_a_long_pause_ends_before_it():
    words = [_w("Amen.", 100.0, 100.4), _w("Let's", 108.0, 108.3), _w("sing", 108.3, 108.6)]
    start_words = [_w("Hello", 10.0, 10.4), _w("everyone", 10.4, 10.9)]
    raw = {"start_seconds": 10, "start_quote": "Hello everyone",
           "end_seconds": 100, "end_quote": "Amen. Let's sing", "confidence": "high"}

    result = validate_and_snap(raw, _segments(start_words, words), DURATION)

    assert result.end == pytest.approx(100.4 + END_PAD)  # at "Amen.", not "sing"
    assert any("pause in the middle" in w and "end" in w for w in result.warnings)
