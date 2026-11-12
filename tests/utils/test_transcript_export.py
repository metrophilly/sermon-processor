import json
import os

import pytest

from app.transcripts.build import (
    MAX_WORDS,
    all_words,
    build_transcript,
    clean_words,
    format_vtt_time,
    split_paragraphs,
    to_vtt,
)
from app.transcripts.export import audio_info, write_exports

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "..", "config", "transcript_schema.json")
AUDIO = {"file": "a.mp3", "sha256": "0" * 64, "duration_seconds": 100.0}
MODEL = {"engine": "test", "name": "t", "settings": {}}


def make_raw(count, gap_every=None, gap=1.0):
    """count words, 0.3 s each; a sentence ends every 12 words; optional pause after sentence ends."""
    raw, t = [], 0.0
    for i in range(count):
        text = f" word{i}" + ("." if (i + 1) % 12 == 0 else "")
        raw.append((t, t + 0.25, text, 0.9))
        t += 0.3
        if gap_every and (i + 1) % gap_every == 0:
            t += gap
    return raw


def build(raw):
    return build_transcript(raw, "sermon-1", "2022-06-26", AUDIO, MODEL)


def test_clean_words_assigns_stable_ids_and_integer_ms():
    words = clean_words([(0.0, 0.5, " Hello", 0.91234), (0.4, 0.3, "", 0.5), (0.6, 0.55, "world.", 1.2)])
    assert [w["id"] for w in words] == ["w000001", "w000002"]
    assert words[0]["start_ms"] == 0 and words[0]["end_ms"] == 500 and words[0]["confidence"] == 0.912
    assert words[1]["end_ms"] >= words[1]["start_ms"] and words[1]["confidence"] == 1.0


def test_paragraphs_stay_in_range_and_cover_every_word():
    transcript = build(make_raw(1200, gap_every=60))
    sizes = [p["word_count"] for p in transcript["paragraphs"]]
    assert sum(sizes) == 1200 and max(sizes) <= MAX_WORDS + 50
    assert all(s >= 100 for s in sizes[:-1])
    ids = [w["id"] for w in all_words(transcript)]
    assert ids == sorted(ids) and len(set(ids)) == 1200


def test_same_input_gives_same_ids_and_output():
    raw = make_raw(500, gap_every=60)
    assert json.dumps(build(raw), sort_keys=True) == json.dumps(build(raw), sort_keys=True)


def test_short_tail_is_merged():
    groups = split_paragraphs(clean_words(make_raw(260)))
    assert all(len(g) >= 50 for g in groups)


def test_validates_against_schema():
    jsonschema = pytest.importorskip("jsonschema")
    transcript = build(make_raw(400, gap_every=60))
    with open(SCHEMA) as handle:
        jsonschema.validate(transcript, json.load(handle))
    bad = json.loads(json.dumps(transcript))
    bad["paragraphs"][0]["words"][0]["confidence"] = 2
    with open(SCHEMA) as handle, pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, json.load(handle))


def test_vtt_is_well_formed():
    vtt = to_vtt(build(make_raw(300)))
    assert vtt.startswith("WEBVTT\n\n")
    cues = [b for b in vtt.split("\n\n")[1:] if b.strip()]
    assert len(cues) > 5
    previous_end = -1
    for cue in cues:
        timing, text = cue.split("\n", 1)
        start, end = [t.strip() for t in timing.split("-->")]
        assert len(start) == 12 and start < end and text.strip() and len(text) <= 100
        assert start >= (previous_end if isinstance(previous_end, str) else "")
        previous_end = end


def test_vtt_time_format():
    assert format_vtt_time(3723456) == "01:02:03.456" and format_vtt_time(0) == "00:00:00.000"


def test_write_exports_is_atomic_and_leaves_no_part_files(tmp_path):
    audio = tmp_path / "a.mp3"
    audio.write_bytes(b"abc")
    info = audio_info(str(audio), 12.3456)
    assert info["sha256"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    transcript = build_transcript(make_raw(50), "s", "2022-06-26", info, MODEL)
    json_path, vtt_path = write_exports(transcript, str(tmp_path / "out"), "2022-06-26")
    assert os.path.exists(json_path) and os.path.exists(vtt_path)
    assert not [f for f in os.listdir(tmp_path / "out") if f.endswith(".part")]
    assert json.load(open(json_path))["sermon_id"] == "s"
