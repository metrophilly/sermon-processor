import shutil
import subprocess

import pytest

from app.utils import cut_preview
from app.utils.cut_preview import confirm_cuts, make_cut_preview


class Script:
    """Feeds scripted answers to the prompt and records what was played."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.played = 0
        self.messages = []

    def input(self, prompt):
        return self.answers.pop(0)

    def play(self, path):
        self.played += 1

    def say(self, message):
        self.messages.append(message)


@pytest.fixture
def fake_preview(monkeypatch):
    calls = []
    monkeypatch.setattr(
        cut_preview, "make_cut_preview", lambda *a, **k: calls.append(a[1:3])
    )
    return calls


def _run(answers, start=100.0, end=500.0, duration=1000.0, tmp="."):
    script = Script(answers)
    result = confirm_cuts(
        "x.wav", start, end, duration, workdir=tmp,
        input_fn=script.input, play_fn=script.play, print_fn=script.say,
    )
    return result, script


def test_enter_accepts_cuts_after_one_preview(fake_preview):
    result, script = _run([""])
    assert result == (100.0, 500.0)
    assert script.played == 1


def test_quit_cancels(fake_preview):
    result, _ = _run(["q"])
    assert result is None


def test_replay_plays_again(fake_preview):
    result, script = _run(["r", ""])
    assert result == (100.0, 500.0)
    assert script.played == 2


def test_adjusting_start_and_end_replays_with_new_values(fake_preview):
    result, script = _run(["s 1:50", "e 8:30", ""])
    assert result == (110.0, 510.0)
    assert fake_preview == [(100.0, 500.0), (110.0, 500.0), (110.0, 510.0)]
    assert script.played == 3


def test_bad_input_does_not_replay_or_change_cuts(fake_preview):
    result, script = _run(["s banana", "e 0:10", "what", ""])
    assert result == (100.0, 500.0)
    assert script.played == 1  # only the initial preview
    assert any("Invalid time" in m for m in script.messages)
    assert any("out of order" in m for m in script.messages)
    assert any("Didn't understand" in m for m in script.messages)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_make_cut_preview_writes_a_short_playable_file(tmp_path):
    source = tmp_path / "in.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=d=60", str(source)],
        check=True,
    )
    out = tmp_path / "preview.wav"

    make_cut_preview(str(source), 20.0, 50.0, str(out), duration=60.0)

    seconds = float(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)],
            capture_output=True, text=True, check=True,
        ).stdout
    )
    # (4s + 6s) + 1s gap + (6s + 4s)
    assert seconds == pytest.approx(21, abs=0.3)
