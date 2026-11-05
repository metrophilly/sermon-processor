import pytest

from app.utils.progress_bar import ProgressBar, format_duration


class Stream:
    def __init__(self, tty):
        self.tty = tty
        self.text = ""

    def isatty(self):
        return self.tty

    def write(self, text):
        self.text += text

    def flush(self):
        pass


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_format_duration():
    assert [format_duration(s) for s in (0, 45, 59.6, 60, 95, 3725)] == [
        "0s", "45s", "1m00s", "1m00s", "1m35s", "62m05s",
    ]


def test_on_a_terminal_the_bar_redraws_in_place_and_ends_with_a_newline():
    stream, clock = Stream(tty=True), Clock()
    bar = ProgressBar("Transcribing", stream, clock=clock)

    bar(0.0)
    bar(0.5)
    bar(1.0)
    bar.close()

    frames = stream.text.split("\r")[1:]
    assert len(frames) == 3  # one redraw per distinct percent
    assert frames[0].startswith("Transcribing [------------------------------]   0%")
    assert frames[1].startswith("Transcribing [###############---------------]  50%")
    assert frames[2].startswith("Transcribing [##############################] 100%")
    assert stream.text.endswith("\n") and stream.text.count("\n") == 1


def test_the_same_percent_is_not_redrawn():
    stream = Stream(tty=True)
    bar = ProgressBar("", stream, clock=Clock())
    for fraction in (0.501, 0.505, 0.509):
        bar(fraction)
    assert stream.text.count("\r") == 1


def test_off_a_terminal_it_prints_plain_lines_every_ten_percent():
    stream = Stream(tty=False)
    bar = ProgressBar("Transcribing", stream, clock=Clock())

    for percent in range(0, 101):
        bar(percent / 100)
    bar.close()

    lines = stream.text.splitlines()
    assert len(lines) == 11  # 0%, 10% ... 100%
    assert "\r" not in stream.text
    assert lines[5].startswith("Transcribing [") and "50%" in lines[5]


def test_elapsed_time_and_time_left_are_shown():
    stream, clock = Stream(tty=True), Clock()
    bar = ProgressBar("", stream, clock=clock)

    clock.now += 60
    bar(0.5)

    assert "1m00s, about 1m00s left" in stream.text


def test_no_estimate_until_there_is_enough_to_go_on():
    stream, clock = Stream(tty=True), Clock()
    bar = ProgressBar("", stream, clock=clock)
    clock.now += 1
    bar(0.5)  # under 3 seconds elapsed: an estimate would be noise
    clock.now += 100
    bar(1.0)  # finished: nothing left to estimate

    assert "left" not in stream.text


def test_values_outside_zero_to_one_are_clamped():
    stream = Stream(tty=True)
    bar = ProgressBar("", stream, clock=Clock())
    bar(-3)
    bar(7)
    assert "  0%" in stream.text and "100%" in stream.text


def test_a_shorter_redraw_does_not_leave_old_characters_behind():
    stream, clock = Stream(tty=True), Clock()
    bar = ProgressBar("", stream, clock=clock)
    clock.now += 100
    bar(0.5)  # long line with an estimate
    longest = len(stream.text) - 1
    clock.now = 1000.0  # contrived: a shorter line follows
    bar(0.6)
    last_frame = stream.text.split("\r")[-1]
    assert len(last_frame) >= longest


def test_close_is_safe_to_repeat_and_to_call_without_drawing():
    stream = Stream(tty=True)
    bar = ProgressBar("", stream, clock=Clock())
    bar.close()
    bar(0.2)
    bar.close()
    bar.close()
    assert stream.text.count("\n") == 1
