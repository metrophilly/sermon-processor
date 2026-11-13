import copy
import hashlib
import json

import pytest

from app.transcripts import fixes
from app.transcripts.build import build_transcript

MODEL = {"engine": "fake", "name": "f", "settings": {}}
AUDIO = {"file": "a.mp3", "sha256": "0" * 64, "duration_seconds": 60}


def make(text):
    words = [(i * 0.3, i * 0.3 + 0.25, t, 0.9) for i, t in enumerate(text.split())]
    return build_transcript(words, "s1", "2026-01-04", AUDIO, MODEL)


def test_shipped_rules_load_and_have_unique_ids():
    rules = fixes.load_rules()
    assert len(rules) >= 10 and len({r["id"] for r in rules}) == len(rules)


def test_fixes_web_address_and_hyphen_and_keeps_trailing_punctuation():
    t = make("visit us at MetroPhilly .org. We are a gospel -centered church")
    edited = fixes.apply_fixes(t, fixes.load_rules())
    text = edited["paragraphs"][0]["text"]
    assert "MetroPhilly.org." in text and "gospel-centered" in text
    assert edited["edit_count"] == 2
    assert edited["edits"][0]["word_ids"] == ["w000004", "w000005"]


def test_numbered_book_matches_but_not_across_punctuation():
    t = make("turn to first Corinthians chapter 13 and then first, John said hello")
    edited = fixes.apply_fixes(t, fixes.load_rules())
    text = edited["paragraphs"][0]["text"]
    assert "1 Corinthians" in text and "first, John" in text
    assert edited["edit_count"] == 1


def test_raw_transcript_is_never_changed():
    t = make("visit MetroPhilly .org today")
    before = copy.deepcopy(t)
    fixes.apply_fixes(t, fixes.load_rules())
    assert t == before


def test_no_edits_gives_empty_layer():
    edited = fixes.apply_fixes(make("nothing to fix here"), fixes.load_rules())
    assert edited["edit_count"] == 0 and edited["paragraphs"] == []


def test_bad_rule_is_rejected(tmp_path):
    path = tmp_path / "f.json"
    path.write_text(json.dumps({"rules": [{"id": "x", "find": []}]}))
    with pytest.raises(ValueError):
        fixes.load_rules(str(path))


def test_cli_writes_edited_file_and_leaves_raw_bytes_alone(tmp_path):
    from app import cli

    raw = tmp_path / "2026-01-04.transcript.json"
    raw.write_text(json.dumps(make("visit MetroPhilly .org today")))
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    out = []
    assert cli.main(["fixes", str(tmp_path)], print_fn=out.append) == 0
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == digest
    edited = json.loads((tmp_path / "2026-01-04.edited.json").read_text())
    assert edited["edit_count"] == 1 and edited["layer"] == "edited"
    assert cli.main(["fixes", "--dry-run", str(tmp_path)], print_fn=out.append) == 0
