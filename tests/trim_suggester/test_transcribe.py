import json
import shutil
import subprocess
from unittest.mock import MagicMock

import pytest

from app.trim_suggester import SuggestionError
from app.trim_suggester import transcribe as transcribe_module
from app.trim_suggester.transcribe import Segment, default_provider, transcribe

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="no ffmpeg")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ("SERMON_STT_PROVIDER", "SERMON_STT_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(transcribe_module, "_local_available", lambda: False)


def test_no_backend_gives_actionable_message():
    with pytest.raises(SuggestionError, match="faster-whisper"):
        default_provider()


def test_provider_choice_order(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    assert default_provider() == "api"
    monkeypatch.setattr(transcribe_module, "_local_available", lambda: True)
    assert default_provider() == "local"  # free option wins when available
    monkeypatch.setenv("SERMON_STT_PROVIDER", "api")
    assert default_provider() == "api"  # explicit choice wins


def test_api_settings_pick_the_right_endpoint(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "g")
    assert "groq" in transcribe_module._api_settings()[0]
    monkeypatch.setenv("SERMON_STT_API_KEY", "custom")
    monkeypatch.setenv("SERMON_STT_BASE_URL", "https://stt.example/v1")
    assert transcribe_module._api_settings() == ("https://stt.example/v1", "custom", "whisper-1")


@needs_ffmpeg
def test_api_transcription_offsets_each_chunk_and_caches(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("SERMON_STT_PROVIDER", "api")
    monkeypatch.setattr(transcribe_module, "CHUNK_SECONDS", 5)  # force 3 chunks from 12s
    audio = tmp_path / "service.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=d=12", str(audio)],
        check=True,
    )

    calls = []

    def fake_post(url, headers, files, data, timeout):
        calls.append(url)
        response = MagicMock(status_code=200)
        response.json.return_value = {"segments": [{"start": 1.0, "end": 2.0, "text": " hi "}]}
        return response

    import requests
    monkeypatch.setattr(requests, "post", fake_post)

    cache = str(tmp_path / "cache")
    first = transcribe(str(audio), cache_dir=cache, progress=lambda *_: None)

    assert len(calls) == 3
    assert calls[0].endswith("/audio/transcriptions")
    starts = [round(s.start) for s in first]
    assert starts[0] == 1 and starts[1] == 6 and starts[2] == 11  # +0, +5, +10
    assert first[0].text == "hi"

    again = transcribe(str(audio), cache_dir=cache, progress=lambda *_: None)
    assert len(calls) == 3  # served from the saved transcript
    assert again == first


class FakeBar:
    def __init__(self):
        self.fractions = []
        self.closed = 0

    def __call__(self, fraction):
        self.fractions.append(round(fraction, 3))

    def close(self):
        self.closed += 1


@needs_ffmpeg
def test_api_transcription_reports_progress_per_part(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("SERMON_STT_PROVIDER", "api")
    monkeypatch.setattr(transcribe_module, "CHUNK_SECONDS", 5)  # 12s -> 3 parts
    audio = tmp_path / "service.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=d=12", str(audio)], check=True
    )
    import requests

    def fake_post(url, headers, files, data, timeout):
        response = MagicMock(status_code=200)
        response.json.return_value = {"segments": [{"start": 0.0, "end": 1.0, "text": "hi"}]}
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    messages = []
    bar = FakeBar()

    transcribe(str(audio), cache_dir=str(tmp_path / "c"), progress=messages.append, bar=bar)

    assert bar.fractions == [0.0, 0.333, 0.667, 1.0]
    assert bar.closed == 1
    assert not any("part" in m for m in messages)  # the bar replaces the text messages


@needs_ffmpeg
def test_the_bar_is_closed_even_when_transcription_fails(tmp_path, monkeypatch):
    audio = tmp_path / "a.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=d=2", str(audio)], check=True
    )
    bar = FakeBar()

    with pytest.raises(SuggestionError):  # local requested but not installed (fixture)
        transcribe(str(audio), cache_dir=str(tmp_path / "c"), provider="local",
                   progress=lambda *_: None, bar=bar)

    assert bar.closed == 1


def test_a_saved_transcript_shows_no_bar(tmp_path, monkeypatch):
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    cache = tmp_path / "c"
    cache.mkdir()
    saved = transcribe_module._cache_path(str(audio), str(cache), "local")
    with open(saved, "w") as handle:
        handle.write('[{"start": 0, "end": 1, "text": "hello", "words": []}]')
    bar = FakeBar()

    segments = transcribe(str(audio), cache_dir=str(cache), provider="local",
                          progress=lambda *_: None, bar=bar)

    assert segments[0].text == "hello"
    assert bar.fractions == [] and bar.closed == 0


@needs_ffmpeg
def test_api_error_is_reported_plainly(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "bad")
    monkeypatch.setenv("SERMON_STT_PROVIDER", "api")
    audio = tmp_path / "a.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=d=2", str(audio)], check=True
    )
    import requests
    monkeypatch.setattr(
        requests, "post",
        lambda *a, **k: MagicMock(status_code=401, text='{"error":"bad key"}'),
    )
    with pytest.raises(SuggestionError, match="401"):
        transcribe(str(audio), cache_dir=str(tmp_path / "c"), progress=lambda *_: None)
