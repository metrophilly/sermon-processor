import re
import subprocess
import sys
import time

_PROGRESS_KEY = re.compile(r"^[a-z_0-9]+=")
_OUT_TIME = re.compile(r"^out_time_(?:us|ms)=(-?\d+)")  # both are microseconds
_BAR_WIDTH = 30


def _bar(fraction, elapsed):
    filled = int(round(fraction * _BAR_WIDTH))
    return (
        f"[{'#' * filled}{'-' * (_BAR_WIDTH - filled)}] "
        f"{int(fraction * 100):3d}%  {int(elapsed)}s"
    )


def run_ffmpeg(command, total_seconds, stream=None):
    """
    Runs an ffmpeg command and shows a progress bar as it goes.

    `command` is the normal argument list starting with "ffmpeg". `total_seconds`
    is the expected output length, used to turn ffmpeg's position into a percent.
    On a terminal the bar redraws in place; otherwise a line prints every 10%.

    Raises subprocess.CalledProcessError, with ffmpeg's messages in `.output`,
    if ffmpeg fails.
    """
    stream = stream or sys.stdout
    interactive = hasattr(stream, "isatty") and stream.isatty()
    full = command[:1] + ["-progress", "pipe:1", "-nostats"] + command[1:]

    process = subprocess.Popen(
        full,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # merged so a full pipe can never deadlock us
        text=True,
        bufsize=1,
    )
    messages = []
    started = time.time()
    last_percent = -1
    for raw in process.stdout:
        line = raw.strip()
        match = _OUT_TIME.match(line)
        if match and total_seconds > 0:
            fraction = min(max(int(match.group(1)) / 1e6 / total_seconds, 0.0), 1.0)
            percent = int(fraction * 100)
            if percent != last_percent and (interactive or percent % 10 == 0):
                last_percent = percent
                text = _bar(fraction, time.time() - started)
                stream.write(f"\r{text}" if interactive else f"{text}\n")
                stream.flush()
        elif line and not _PROGRESS_KEY.match(line):
            messages.append(line)

    returncode = process.wait()
    if interactive and last_percent >= 0:
        stream.write("\n")
        stream.flush()
    if returncode != 0:
        raise subprocess.CalledProcessError(
            returncode, full, output="\n".join(messages[-15:])
        )
