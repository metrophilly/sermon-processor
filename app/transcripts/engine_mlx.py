"""
The chosen speech engine for the archive (DT-246): large-v3-turbo through
mlx-whisper on the Apple GPU, about 20x realtime on an M1 Max. Apple Silicon only.
Install with: pip install mlx-whisper

Settings match the pilot: English, word timestamps, no carried-over context.
"""

import subprocess

MODEL_REPO = "mlx-community/whisper-large-v3-turbo"
SETTINGS = {"language": "en", "word_timestamps": True, "condition_on_previous_text": False}


def decode_audio(path):
    """16 kHz mono float32 samples, decoded with our own ffmpeg."""
    import numpy as np

    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def transcribe(path):
    """Returns (raw_words, model_info). raw_words are (start, end, text, confidence)."""
    import mlx_whisper

    result = mlx_whisper.transcribe(decode_audio(path), path_or_hf_repo=MODEL_REPO, verbose=None, **SETTINGS)
    raw = [
        (w["start"], w["end"], w["word"], w.get("probability", 0.0))
        for segment in result["segments"]
        for w in segment.get("words", [])
    ]
    return raw, {"engine": "mlx-whisper", "name": MODEL_REPO.split("/")[-1], "settings": dict(SETTINGS)}


def words_from_pilot_result(path):
    """Reads a pilot results file (pilot/results/DATE.MODEL.json) as raw words."""
    import json

    with open(path) as handle:
        data = json.load(handle)
    return [tuple(w[:4]) for segment in data["segments"] for w in segment["words"]], {
        "engine": "pilot-result",
        "name": data.get("model", "unknown"),
        "settings": {},
    }
