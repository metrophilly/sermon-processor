"""
Speech-to-text with timestamps, with two interchangeable backends:

  local  faster-whisper on this machine. Free, no account, slower.
         Needs `pip install faster-whisper`.
  api    Any OpenAI-compatible /audio/transcriptions endpoint (OpenAI, Groq...).
         Cheap and fast. Needs an API key.

Which one runs is chosen by SERMON_STT_PROVIDER ("local" or "api"), otherwise
local if faster-whisper is installed, otherwise api if a key is set.

Transcripts are cached by file, so adjusting a cut and re-running does not pay
for transcription twice.
"""

import glob
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List

from app.steps.render_audio_step import probe_audio_duration
from app.trim_suggester.errors import SuggestionError

CHUNK_SECONDS = 1200  # 20 min of 32 kbps mono mp3 is ~5 MB, far under API limits


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: List[Word] = field(default_factory=list)  # empty if the backend gave none


def _segment_from_dict(item):
    words = [Word(**w) for w in item.get("words", [])]
    return Segment(item["start"], item["end"], item["text"], words)


def _segment_to_dict(segment):
    return {
        "start": segment.start,
        "end": segment.end,
        "text": segment.text,
        "words": [w.__dict__ for w in segment.words],
    }


def _api_settings():
    """Returns (base_url, api_key, model) for the first configured API, or None."""
    model_override = os.environ.get("SERMON_STT_MODEL")
    if os.environ.get("SERMON_STT_API_KEY"):
        return (
            os.environ.get("SERMON_STT_BASE_URL", "https://api.openai.com/v1"),
            os.environ["SERMON_STT_API_KEY"],
            model_override or "whisper-1",
        )
    if os.environ.get("GROQ_API_KEY"):
        return (
            "https://api.groq.com/openai/v1",
            os.environ["GROQ_API_KEY"],
            model_override or "whisper-large-v3-turbo",
        )
    if os.environ.get("OPENAI_API_KEY"):
        return (
            "https://api.openai.com/v1",
            os.environ["OPENAI_API_KEY"],
            model_override or "whisper-1",
        )
    return None


def _local_available():
    try:
        import faster_whisper  # noqa: F401

        return True
    except ImportError:
        return False


def default_provider():
    chosen = os.environ.get("SERMON_STT_PROVIDER", "").strip().lower()
    if chosen in ("local", "api"):
        return chosen
    if _local_available():
        return "local"
    if _api_settings():
        return "api"
    raise SuggestionError(
        "No transcription is set up. Pick one:\n"
        "  free, on this computer:  pip install faster-whisper\n"
        "  cheap, hosted:           set GROQ_API_KEY or OPENAI_API_KEY\n"
        "Or skip auto-trim by passing --start and --end."
    )


def _cache_path(audio_path, cache_dir, provider):
    stat = os.stat(audio_path)
    stem = os.path.splitext(os.path.basename(audio_path))[0]
    # "words" in the name: transcripts saved before word timing existed are ignored.
    return os.path.join(
        cache_dir, f"{stem}-{stat.st_size}-{int(stat.st_mtime)}-{provider}-words.json"
    )


def _extract_chunks(audio_path, workdir):
    pattern = os.path.join(workdir, "chunk%03d.mp3")
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", audio_path, "-vn",
            "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "32k",
            "-f", "segment", "-segment_time", str(CHUNK_SECONDS),
            "-reset_timestamps", "1", pattern,
        ],
        check=True,
    )
    return sorted(glob.glob(os.path.join(workdir, "chunk*.mp3")))


def _transcribe_api(audio_path, progress):
    import requests

    settings = _api_settings()
    if not settings:
        raise SuggestionError(
            "SERMON_STT_PROVIDER=api but no API key is set "
            "(SERMON_STT_API_KEY, GROQ_API_KEY or OPENAI_API_KEY)."
        )
    base_url, api_key, model = settings

    segments = []
    with tempfile.TemporaryDirectory() as workdir:
        chunks = _extract_chunks(audio_path, workdir)
        offset = 0.0
        for index, chunk in enumerate(chunks):
            progress(f"Transcribing part {index + 1} of {len(chunks)}...")
            with open(chunk, "rb") as handle:
                response = requests.post(
                    f"{base_url.rstrip('/')}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    files={"file": (os.path.basename(chunk), handle, "audio/mpeg")},
                    data=[
                        ("model", model),
                        ("response_format", "verbose_json"),
                        ("timestamp_granularities[]", "segment"),
                        ("timestamp_granularities[]", "word"),
                        ("language", "en"),
                    ],
                    timeout=900,
                )
            if response.status_code != 200:
                raise SuggestionError(
                    f"Transcription failed ({response.status_code}): "
                    f"{response.text[:300]}"
                )
            body = response.json()
            part = [
                Segment(
                    offset + float(item["start"]),
                    offset + float(item["end"]),
                    item["text"].strip(),
                )
                for item in body.get("segments", [])
            ]
            for word in body.get("words", []):  # words arrive as one flat list
                start = offset + float(word["start"])
                for segment in part:
                    if segment.start - 0.05 <= start < segment.end + 0.05:
                        segment.words.append(
                            Word(start, offset + float(word["end"]), word["word"].strip())
                        )
                        break
            segments.extend(part)
            offset += probe_audio_duration(chunk)
    return segments


def _decode_to_samples(audio_path):
    """Decodes any audio file to 16 kHz mono float samples using our own ffmpeg.

    Done here instead of letting faster-whisper decode, because its bundled
    decoder (PyAV) is a frequent source of version-mismatch crashes.
    """
    import numpy

    result = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", audio_path, "-vn", "-ac", "1", "-ar", "16000",
         "-f", "f32le", "-"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise SuggestionError(
            f"Could not read the audio: {result.stderr.decode(errors='replace')[:300]}"
        )
    return numpy.frombuffer(result.stdout, dtype=numpy.float32)


def _transcribe_local(audio_path, duration, progress):
    from faster_whisper import WhisperModel

    model_name = os.environ.get("SERMON_WHISPER_MODEL", "base.en")
    progress(f"Loading speech model '{model_name}' (first run downloads it)...")
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    samples = _decode_to_samples(audio_path)
    iterator, _ = model.transcribe(
        samples, language="en", vad_filter=True, beam_size=1, word_timestamps=True
    )
    segments = []
    last_percent = -1
    for item in iterator:
        words = [Word(w.start, w.end, w.word.strip()) for w in (item.words or [])]
        segments.append(Segment(item.start, item.end, item.text.strip(), words))
        percent = int(item.end / duration * 100) if duration else 0
        if percent // 10 != last_percent // 10:
            last_percent = percent
            progress(f"Transcribing... {min(percent, 100)}%")
    return segments


def transcribe(audio_path, cache_dir="cache/transcripts", provider=None, progress=print):
    """Returns a list of Segments for the audio, using the cache when possible."""
    provider = provider or default_provider()
    cache_file = _cache_path(audio_path, cache_dir, provider)
    if os.path.exists(cache_file):
        progress("Using saved transcript.")
        with open(cache_file) as handle:
            return [_segment_from_dict(item) for item in json.load(handle)]

    duration = probe_audio_duration(audio_path)
    if provider == "api":
        segments = _transcribe_api(audio_path, progress)
    else:
        if not _local_available():
            raise SuggestionError(
                "Local transcription needs faster-whisper: pip install faster-whisper"
            )
        segments = _transcribe_local(audio_path, duration, progress)

    if not segments:
        raise SuggestionError("The transcript came back empty. Is the audio silent?")

    os.makedirs(cache_dir, exist_ok=True)
    with open(cache_file, "w") as handle:
        json.dump([_segment_to_dict(s) for s in segments], handle)
    return segments
