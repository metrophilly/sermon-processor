"""
Regression tests for a real failure: Whisper stored "...Jesus' name, Amen. Let's
all stand and sing" in one segment that ran through four minutes of singing, and
the end cut snapped to that segment's far edge (1:21:34) instead of the "Amen"
(1:17:29).
"""

import json
import shutil
import subprocess
from unittest.mock import MagicMock

import pytest

from app.trim_suggester import suggest
from app.trim_suggester.suggest import END_PAD, validate_and_snap
from app.trim_suggester.transcribe import (
    Segment,
    Word,
    _cache_path,
    _segment_from_dict,
    _segment_to_dict,
)

DURATION = 5000.0
END_QUOTE = "We pray all the things in Jesus' name, Amen."
RAW = {
    "start_seconds": 100,
    "start_quote": "Today's scripture reading comes from the book of Exodus",
    "end_seconds": 4651,
    "end_quote": END_QUOTE,
    "confidence": "high",
    "reasoning": "x",
}


def _words(start, tokens, step=0.4):
    return [Word(start + i * step, start + i * step + 0.3, t) for i, t in enumerate(tokens)]


def _service(long_segment_words=None):
    start_seg = Segment(100.0, 110.0, "Today's scripture reading comes from the book of Exodus.")
    prayer_text = "Father we come to you. We pray all the"
    prayer = Segment(
        4640.0,
        4648.9,
        prayer_text,
        _words(4643.0, prayer_text.split()) if long_segment_words else [],
    )
    # The bad segment: "Amen" at ~4651, but the segment runs to 4894 (singing).
    long_text = "things in Jesus' name, Amen. Let's all stand and sing together."
    long_segment = Segment(4649.0, 4894.0, long_text, long_segment_words or [])
    return [start_seg, prayer, long_segment]


def test_long_segment_without_word_timing_does_not_overshoot():
    result = validate_and_snap(RAW, _service(), DURATION)

    assert result.end == pytest.approx(4651 + END_PAD)  # model's time, not 4896
    assert any("no precise timing" in w for w in result.warnings)


def test_word_timing_puts_the_cut_on_the_actual_amen():
    words = _words(4649.0, "things in Jesus' name, Amen. Let's all stand and sing together.".split())
    amen = words[4]
    result = validate_and_snap(RAW, _service(words), DURATION)

    next_word = words[5]  # "Let's" follows "Amen." almost immediately
    # The next word is closer than the full pad, so the cut goes halfway into the gap
    # instead of running into "Let's".
    assert result.end == pytest.approx(amen.end + (next_word.start - amen.end) / 2)
    assert result.end < next_word.start
    assert result.verified is True
    assert not any("no precise timing" in w for w in result.warnings)


def test_start_uses_the_first_word_not_the_segment_edge():
    start_words = _words(103.0, "Today's scripture reading comes from the book of Exodus.".split())
    segments = _service(_words(4649.0, "things in Jesus' name, Amen.".split()))
    segments[0] = Segment(100.0, 110.0, segments[0].text, start_words)

    result = validate_and_snap(RAW, segments, DURATION)

    assert result.start == pytest.approx(103.0 - 1.0)  # first word minus the pad


def test_repeated_phrase_picks_the_occurrence_nearest_the_claimed_time():
    words_early = _words(900.0, "in Jesus' name Amen".split())
    words_late = _words(4650.0, "in Jesus' name Amen".split())
    segments = [
        Segment(100.0, 110.0, "Today's scripture reading comes from the book of Exodus."),
        Segment(900.0, 903.0, "in Jesus' name Amen", words_early),
        Segment(4650.0, 4653.0, "in Jesus' name Amen", words_late),
    ]
    raw = dict(RAW, end_quote="in Jesus' name Amen")
    result = validate_and_snap(raw, segments, DURATION)

    assert result.end == pytest.approx(words_late[-1].end + END_PAD)


def test_cut_far_from_the_models_time_is_flagged():
    # Short, trustworthy segment, but the model's time was 90 seconds too early.
    segments = [
        Segment(100.0, 110.0, "Today's scripture reading comes from the book of Exodus."),
        Segment(4645.0, 4652.0, "We pray all the things in Jesus' name, Amen."),
    ]
    result = validate_and_snap(dict(RAW, end_seconds=4560), segments, DURATION)

    assert result.verified is True  # the words were found...
    assert any("away from the time the model gave" in w for w in result.warnings)


def test_segments_round_trip_through_the_saved_transcript():
    original = Segment(1.0, 2.0, "hello there", _words(1.0, ["hello", "there"]))
    assert _segment_from_dict(json.loads(json.dumps(_segment_to_dict(original)))) == original
    # Saved transcripts that predate word timing still load.
    assert _segment_from_dict({"start": 1, "end": 2, "text": "old"}).words == []


def test_old_style_cached_transcripts_are_not_reused(tmp_path):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    assert _cache_path(str(audio), str(tmp_path), "local").endswith("-local-words.json")


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_api_words_are_attached_to_their_segments(tmp_path, monkeypatch):
    import requests

    from app.trim_suggester import transcribe as transcribe_module

    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("SERMON_STT_PROVIDER", "api")
    monkeypatch.setattr(transcribe_module, "_local_available", lambda: False)
    audio = tmp_path / "a.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=d=3", str(audio)], check=True
    )

    def fake_post(url, headers, files, data, timeout):
        assert ("timestamp_granularities[]", "word") in data
        response = MagicMock(status_code=200)
        response.json.return_value = {
            "segments": [{"start": 0.0, "end": 1.0, "text": " hello there"},
                         {"start": 1.0, "end": 2.0, "text": " general"}],
            "words": [{"word": "hello", "start": 0.0, "end": 0.4},
                      {"word": "there", "start": 0.5, "end": 0.9},
                      {"word": "general", "start": 1.1, "end": 1.8}],
        }
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    segments = transcribe_module.transcribe(
        str(audio), cache_dir=str(tmp_path / "c"), progress=lambda *_: None
    )

    assert [w.text for w in segments[0].words] == ["hello", "there"]
    assert [w.text for w in segments[1].words] == ["general"]
