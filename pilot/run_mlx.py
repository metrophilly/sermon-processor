"""DT-246 follow-up: mlx-whisper (Apple GPU) on the pilot files.

Models: large-v3-turbo and large-v3, word timestamps on,
condition_on_previous_text=False. Resumable: skips existing results.
Usage: .venv-mlx/bin/python pilot/run_mlx.py [DATE ...]   (default: all 10)
Results use the same JSON shape as run_pilot.py so compare scripts work.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import mlx_whisper
import numpy as np

HERE = Path(__file__).parent
OUT = HERE / "results"
MODELS = {
    "mlx-turbo": "mlx-community/whisper-large-v3-turbo",
    "mlx-large": "mlx-community/whisper-large-v3-mlx",
}


def decode(path):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    dates = sys.argv[1:] or sorted(x["spokenDate"][:10] for x in manifest)
    import os
    only = os.environ.get("MLX_ONLY")  # e.g. MLX_ONLY=mlx-turbo
    names = [only] if only else list(MODELS)
    for name in names:
        for d in dates:
            out = OUT / f"{d}.{name}.json"
            if out.exists():
                continue
            audio = decode(HERE / "audio" / f"{d}.mp3")
            seconds = len(audio) / 16000
            t0 = time.time()
            res = mlx_whisper.transcribe(
                audio, path_or_hf_repo=MODELS[name], language="en",
                word_timestamps=True, condition_on_previous_text=False, verbose=None,
            )
            elapsed = time.time() - t0
            rows = []
            for s in res["segments"]:
                rows.append({
                    "start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip(),
                    "avg_logprob": float(s.get("avg_logprob", 0)), "no_speech_prob": float(s.get("no_speech_prob", 0)),
                    "words": [[float(w["start"]), float(w["end"]), w["word"], float(w.get("probability", 0))]
                              for w in s.get("words", [])],
                })
            out.write_text(json.dumps({
                "date": d, "model": name, "audio_seconds": seconds, "elapsed_seconds": elapsed,
                "speed_x_realtime": seconds / elapsed, "segments": rows,
            }))
            print(f"{d} {name} {seconds/elapsed:.1f}x ({elapsed/60:.1f} min)", flush=True)


if __name__ == "__main__":
    sys.exit(main())
