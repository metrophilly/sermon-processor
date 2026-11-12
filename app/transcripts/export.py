"""Writes DATE.transcript.json and DATE.vtt next to each other, atomically."""

import hashlib
import json
import os

from app.transcripts.build import to_vtt


def sha256_of(path, chunk=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()


def audio_info(path, duration_seconds):
    return {
        "file": os.path.basename(path),
        "sha256": sha256_of(path),
        "duration_seconds": round(float(duration_seconds), 3),
    }


def _write_atomic(path, text):
    """Write to a temp file, then rename, so a stopped run never leaves half a file."""
    temp = path + ".part"
    with open(temp, "w", encoding="utf-8") as handle:
        handle.write(text)
    os.replace(temp, path)


def write_exports(transcript, out_dir, stem):
    """Writes `<stem>.transcript.json` (last) and `<stem>.vtt`. Returns both paths.

    The JSON is written last: a transcript file that exists is a finished one.
    """
    os.makedirs(out_dir, exist_ok=True)
    vtt_path = os.path.join(out_dir, f"{stem}.vtt")
    json_path = os.path.join(out_dir, f"{stem}.transcript.json")
    _write_atomic(vtt_path, to_vtt(transcript))
    _write_atomic(json_path, json.dumps(transcript, indent=1, ensure_ascii=False) + "\n")
    return json_path, vtt_path


def validate(transcript, schema_path):
    """Raises jsonschema.ValidationError if the transcript does not match the schema."""
    import jsonschema

    with open(schema_path) as handle:
        jsonschema.validate(transcript, json.load(handle))
