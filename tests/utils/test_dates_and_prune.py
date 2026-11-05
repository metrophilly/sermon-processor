import datetime
import os

import pytest

from app.utils.dates import last_sunday, validate_date
from app.utils.prune import prune_cache


@pytest.mark.parametrize(
    "today,expected",
    [
        (datetime.date(2026, 11, 8), "2026-11-08"),  # Sunday -> itself
        (datetime.date(2026, 11, 9), "2026-11-08"),  # Monday
        (datetime.date(2026, 11, 12), "2026-11-08"),  # Thursday
        (datetime.date(2026, 11, 14), "2026-11-08"),  # Saturday
        (datetime.date(2026, 1, 1), "2025-12-28"),  # across a year boundary
    ],
)
def test_last_sunday(today, expected):
    assert last_sunday(today) == expected


def test_validate_date():
    assert validate_date("2026-11-01") == "2026-11-01"
    for bad in ("11/01/2026", "2026-13-01", "", "yesterday"):
        with pytest.raises(ValueError):
            validate_date(bad)


def _make(path, age_days, now):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write("x")
    stamp = now - age_days * 86400
    os.utime(path, (stamp, stamp))


def test_prune_removes_only_old_files_in_prunable_folders(tmp_path):
    now = 1_800_000_000
    cache = str(tmp_path)
    old_audio = f"{cache}/audio/old.wav"
    new_audio = f"{cache}/audio/new.wav"
    old_transcript = f"{cache}/transcripts/old.json"
    old_intro = f"{cache}/s3/audio_intro.wav"  # must never be touched
    _make(old_audio, 40, now)
    _make(new_audio, 3, now)
    _make(old_transcript, 40, now)
    _make(old_intro, 400, now)

    removed = prune_cache(cache, keep_days=28, now=now)

    assert sorted(removed) == sorted([old_audio, old_transcript])
    assert os.path.exists(new_audio)
    assert os.path.exists(old_intro)


def test_prune_disabled_with_zero_days(tmp_path):
    now = 1_800_000_000
    path = f"{tmp_path}/audio/old.wav"
    _make(path, 400, now)
    assert prune_cache(str(tmp_path), keep_days=0, now=now) == []
    assert os.path.exists(path)


def test_prune_handles_missing_cache(tmp_path):
    assert prune_cache(str(tmp_path / "nope"), keep_days=28) == []
