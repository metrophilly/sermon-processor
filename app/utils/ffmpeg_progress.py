import re
import subprocess
import sys

from app.utils.progress_bar import ProgressBar

_PROGRESS_KEY = re.compile(r"^[a-z_0-9]+=")
_OUT_TIME = re.compile(r"^out_time_(?:us|ms)=(-?\d+)")  # both are microseconds


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
    full = command[:1] + ["-progress", "pipe:1", "-nostats"] + command[1:]

    process = subprocess.Popen(
        full,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # merged so a full pipe can never deadlock us
        text=True,
        bufsize=1,
    )
    bar = ProgressBar(stream=stream)
    messages = []
    for raw in process.stdout:
        line = raw.strip()
        match = _OUT_TIME.match(line)
        if match and total_seconds > 0:
            bar(int(match.group(1)) / 1e6 / total_seconds)
        elif line and not _PROGRESS_KEY.match(line):
            messages.append(line)

    returncode = process.wait()
    bar.close()
    if returncode != 0:
        raise subprocess.CalledProcessError(
            returncode, full, output="\n".join(messages[-15:])
        )
