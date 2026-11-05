import sys
import time


def format_duration(seconds):
    """45 -> '45s', 95 -> '1m35s'."""
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}m{secs:02d}s"


class ProgressBar:
    """
    A one-line progress bar with elapsed time and an estimate of time left.

        Transcribing [##############----------------]  47%  1m02s, about 1m10s left

    Call it with a fraction between 0 and 1: `bar(0.47)`. On a terminal it
    redraws in place; anywhere else (a log, a pipe) it prints a plain line every
    10% so output stays readable. Call `close()` when finished.
    """

    def __init__(self, label="", stream=None, width=30, clock=time.time):
        self.label = label
        self.stream = stream or sys.stdout
        self.width = width
        self.clock = clock
        self.interactive = hasattr(self.stream, "isatty") and self.stream.isatty()
        self.started = clock()
        self.last_percent = -1
        self.drawn = False
        self._longest = 0

    def _line(self, fraction):
        elapsed = self.clock() - self.started
        filled = int(round(fraction * self.width))
        text = (
            (f"{self.label} " if self.label else "")
            + f"[{'#' * filled}{'-' * (self.width - filled)}] "
            + f"{int(fraction * 100):3d}%  {format_duration(elapsed)}"
        )
        if 0.03 <= fraction < 1.0 and elapsed >= 3:
            text += f", about {format_duration(elapsed * (1 - fraction) / fraction)} left"
        return text

    def update(self, fraction):
        fraction = min(max(float(fraction), 0.0), 1.0)
        percent = int(fraction * 100)
        if percent == self.last_percent:
            return
        if not self.interactive and percent % 10 != 0 and fraction < 1.0:
            return
        self.last_percent = percent
        line = self._line(fraction)
        if self.interactive:
            self._longest = max(self._longest, len(line))
            self.stream.write("\r" + line.ljust(self._longest))  # overwrite leftovers
        else:
            self.stream.write(line + "\n")
        self.stream.flush()
        self.drawn = True

    __call__ = update

    def close(self):
        """Ends the bar's line. Safe to call more than once."""
        if self.interactive and self.drawn:
            self.stream.write("\n")
            self.stream.flush()
        self.drawn = False
