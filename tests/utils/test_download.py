import os

import pytest

from app.utils.download import download_file


def test_downloads_then_reuses_the_cached_copy(tmp_path):
    source = tmp_path / "intro.wav"
    source.write_bytes(b"audio-bytes")
    destination = tmp_path / "cache" / "s3" / "audio_intro.wav"

    download_file(source.as_uri(), str(destination))
    assert destination.read_bytes() == b"audio-bytes"

    source.write_bytes(b"changed")  # a second call must not fetch again
    download_file(source.as_uri(), str(destination))
    assert destination.read_bytes() == b"audio-bytes"


def test_failed_download_leaves_nothing_that_looks_cached(tmp_path):
    destination = tmp_path / "cache" / "audio_intro.wav"
    with pytest.raises(OSError):
        download_file((tmp_path / "does-not-exist.wav").as_uri(), str(destination))
    assert not destination.exists()
    assert not os.path.exists(f"{destination}.part")


def test_an_empty_leftover_file_is_not_trusted(tmp_path):
    source = tmp_path / "intro.wav"
    source.write_bytes(b"real")
    destination = tmp_path / "audio_intro.wav"
    destination.write_bytes(b"")  # e.g. from an old failed run

    download_file(source.as_uri(), str(destination))
    assert destination.read_bytes() == b"real"
