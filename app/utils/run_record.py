import datetime
import json
import os
import subprocess


def _git_commit():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        )
        return result.stdout.strip() or None
    except Exception:
        return None


def _ffmpeg_version():
    try:
        first_line = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, text=True
        ).stdout.splitlines()[0]
        return first_line
    except Exception:
        return None


def write_run_record(output_path, record):
    """
    Writes `<output>.json` next to the finished audio so a run can be repeated
    or explained later ("redo last week with 10 more seconds at the start").
    Returns the path written.
    """
    record = dict(record)
    record.setdefault("created_at", datetime.datetime.now().astimezone().isoformat())
    record.setdefault("tool_commit", _git_commit())
    record.setdefault("ffmpeg", _ffmpeg_version())
    path = f"{os.path.splitext(output_path)[0]}.json"
    with open(path, "w") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    return path


def describe_input(path):
    stat = os.stat(path)
    return {
        "path": os.path.abspath(path),
        "bytes": stat.st_size,
        "modified": datetime.datetime.fromtimestamp(stat.st_mtime)
        .astimezone()
        .isoformat(),
    }
