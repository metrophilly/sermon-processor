"""DT-246 pilot: time small.en and medium.en on each file in manifest.json.

Resumable: skips any (date, model) pair that already has a result file.
Run: .venv/bin/python pilot/run_pilot.py
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

HERE = Path(__file__).parent
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
MODELS = ["small.en", "medium.en"]


def decode(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    dates = sorted(x["spokenDate"][:10] for x in manifest)
    for model_name in MODELS:
        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        for d in dates:
            out = OUT / f"{d}.{model_name}.json"
            if out.exists():
                continue
            audio = decode(HERE / "audio" / f"{d}.mp3")
            seconds = len(audio) / 16000
            t0 = time.time()
            segs, _ = model.transcribe(audio, language="en", word_timestamps=True, vad_filter=False)
            rows = []
            for s in segs:
                rows.append({
                    "start": float(s.start), "end": float(s.end), "text": s.text.strip(),
                    "avg_logprob": float(s.avg_logprob), "no_speech_prob": float(s.no_speech_prob),
                    "words": [[float(w.start), float(w.end), w.word, float(w.probability)] for w in (s.words or [])],
                })
            elapsed = time.time() - t0
            out.write_text(json.dumps({
                "date": d, "model": model_name, "audio_seconds": seconds,
                "elapsed_seconds": elapsed, "speed_x_realtime": seconds / elapsed, "segments": rows,
            }))
            print(f"{d} {model_name} {seconds/elapsed:.1f}x ({elapsed/60:.1f} min)", flush=True)


if __name__ == "__main__":
    sys.exit(main())
