import re
import shutil
import subprocess

import pytest

from app.trim_suggester.transcribe import Segment, Word
from app.trim_suggester.suggest import words_around
from app.utils import cut_preview
from app.utils.cut_preview import confirm_cuts, make_cut_preview

TIMELINE = [(0.0, 4.0, "before the START cut"), (4.0, 4.15, "BEEP = the START cut"),
            (4.15, 11.15, "after the START cut")]


class Script:
    """Feeds scripted answers to the prompt and records what was played and said."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.played = 0
        self.messages = []
        self.prompts = []

    def input(self, prompt):
        self.prompts.append(prompt)
        return self.answers.pop(0)

    def play(self, path, on_tick=None):
        self.played += 1

    def say(self, message):
        self.messages.append(message)

    @property
    def text(self):
        return "\n".join(self.messages)


@pytest.fixture
def fake_preview(monkeypatch):
    calls = []

    def fake(main, start, end, out, duration):
        calls.append((start, end))
        return TIMELINE

    monkeypatch.setattr(cut_preview, "make_cut_preview", fake)
    return calls


def _run(answers, start=100.0, end=500.0, duration=1000.0, context_fn=None):
    script = Script(answers)
    result = confirm_cuts(
        "x.wav", start, end, duration, workdir=".",
        input_fn=script.input, play_fn=script.play, print_fn=script.say,
        context_fn=context_fn,
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


def test_nudging_by_seconds_is_relative_to_the_current_cut(fake_preview):
    result, _ = _run(["s +2", "s -0.5", "e -3", "e +1", ""])
    assert result == (101.5, 498.0)


def test_bad_input_does_not_replay_or_change_cuts(fake_preview):
    result, script = _run(["s banana", "e 0:10", "what", ""])
    assert result == (100.0, 500.0)
    assert script.played == 1  # only the initial preview
    assert "Invalid time" in script.text
    assert "out of order" in script.text
    assert "Didn't understand" in script.text


def test_the_screen_explains_what_to_listen_for(fake_preview):
    _, script = _run([""])
    text = script.text
    assert "BEEP" in text
    assert "START cut at 0:01:40" in text and "END cut at 0:08:20" in text
    assert "should be the last words of the sermon's closing prayer" in text


def test_prompt_lists_every_choice_with_examples(fake_preview):
    _, script = _run([""])
    prompt = script.prompts[0]
    for expected in ("[Enter]", "[r]", "[s 40:55]", "[s +2]", "[s -0.5]",
                     "[e 1:17:30]", "[e +2]", "[e -0.5]", "[q]"):
        assert expected in prompt


def test_half_second_and_smaller_nudges_work(fake_preview):
    result, _ = _run(["s -0.5", "s +.25", "e +0.5", "e -1.75", ""])
    assert result == (99.75, 498.75)


def test_transcript_words_are_shown_around_each_cut(fake_preview):
    shown = []

    def context(seconds, before, after):
        shown.append((seconds, before, after))
        return ("announcements. Thank you.", "Today's scripture reading comes") if seconds == 100.0 \
            else ("in Jesus' name. Amen.", "")

    _, script = _run([""], context_fn=context)

    assert 'before the beep: "announcements. Thank you."' in script.text
    assert 'after the beep:  "Today\'s scripture reading comes"' in script.text
    assert "after the beep:  (nothing spoken)" in script.text
    # Each cut is asked about exactly the seconds the clip plays around it.
    assert shown == [(100.0, 4.0, 7.0), (500.0, 7.0, 4.0)]


def test_context_is_recomputed_when_a_cut_moves(fake_preview):
    shown = []
    _run(["s +5", ""], context_fn=lambda s, b, a: shown.append(s) or ("a", "b"))
    assert shown == [100.0, 500.0, 105.0, 500.0]


def test_notes_are_not_wrapped_in_quotes_but_spoken_words_are(fake_preview):
    _, script = _run([""], context_fn=lambda s, b, a: ('(quiet. The last words were 8s earlier: "...Thank you.")', "Today's scripture"))
    assert 'before the beep: (quiet. The last words were 8s earlier: "...Thank you.")' in script.text
    assert 'after the beep:  "Today\'s scripture"' in script.text


def test_the_live_position_line_says_where_in_the_clip_you_are(monkeypatch):
    written = []

    class Terminal:
        def isatty(self):
            return True

        def write(self, text):
            written.append(text)

        def flush(self):
            pass

    monkeypatch.setattr(cut_preview.sys, "stdout", Terminal())
    tick = cut_preview._make_ticker(
        [(0.0, 4.0, "before the START cut"), (4.0, 4.15, "BEEP = the START cut"), (4.15, 23.0, "after the START cut")]
    )

    tick(1.2)
    tick(4.05)
    tick(10.0)

    assert "0:01 / 0:23" in written[0] and "before the START cut" in written[0]
    assert "BEEP = the START cut" in written[1]
    assert "after the START cut" in written[2]


def test_there_is_no_live_line_when_not_on_a_terminal(monkeypatch):
    monkeypatch.setattr(cut_preview.sys.stdout, "isatty", lambda: False, raising=False)
    assert cut_preview._make_ticker([(0.0, 5.0, "x")]) is None


# --- words_around ----------------------------------------------------------


def _words(start, tokens, step=1.0):
    return [Word(start + i * step, start + i * step + 0.5, t) for i, t in enumerate(tokens)]


def test_words_around_uses_word_timing():
    seg = Segment(0, 20, "a b c d e f", _words(0, "announcements end. Thank you. Today's scripture".split()))
    before, after = words_around([seg], 4.0)
    assert before.endswith("Thank you.") and "announcements" in before
    assert after.startswith("Today's scripture")


def test_words_around_only_reports_what_the_clip_actually_plays():
    # Real case: "Thank you." right at the cut, then 10 seconds of quiet, then the reading.
    words = _words(0.0, ["sign", "up", "events.", "Thank", "you."], step=0.5)  # ends at 2.5
    words += _words(12.0, ["Today's", "scripture", "reading"], step=0.5)
    seg = Segment(0, 14, "x", words)

    before, after = words_around([seg], 2.5, before_seconds=4.0, after_seconds=7.0)

    assert before.endswith("Thank you.")
    # The reading is ~9.5s away, beyond the 7s that are played, so it must be presented
    # as coming after silence, never as something you will hear right after the beep.
    assert after.startswith("(silence for 10s, then:")
    assert 'Today\'s scripture reading..."' in after


def test_words_around_reports_silence_before_a_cut_too():
    words = _words(0.0, ["Amen."], step=0.5) + _words(30.0, ["Let's", "sing"], step=0.5)
    before, after = words_around([Segment(0, 31, "x", words)], 30.0, before_seconds=7.0, after_seconds=4.0)
    assert before.startswith("(quiet") and "Amen." in before
    assert after.startswith("Let's sing")


def test_words_around_falls_back_to_segment_text_without_word_timing():
    segments = [Segment(0, 5, "Thank you."), Segment(5, 10, "Today's scripture reading")]
    assert words_around(segments, 5.0) == ("Thank you.", "Today's scripture reading")


def test_words_around_at_the_edges_is_empty_not_an_error():
    segments = [Segment(10, 12, "hello there")]
    assert words_around(segments, 0.0, 5.0, 5.0)[0] == ""
    assert words_around(segments, 100.0, 5.0, 5.0)[1] == ""


# --- the real clip ------------------------------------------------------------

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _max_volume(path, start, length):
    result = subprocess.run(
        ["ffmpeg", "-v", "info", "-ss", str(start), "-t", str(length), "-i", str(path),
         "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return float(re.search(r"max_volume: (-?[\d.]+) dB", result.stderr).group(1))


@needs_ffmpeg
def test_the_clip_has_a_beep_exactly_at_each_cut_and_a_correct_timeline(tmp_path):
    source = tmp_path / "silence.wav"
    subprocess.run(  # 60 seconds of pure silence, so any loud sound is the beep
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-t", "60", "-i",
         "anullsrc=r=44100:cl=stereo", str(source)], check=True)
    out = tmp_path / "preview.wav"

    timeline = make_cut_preview(str(source), 20.0, 50.0, str(out), duration=60.0)

    labels = [label for _, _, label in timeline]
    assert labels == [
        "before the START cut", "BEEP = the START cut", "after the START cut",
        "before the END cut", "BEEP = the END cut", "after the END cut",
    ]
    total = timeline[-1][1]
    assert total == pytest.approx(4 + 0.15 + 7 + 1 + 7 + 0.15 + 4)  # 23.3

    beeps = [(a, b) for a, b, label in timeline if label.startswith("BEEP")]
    for begin, finish in beeps:
        assert _max_volume(out, begin + 0.02, finish - begin - 0.04) > -12  # clearly audible
    assert _max_volume(out, 0.5, 3.0) < -60  # silence just before the first beep
    assert _max_volume(out, beeps[0][1] + 0.5, 5.0) < -60  # silence after it


@needs_ffmpeg
def test_a_cut_at_the_very_start_of_the_file_still_works(tmp_path):
    source = tmp_path / "a.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=d=30", str(source)], check=True)

    timeline = make_cut_preview(str(source), 0.0, 25.0, str(tmp_path / "p.wav"), duration=30.0)

    assert [l for _, _, l in timeline][0] == "BEEP = the START cut"  # nothing before it to play
