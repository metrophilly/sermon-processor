"""End-to-end `sermon audio` runs through real ffmpeg on tiny generated files."""

import json
import os
import shutil
import subprocess

import pytest

from app import cli
from app.trim_suggester.suggest import TrimSuggestion
from app.utils import cut_preview

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _tone(path, seconds):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=d={seconds}", str(path)],
        check=True,
    )


def _duration(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(cli, "open_result", lambda path: None)
    monkeypatch.setattr(cli, "notify", lambda *a: None)
    source = tmp_path / "service.mp3"
    _tone(source, 30)
    return tmp_path, source


def _run(tmp_path, source, *extra, input_fn=None):
    argv = ["audio", str(source), "--output-dir", str(tmp_path / "out"),
            "--config", str(tmp_path / "none.json"), "--no-open", *extra]
    return cli.main(argv, input_fn=input_fn or (lambda p: ""), print_fn=lambda *_: None)


def test_manual_cuts_produce_output_and_a_record(env):
    tmp_path, source = env
    code = _run(tmp_path, source, "--start", "0:05", "--end", "0:25", "--date", "2026-11-01", "-y")

    assert code == 0
    output = tmp_path / "out" / "sermon" / "2026-11-01.wav"
    assert _duration(output) == pytest.approx(20, abs=0.3)
    record = json.loads((tmp_path / "out" / "sermon" / "2026-11-01.json").read_text())
    assert record["trim"]["start_formatted"] == "0:00:05"
    assert record["trim"]["chosen_by"] == "you"
    assert record["input"]["bytes"] == os.path.getsize(source)
    assert record["auto_trim"] is None


def test_rerun_never_overwrites_an_earlier_result(env):
    tmp_path, source = env
    for _ in range(2):
        _run(tmp_path, source, "--start", "0:05", "--end", "0:15", "--date", "2026-11-01", "-y")
    folder = tmp_path / "out" / "sermon"
    assert sorted(p.name for p in folder.glob("*.wav")) == ["2026-11-01-2.wav", "2026-11-01.wav"]


def _codec(path):
    return subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def test_by_default_a_wav_an_mp3_and_a_record_are_written_together(env):
    tmp_path, source = env
    lines = []
    code = cli.main(
        ["audio", str(source), "--output-dir", str(tmp_path / "out"),
         "--config", str(tmp_path / "none.json"), "--no-open",
         "--start", "0:05", "--end", "0:25", "--date", "2026-11-01", "-y"],
        print_fn=lines.append,
    )

    folder = tmp_path / "out" / "sermon"
    assert code == 0
    assert sorted(p.name for p in folder.iterdir()) == ["2026-11-01.json", "2026-11-01.mp3", "2026-11-01.wav"]
    assert _codec(folder / "2026-11-01.wav") == "pcm_s16le"
    assert _codec(folder / "2026-11-01.mp3") == "mp3"
    # Same sermon: the two files are the same length.
    assert _duration(folder / "2026-11-01.mp3") == pytest.approx(_duration(folder / "2026-11-01.wav"), abs=0.1)
    record = json.loads((folder / "2026-11-01.json").read_text())
    assert set(record["outputs"]) == {"wav", "mp3"}
    assert record["output"].endswith(".wav")
    text = "\n".join(lines)
    assert "2026-11-01.wav" in text and "2026-11-01.mp3" in text
    assert "edit in Audacity" in text and "ready to use" in text


def test_a_single_format_can_still_be_asked_for(env):
    tmp_path, source = env
    _run(tmp_path, source, "--start", "0:05", "--end", "0:15", "--format", "wav", "--date", "2026-11-01", "-y")
    folder = tmp_path / "out" / "sermon"
    assert sorted(p.name for p in folder.iterdir()) == ["2026-11-01.json", "2026-11-01.wav"]


def test_any_leftover_file_of_the_set_makes_the_next_run_use_a_new_name(env):
    tmp_path, source = env
    folder = tmp_path / "out" / "sermon"
    folder.mkdir(parents=True)
    (folder / "2026-11-01.mp3").write_bytes(b"an mp3 you already cleaned up in Audacity")

    _run(tmp_path, source, "--start", "0:05", "--end", "0:15", "--date", "2026-11-01", "-y")

    assert (folder / "2026-11-01.mp3").read_bytes() == b"an mp3 you already cleaned up in Audacity"
    assert (folder / "2026-11-01-2.wav").exists() and (folder / "2026-11-01-2.mp3").exists()


def test_default_date_is_the_most_recent_sunday(env, monkeypatch):
    tmp_path, source = env
    monkeypatch.setattr(cli, "last_sunday", lambda: "2026-11-01")
    _run(tmp_path, source, "--start", "0:05", "--end", "0:15", "-y")
    assert (tmp_path / "out" / "sermon" / "2026-11-01.wav").exists()


def test_mp3_output_format(env):
    tmp_path, source = env
    _run(tmp_path, source, "--start", "0:05", "--end", "0:15", "--format", "mp3", "--date", "2026-11-01", "-y")
    assert (tmp_path / "out" / "sermon" / "2026-11-01.mp3").exists()
    assert not (tmp_path / "out" / "sermon" / "2026-11-01.wav").exists()


def test_one_flag_without_the_other_is_rejected(env, capsys):
    tmp_path, source = env
    assert _run(tmp_path, source, "--start", "0:05") == 1
    assert not (tmp_path / "out").exists()


def test_bad_inputs_fail_with_exit_1_and_no_output(env):
    tmp_path, source = env
    assert _run(tmp_path, tmp_path / "missing.wav", "--start", "0:05", "--end", "0:15") == 1
    assert _run(tmp_path, source, "--start", "0:05", "--end", "9:00", "-y") == 1  # past the end
    assert _run(tmp_path, source, "--start", "1:2", "--end", "0:15", "-y") == 1  # typo'd time
    assert not (tmp_path / "out").exists()


def test_cancelling_at_the_preview_renders_nothing(env, monkeypatch):
    tmp_path, source = env
    monkeypatch.setattr(cli, "confirm_cuts", lambda *a, **k: None)
    assert _run(tmp_path, source, "--start", "0:05", "--end", "0:15") == 1
    assert not (tmp_path / "out").exists()


def test_cuts_adjusted_at_the_preview_are_what_gets_rendered(env, monkeypatch):
    tmp_path, source = env
    monkeypatch.setattr(cut_preview, "make_cut_preview", lambda *a, **k: None)
    monkeypatch.setattr(cli, "confirm_cuts", lambda *a, **k: (2.0, 12.0))
    assert _run(tmp_path, source, "--start", "0:05", "--end", "0:15", "--date", "2026-11-01") == 0
    assert _duration(tmp_path / "out" / "sermon" / "2026-11-01.wav") == pytest.approx(10, abs=0.3)


def _fake_suggestion(**overrides):
    base = dict(start=5.0, end=25.0, start_quote="first words", end_quote="last words",
                confidence="high", reasoning="because", verified=True, warnings=[], model="fake")
    base.update(overrides)
    return TrimSuggestion(**base)


def test_auto_trim_is_used_and_recorded(env, monkeypatch):
    tmp_path, source = env
    monkeypatch.setattr(cli, "suggest_trim", lambda *a, **k: _fake_suggestion())
    assert _run(tmp_path, source, "--date", "2026-11-01", "-y") == 0
    record = json.loads((tmp_path / "out" / "sermon" / "2026-11-01.json").read_text())
    assert record["trim"]["chosen_by"] == "auto"
    assert record["auto_trim"]["start_quote"] == "first words"
    assert record["auto_trim"]["adjusted_by_you"] is False
    assert _duration(tmp_path / "out" / "sermon" / "2026-11-01.wav") == pytest.approx(20, abs=0.3)


def test_numpy_numbers_in_a_suggestion_do_not_break_the_run(env, monkeypatch):
    numpy = pytest.importorskip("numpy")
    tmp_path, source = env
    monkeypatch.setattr(
        cli, "suggest_trim",
        lambda *a, **k: _fake_suggestion(start=numpy.float64(5.0), end=numpy.float64(25.0)),
    )

    assert _run(tmp_path, source, "--date", "2026-11-01", "-y") == 0

    record = json.loads((tmp_path / "out" / "sermon" / "2026-11-01.json").read_text())
    assert record["auto_trim"]["adjusted_by_you"] is False
    assert record["trim"]["start"] == 5.0


def test_a_record_that_cannot_be_saved_does_not_lose_the_audio(env, monkeypatch):
    tmp_path, source = env
    monkeypatch.setattr(cli, "write_run_record", lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")))
    lines = []

    code = cli.main(
        ["audio", str(source), "--output-dir", str(tmp_path / "out"),
         "--config", str(tmp_path / "none.json"), "--no-open",
         "--start", "0:05", "--end", "0:25", "--date", "2026-11-01", "-y"],
        print_fn=lines.append,
    )

    folder = tmp_path / "out" / "sermon"
    assert code == 0  # the audio is made, so the run succeeds
    assert (folder / "2026-11-01.wav").exists() and (folder / "2026-11-01.mp3").exists()
    text = "\n".join(lines)
    assert "run record could not be saved" in text and "disk full" in text
    assert "Done:" in text and "ready to use" in text


def test_an_unexpected_error_is_explained_and_logged_not_a_traceback(env, monkeypatch):
    tmp_path, source = env
    monkeypatch.setattr(cli, "render_audio_step", lambda *a, **k: {}["missing"])
    lines = []

    code = cli.main(
        ["audio", str(source), "--output-dir", str(tmp_path / "out"),
         "--config", str(tmp_path / "none.json"), "--no-open",
         "--start", "0:05", "--end", "0:25", "-y"],
        print_fn=lines.append,
    )

    assert code == 1
    text = "\n".join(lines)
    assert "Something unexpected went wrong: KeyError" in text
    log = tmp_path / "cache" / "last-error.log"
    assert "Traceback" in log.read_text() and "KeyError" in log.read_text()
    assert "Traceback" not in text  # the details are in the log, not on the screen


def test_plan_only_shows_the_cuts_and_renders_nothing(env, monkeypatch):
    tmp_path, source = env
    monkeypatch.setattr(cli, "suggest_trim", lambda *a, **k: _fake_suggestion())
    lines = []
    code = cli.main(
        ["audio", str(source), "--output-dir", str(tmp_path / "out"),
         "--config", str(tmp_path / "none.json"), "--plan-only"],
        print_fn=lines.append,
    )
    assert code == 0
    assert not (tmp_path / "out").exists()
    text = "\n".join(lines)
    assert "first words" in text and "last words" in text


@pytest.mark.parametrize("risky",[dict(warnings=["Could not find the start words"]), dict(confidence="low")])
def test_unattended_run_refuses_an_unverified_auto_cut(env, monkeypatch, risky):
    tmp_path, source = env
    monkeypatch.setattr(cli, "suggest_trim", lambda *a, **k: _fake_suggestion(**risky))
    assert _run(tmp_path, source, "-y") == 1
    assert not (tmp_path / "out").exists()
