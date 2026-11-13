import json
import os

from app.archive import db_import


def test_normalize_key_decodes_and_strips_the_leading_slash():
    assert db_import.normalize_key("/2012/2012-02/1-02%20Our%20True%20Joy.mp3") == "2012/2012-02/1-02 Our True Joy.mp3"
    assert db_import.normalize_key(None) is None


def test_sermon_row_joins_the_speaker_name_and_strips_drafts():
    row = db_import.sermon_row(
        {"_id": "drafts.abc", "title": "T", "slug": "t", "spokenDate": "2024-01-07T16:30:00.000Z",
         "speaker": {"firstName": "Andrew", "lastName": "Pae"}, "isPublished": True, "s3": "/2024/2024-01-07.mp3"},
        "2026-11-12T00:00:00+00:00",
    )
    assert row["id"] == "abc" and row["speakerName"] == "Andrew Pae" and row["s3AudioPath"] == "2024/2024-01-07.mp3"


def test_transcript_paragraphs_use_edited_text_and_group_edits_by_paragraph():
    transcript = {"paragraphs": [
        {"id": "p001", "index": 1, "start_ms": 0, "end_ms": 1000, "text": "a gospel -centered x", "avg_confidence": 0.9,
         "words": [{"id": "w1"}, {"id": "w2"}, {"id": "w3"}, {"id": "w4"}]},
        {"id": "p002", "index": 2, "start_ms": 1000, "end_ms": 2000, "text": "plain", "avg_confidence": 0.8, "words": [{"id": "w5"}]},
    ]}
    edit = {"rule": "r", "word_ids": ["w2", "w3"], "old": "gospel -centered", "new": "gospel-centered"}
    edited = {"paragraphs": [{"id": "p001", "text": "a gospel-centered x"}], "edits": [edit]}
    rows = db_import.transcript_paragraphs(transcript, edited)
    assert rows[0]["textEdited"] == "a gospel-centered x" and rows[0]["edits"] == [edit]
    assert rows[1]["textEdited"] == "plain" and rows[1]["edits"] is None


def test_copy_cells_escape_tabs_newlines_and_backslashes():
    assert db_import._cell("a\tb\nc\\d") == "a\\tb\\nc\\\\d"
    assert db_import._cell(None) == "\\N" and db_import._cell(True) == "t"
    assert json.loads(db_import._cell({"x": "a\tb"}).replace("\\t", "\\t")) is not None


def _plan(sha="s1"):
    paragraph = {"paragraphId": "p001", "position": 1, "startMs": 0, "endMs": 1, "textRaw": "r", "textEdited": "e",
                 "edits": None, "avgConfidence": 0.9}
    return {"sermons": [], "transcripts": [{"s3Key": "k.mp3", "audioSha256": sha, "durationSeconds": 1.0, "model": "m",
            "wordCount": 1, "fixesCommit": "abc", "generatedAt": "2026-01-01T00:00:00+00:00", "paragraphs": [paragraph]}]}


def test_same_audio_updates_in_place_and_new_audio_makes_a_new_version():
    sql, counts = db_import.build_sql(_plan("s1"), {"k.mp3": ("t1", 1, "s1")})
    assert counts == {"new": 0, "updated": 1, "retired": 0, "paragraphs": 1} and "COPY sermon_transcript" not in sql
    sql, counts = db_import.build_sql(_plan("s2"), {"k.mp3": ("t1", 1, "s1")})
    assert counts == {"new": 1, "updated": 0, "retired": 1, "paragraphs": 1}
    assert 'SET "isCurrent" = false WHERE id = \'t1\'' in sql and sql.index("isCurrent\" = false") < sql.index("COPY sermon_transcript")
