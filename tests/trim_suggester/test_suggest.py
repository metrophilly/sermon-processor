import json

import pytest

from app.trim_suggester import SuggestionError, suggest_trim
from app.trim_suggester.suggest import (
    END_PAD,
    START_PAD,
    parse_json_object,
    validate_and_snap,
)
from app.trim_suggester.transcribe import Segment

# A tiny stand-in for a service: songs, announcements, sermon, closing song.
SEGMENTS = [Segment(i * 10.0, i * 10.0 + 9.5, text) for i, text in enumerate([
    "Great is thy faithfulness oh God my father",       # 0   0s
    "Welcome everyone and a few announcements today",   # 1  10s
    "Please sign up for the fall community groups",     # 2  20s
    "Let's pray before we open God's word together",    # 3  30s
    "Good morning church turn with me to Romans eight", # 4  40s  <- sermon starts
    "There is therefore now no condemnation",           # 5  50s
    "For those who are in Christ Jesus",                # 6  60s
    "And that is the good news of the gospel amen",     # 7  70s  <- sermon ends
    "Let's stand and sing our closing song",            # 8  80s
    "Amazing grace how sweet the sound",                # 9  90s
])]
DURATION = 100.0

GOOD = {
    "start_seconds": 40,
    "start_quote": "Good morning church turn with me to Romans eight",
    "end_seconds": 79,
    "end_quote": "And that is the good news of the gospel amen",
    "confidence": "high",
    "reasoning": "Preacher opens with a greeting and closes with amen.",
}


def test_snaps_to_segment_edges_with_padding():
    result = validate_and_snap(GOOD, SEGMENTS, DURATION)
    assert result.start == pytest.approx(40.0 - START_PAD)
    assert result.end == pytest.approx(79.5 + END_PAD)
    assert result.verified is True


def test_corrects_a_model_timestamp_that_is_a_bit_off():
    off = dict(GOOD, start_seconds=47, end_seconds=88)  # quotes still point to 40s / 70s
    result = validate_and_snap(off, SEGMENTS, DURATION)
    assert result.start == pytest.approx(40.0 - START_PAD)
    assert result.end == pytest.approx(79.5 + END_PAD)


def test_quote_must_be_near_the_claimed_time():
    # The words exist in the transcript, but ~14 minutes away from the claimed end.
    far = dict(GOOD, end_seconds=900)
    result = validate_and_snap(far, SEGMENTS, 1000.0)
    assert result.verified is False
    assert any("end words" in w for w in result.warnings)


def test_hallucinated_quote_is_flagged_not_trusted():
    fake = dict(GOOD, end_quote="and now a completely invented closing sentence here")
    result = validate_and_snap(fake, SEGMENTS, DURATION)
    assert result.verified is False
    assert any("end words" in w for w in result.warnings)
    assert result.end == pytest.approx(79 + END_PAD)  # falls back to the claimed time


def test_quote_spanning_two_segments_is_found():
    spanning = dict(GOOD, end_quote="gospel amen let's stand and sing")
    result = validate_and_snap(spanning, SEGMENTS, DURATION)
    assert result.verified is True


def test_times_are_clamped_to_the_file():
    edge = dict(GOOD, start_seconds=0.2, start_quote="Great is thy faithfulness oh God")
    result = validate_and_snap(edge, SEGMENTS, DURATION)
    assert result.start == 0.0


def test_short_sermon_gets_a_warning_but_is_still_verified():
    result = validate_and_snap(GOOD, SEGMENTS, DURATION)
    assert any("shorter than a typical sermon" in w for w in result.warnings)
    assert result.verified is True  # the words were found; only the length is odd


def test_end_before_start_is_an_error():
    bad = dict(GOOD, start_seconds=70, start_quote="And that is the good news",
               end_seconds=40, end_quote="Good morning church turn with me")
    with pytest.raises(SuggestionError):
        validate_and_snap(bad, SEGMENTS, DURATION)


def test_missing_fields_are_an_error():
    with pytest.raises(SuggestionError):
        validate_and_snap({"reasoning": "?"}, SEGMENTS, DURATION)


def test_parse_json_object_tolerates_chatter_and_fences():
    wrapped = "Sure!\n```json\n" + json.dumps(GOOD) + "\n```\nHope that helps."
    assert parse_json_object(wrapped)["start_seconds"] == 40
    for junk in ("no json here", "{broken"):
        with pytest.raises(SuggestionError):
            parse_json_object(junk)


def test_suggest_trim_end_to_end_with_a_fake_model():
    seen = {}

    def fake_llm(system, user):
        seen["prompt"] = user
        return json.dumps(GOOD), "fake-model"

    result = suggest_trim(
        "ignored.wav", DURATION, segments=SEGMENTS, llm=fake_llm,
        guidance="GUIDANCE-MARKER", progress=lambda *_: None,
    )

    assert result.model == "fake-model"
    assert "GUIDANCE-MARKER" in seen["prompt"]
    assert "[0:00:40] Good morning church" in seen["prompt"]  # timestamped lines
    assert result.start == pytest.approx(40.0 - START_PAD)
