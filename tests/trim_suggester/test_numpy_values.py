"""
faster-whisper returns NumPy numbers. A run once crashed at the very end
("Object of type bool is not JSON serializable") because a comparison of those
numbers produced a NumPy bool. Transcripts must hand back plain Python floats.
"""

import sys
import types

import pytest

numpy = pytest.importorskip("numpy")

from app.trim_suggester import transcribe as transcribe_module  # noqa: E402


class NumpyWord:
    def __init__(self, start, end, word):
        self.start, self.end, self.word = numpy.float64(start), numpy.float32(end), word


class NumpySegment:
    def __init__(self, start, end, text, words):
        self.start, self.end, self.text = numpy.float64(start), numpy.float64(end), text
        self.words = words


@pytest.fixture
def fake_faster_whisper(monkeypatch):
    class WhisperModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, samples, **kwargs):
            words = [NumpyWord(0.0, 0.4, " Hello"), NumpyWord(0.4, 0.9, " there.")]
            return iter([NumpySegment(0.0, 1.0, " Hello there.", words)]), None

    module = types.ModuleType("faster_whisper")
    module.WhisperModel = WhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", module)
    monkeypatch.setattr(transcribe_module, "_decode_to_samples", lambda path: None)


def test_local_transcription_returns_plain_python_floats(fake_faster_whisper):
    fractions = []

    segments = transcribe_module._transcribe_local(
        "x.wav", 10.0, progress=lambda *_: None, bar=fractions.append
    )

    segment = segments[0]
    assert type(segment.start) is float and type(segment.end) is float
    for word in segment.words:
        assert type(word.start) is float and type(word.end) is float
    assert all(type(f) is float for f in fractions)


def test_comparing_transcript_times_gives_real_booleans(fake_faster_whisper):
    segments = transcribe_module._transcribe_local("x.wav", 10.0, progress=lambda *_: None)
    result = abs(segments[0].start - segments[0].end) > 0.01
    assert type(result) is bool  # a NumPy bool here is what broke JSON saving
