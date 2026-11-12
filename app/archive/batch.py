"""
`sermon batch`: transcribe the archive, resumably (DT-248).

Reads the manifest from `sermon manifest`. For each sermon that is not done it
downloads the audio, transcribes it, writes the export (DT-247) into
`output/archive/transcripts/<sermon_id>/` and deletes the download. A sermon is
done when its `DATE.transcript.json` exists. That file is written last and
atomically, so stopping at any moment leaves nothing half done: run the command
again and it carries on. A failure is logged and the batch continues.
"""

import datetime
import json
import os
import time
import urllib.request

from app.archive.manifest import s3_url
from app.transcripts.build import all_words, build_transcript
from app.transcripts.export import audio_info, validate, write_exports

SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config", "transcript_schema.json"
)
MAX_ATTEMPTS = 3
SPARSE_WINDOW_SECONDS = 20
SPARSE_MIN_WORDS = 15  # the pilot median was 55 words per 20 seconds
EDGE_SECONDS = 90  # intro and outro music is not checked
PILOT_MINUTES_PER_SERMON = 2.0  # about 21x realtime on an M1 Max for a 40 minute sermon


def transcript_dir(archive_dir, sermon_id):
    return os.path.join(archive_dir, "transcripts", sermon_id)


def transcript_path(archive_dir, row):
    return os.path.join(transcript_dir(archive_dir, row["sermon_id"]), f"{row['date']}.transcript.json")


def is_done(archive_dir, row):
    return os.path.exists(transcript_path(archive_dir, row))


def load_state(path):
    if os.path.exists(path):
        with open(path) as handle:
            return json.load(handle)
    return {"version": 1, "sermons": {}}


def save_state(path, state):
    temp = path + ".part"
    with open(temp, "w") as handle:
        json.dump(state, handle, indent=1)
    os.replace(temp, path)


def plan(rows, archive_dir, state, redo=(), retry_failed=False, only=(), years=(), limit=None):
    """Returns (todo, skipped). `skipped` is a list of (row, reason). Newest sermons first."""
    todo, skipped, seen_files = [], [], set()
    for row in sorted(rows, key=lambda r: (r["date"] or "", r["sermon_id"]), reverse=True):
        if only and row["sermon_id"] not in only and row["date"] not in only:
            continue
        if years and (row["date"] or "")[:4] not in years:
            continue
        if row["status"] != "ready":
            skipped.append((row, "blocked: " + ", ".join(row["problems"])))
            continue
        if row["s3_key"] in seen_files:
            skipped.append((row, "shared_file: another sermon with this file is handled first"))
            continue
        seen_files.add(row["s3_key"])
        if is_done(archive_dir, row) and row["sermon_id"] not in redo:
            skipped.append((row, "done"))
            continue
        failed = state["sermons"].get(row["sermon_id"], {})
        if failed.get("status") == "failed" and failed.get("attempts", 0) >= MAX_ATTEMPTS and not retry_failed:
            skipped.append((row, f"failed {failed['attempts']} times (use --retry-failed)"))
            continue
        todo.append(row)
    if limit:
        todo = todo[:limit]
    return todo, skipped


def sparse_windows(transcript, duration_seconds):
    """Windows with very few words: a sign the engine may have dropped speech. A hint, not proof."""
    words = all_words(transcript)
    flagged, start = [], EDGE_SECONDS
    while start + SPARSE_WINDOW_SECONDS <= duration_seconds - EDGE_SECONDS:
        end = start + SPARSE_WINDOW_SECONDS
        count = sum(1 for w in words if start * 1000 <= w["start_ms"] < end * 1000)
        if count < SPARSE_MIN_WORDS:
            flagged.append({"start_seconds": start, "end_seconds": end, "words": count})
        start = end
    return flagged


def download(row, dest):
    """Downloads the stored S3 path to `dest` through a temp file."""
    temp = dest + ".part"
    urllib.request.urlretrieve(s3_url(row["s3_key"]), temp)
    os.replace(temp, dest)


def format_duration(seconds):
    seconds = int(max(0, seconds))
    hours, rest = divmod(seconds, 3600)
    return f"{hours}h {rest // 60:02d}m" if hours else f"{rest // 60}m {rest % 60:02d}s"


def process(row, archive_dir, cache_dir, transcribe_fn, duration_fn, download_fn=download, now=None):
    """Transcribes one sermon. Returns the state record. The download is always removed."""
    ext = os.path.splitext(row["s3_key"])[1] or ".mp3"
    audio = os.path.join(cache_dir, f"{row['sermon_id']}{ext}")
    os.makedirs(cache_dir, exist_ok=True)
    started = time.time()
    try:
        download_fn(row, audio)
        duration = duration_fn(audio)
        raw, model = transcribe_fn(audio)
        transcript = build_transcript(
            raw,
            sermon_id=row["sermon_id"],
            date=row["date"],
            audio=audio_info(audio, duration),
            model=model,
            generated_at=(now or datetime.datetime.now(datetime.timezone.utc)).isoformat(timespec="seconds"),
        )
        validate(transcript, SCHEMA_PATH)
        write_exports(transcript, transcript_dir(archive_dir, row["sermon_id"]), row["date"])
    finally:
        for leftover in (audio, audio + ".part"):
            if os.path.exists(leftover):
                os.remove(leftover)
    return {
        "status": "done",
        "words": transcript["word_count"],
        "audio_seconds": round(duration, 1),
        "seconds": round(time.time() - started, 1),
        "warnings": [{"kind": "sparse_speech", **w} for w in sparse_windows(transcript, duration)],
    }


def run(todo, archive_dir, cache_dir, state, state_path, transcribe_fn, duration_fn, print_fn=print, download_fn=download):
    """Processes `todo` in order. Failures are recorded and the loop carries on.
    KeyboardInterrupt cleans up (process() removes the download) and is re-raised."""
    done_this_run, elapsed = 0, []
    for index, row in enumerate(todo, 1):
        eta = (sum(elapsed) / len(elapsed)) * (len(todo) - index + 1) if elapsed else None
        print_fn(
            f"[{index}/{len(todo)}] {row['date']} {(row['title'] or '')[:50]}"
            + (f"  (about {format_duration(eta)} left)" if eta else "")
        )
        previous = state["sermons"].get(row["sermon_id"], {})
        try:
            record = process(row, archive_dir, cache_dir, transcribe_fn, duration_fn, download_fn)
            record["attempts"] = previous.get("attempts", 0) + 1
            done_this_run += 1
            elapsed.append(record["seconds"])
            if record["warnings"]:
                print_fn(f"    note: {len(record['warnings'])} sparse stretch(es), check for dropped speech")
        except KeyboardInterrupt:
            raise
        except Exception as error:  # one bad file must not stop the batch
            record = {
                "status": "failed",
                "error": f"{type(error).__name__}: {error}"[:300],
                "attempts": previous.get("attempts", 0) + 1,
            }
            print_fn(f"    FAILED: {record['error']}")
        record["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        state["sermons"][row["sermon_id"]] = record
        save_state(state_path, state)
    return done_this_run


def report(rows, archive_dir, state, skipped):
    done = [r for r in rows if is_done(archive_dir, r)]
    failed = [(r, state["sermons"][r["sermon_id"]]) for r in rows if state["sermons"].get(r["sermon_id"], {}).get("status") == "failed" and not is_done(archive_dir, r)]
    warned = [(r, state["sermons"][r["sermon_id"]]) for r in done if state["sermons"].get(r["sermon_id"], {}).get("warnings")]
    lines = [
        f"Sermons in the manifest: {len(rows)}",
        f"Transcribed: {len(done)}",
        f"Failed: {len(failed)}",
        f"Blocked or skipped (not transcribed): {sum(1 for _, why in skipped if not why == 'done')}",
        f"Transcripts with sparse stretches to check: {len(warned)}",
    ]
    if failed:
        lines.append("\nFailed:")
        lines += [f"  {r['date']}  {r['sermon_id']}  attempts {s['attempts']}  {s['error']}" for r, s in failed]
    if warned:
        lines.append("\nSparse stretches (20 s windows with under 15 words; may be silence, music or dropped speech):")
        for r, s in warned:
            spots = ", ".join(f"{w['start_seconds'] // 60}:{w['start_seconds'] % 60:02d}" for w in s["warnings"])
            lines.append(f"  {r['date']}  {r['sermon_id']}  at {spots}")
    return "\n".join(lines)


def dry_run_text(todo, skipped):
    reasons = {}
    for _, why in skipped:
        key = why.split(":")[0].split(" (")[0]
        reasons[key] = reasons.get(key, 0) + 1
    lines = [f"Would transcribe {len(todo)} sermons, newest first."]
    if todo:
        lines.append(f"Rough time: about {format_duration(len(todo) * PILOT_MINUTES_PER_SERMON * 60)} at the pilot speed (about 2 minutes per sermon on an M1 Max).")
        lines += [f"  {r['date']}  {r['sermon_id']}  {(r['title'] or '')[:50]}" for r in todo[:10]]
        if len(todo) > 10:
            lines.append(f"  ... and {len(todo) - 10} more")
    lines.append("Skipped: " + (", ".join(f"{k} {v}" for k, v in sorted(reasons.items())) or "none"))
    return "\n".join(lines)
