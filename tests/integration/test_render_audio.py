"""
Runs render_audio_step through real ffmpeg on tiny generated files.

Covers every input container, optional intro/outro, mp3 output, and the early
validation errors. Skipped if ffmpeg is not installed.
"""

import glob
import re
import shutil
import subprocess

import pytest

from app.data_models.pipeline_data import PipelineData
from app.steps.render_audio_step import parse_timestamp, render_audio_step

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not installed"
)


def _tone(path, seconds, freq=440):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"sine=frequency={freq}:duration={seconds}", "-ar", "48000", str(path)],
        check=True,
    )


def _probe(path, entry):
    return subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", entry,
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def _duration(path):
    return float(_probe(path, "format=duration"))


@pytest.fixture
def clips(tmp_path):
    intro, outro = tmp_path / "intro.wav", tmp_path / "outro.wav"
    _tone(intro, 2, 880)
    _tone(outro, 2, 660)
    return tmp_path, intro, outro


def _data(main, intro=None, outro=None):
    return PipelineData(
        main_file_path=str(main),
        active_file_path=str(main),
        intro_file_path=str(intro) if intro else None,
        outro_file_path=str(outro) if outro else None,
    )


@pytest.mark.parametrize("name", ["sermon.wav", "sermon.mp3", "sermon.m4a", "Sermon.WAV"])
def test_every_input_format_renders_wav(clips, name):
    tmp_path, intro, outro = clips
    main = tmp_path / name
    _tone(main, 10)

    data = render_audio_step(
        _data(main, intro, outro), start_time="00:00:02", end_time="00:00:08"
    )

    assert data.active_file_path.endswith("_rendered.wav")
    assert _probe(data.active_file_path, "stream=codec_name") == "pcm_s16le"
    assert _probe(data.active_file_path, "stream=sample_rate") == "44100"
    assert _duration(data.active_file_path) == pytest.approx(15, abs=0.3)  # 2 + 2.5 + 6 + 2.5 + 2


def test_mp3_output(clips):
    tmp_path, intro, outro = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 10)

    data = render_audio_step(
        _data(main, intro, outro),
        start_time="00:00:00",
        end_time="00:00:06",
        output_format="mp3",
    )

    assert data.active_file_path.endswith("_rendered.mp3")
    assert _probe(data.active_file_path, "stream=codec_name") == "mp3"
    assert _duration(data.active_file_path) == pytest.approx(15, abs=0.3)


def test_intro_and_outro_are_optional(clips):
    tmp_path, _, _ = clips
    main = tmp_path / "sermon.mp3"
    _tone(main, 8)

    data = render_audio_step(_data(main), start_time="00:00:01", end_time="00:00:05")

    assert _duration(data.active_file_path) == pytest.approx(4, abs=0.3)


def test_no_trim_uses_whole_file(clips):
    tmp_path, intro, _ = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 5)

    data = render_audio_step(_data(main, intro))

    assert _duration(data.active_file_path) == pytest.approx(9.5, abs=0.3)  # 2 + 2.5 + 5


def test_rerun_overwrites_previous_render(clips):
    tmp_path, intro, outro = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 6)
    (tmp_path / "sermon_rendered.wav").write_bytes(b"")  # stale leftover

    data = render_audio_step(
        _data(main, intro, outro), start_time="00:00:01", end_time="00:00:05"
    )

    assert _duration(data.active_file_path) == pytest.approx(13, abs=0.3)  # 2 + 2.5 + 4 + 2.5 + 2


def test_trim_past_end_fails_early_with_clear_message(clips):
    tmp_path, intro, outro = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 5)

    with pytest.raises(ValueError, match="past the end"):
        render_audio_step(
            _data(main, intro, outro), start_time="00:00:01", end_time="00:01:00"
        )
    assert not (tmp_path / "sermon_rendered.wav").exists()


def test_end_before_start_is_rejected(clips):
    tmp_path, _, _ = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 5)

    with pytest.raises(ValueError, match="must be after"):
        render_audio_step(_data(main), start_time="00:00:04", end_time="00:00:02")


def test_non_audio_file_is_rejected(tmp_path):
    bogus = tmp_path / "sermon.mp3"
    bogus.write_text("this is not audio")

    with pytest.raises(ValueError, match="could not read"):
        render_audio_step(_data(bogus))


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="not found"):
        render_audio_step(_data(tmp_path / "nope.wav"))


def test_failed_render_leaves_no_partial_file(clips):
    tmp_path, intro, outro = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 5)

    with pytest.raises(subprocess.CalledProcessError):
        render_audio_step(
            _data(main, intro, outro), start_time="00:00:00", end_time="00:00:04",
            output_format="not-a-format",
        )
    assert glob.glob(str(tmp_path / "*_rendered*")) == []


def _max_volume(path, start, length):
    result = subprocess.run(
        ["ffmpeg", "-v", "info", "-ss", str(start), "-t", str(length), "-i", str(path),
         "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return float(re.search(r"max_volume: (-?[\d.]+) dB", result.stderr).group(1))


def test_silence_sits_exactly_between_intro_sermon_and_outro(clips):
    tmp_path, intro, outro = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 10)

    data = render_audio_step(
        _data(main, intro, outro), start_time="00:00:02", end_time="00:00:08"
    )
    out = data.active_file_path

    # intro 0-2 | silence 2-4.5 | sermon 4.5-10.5 | silence 10.5-13 | outro 13-15
    assert _duration(out) == pytest.approx(15, abs=0.15)
    assert _max_volume(out, 0.2, 1.6) > -30  # the intro is audible
    assert _max_volume(out, 2.15, 2.2) < -60  # 2.5s of true silence after it
    assert _max_volume(out, 5.5, 4.0) > -30  # the sermon
    assert _max_volume(out, 10.65, 2.2) < -60  # silence before the outro
    assert _max_volume(out, 13.2, 1.6) > -30  # the outro is audible


def test_the_gap_length_can_be_changed_or_turned_off(clips):
    tmp_path, intro, outro = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 10)
    args = dict(start_time="00:00:02", end_time="00:00:08")

    none = render_audio_step(_data(main, intro, outro), gap_seconds=0, **args)
    assert _duration(none.active_file_path) == pytest.approx(10, abs=0.3)  # 2 + 6 + 2

    short = render_audio_step(_data(main, intro, outro), gap_seconds=1, **args)
    assert _duration(short.active_file_path) == pytest.approx(12, abs=0.3)  # 2 + 1 + 6 + 1 + 2


def test_a_gap_is_only_added_next_to_an_intro_or_outro_that_exists(clips):
    tmp_path, intro, outro = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 10)
    args = dict(start_time="00:00:02", end_time="00:00:08")

    only_outro = render_audio_step(_data(main, outro=outro), **args)
    assert _duration(only_outro.active_file_path) == pytest.approx(10.5, abs=0.3)  # 6 + 2.5 + 2

    neither = render_audio_step(_data(main), **args)
    assert _duration(neither.active_file_path) == pytest.approx(6, abs=0.3)  # nothing to separate


def test_a_second_file_comes_from_the_same_pass(clips, tmp_path):
    folder, intro, outro = clips
    main = folder / "sermon.wav"
    _tone(main, 10)
    wav, mp3 = tmp_path / "out" / "done.wav", tmp_path / "out" / "done.mp3"

    render_audio_step(
        _data(main, intro, outro), start_time="00:00:02", end_time="00:00:08",
        output_format="wav", output_path=str(wav), extra_output_path=str(mp3),
    )

    assert _probe(wav, "stream=codec_name") == "pcm_s16le"
    assert _probe(mp3, "stream=codec_name") == "mp3"
    assert _duration(wav) == pytest.approx(15, abs=0.15)
    assert _duration(mp3) == pytest.approx(_duration(wav), abs=0.1)
    assert _max_volume(mp3, 2.2, 2.0) < -50  # the gap survived the mp3 encode too
    assert glob.glob(str(tmp_path / "out" / "*partial*")) == []


def test_a_failed_render_leaves_neither_file_behind(clips, tmp_path):
    folder, intro, outro = clips
    main = folder / "sermon.wav"
    _tone(main, 5)
    wav, bad = tmp_path / "out" / "done.wav", tmp_path / "out" / "done.not-a-format"

    with pytest.raises(subprocess.CalledProcessError):
        render_audio_step(
            _data(main, intro, outro), start_time="00:00:00", end_time="00:00:04",
            output_path=str(wav), extra_output_path=str(bad),
        )

    assert glob.glob(str(tmp_path / "out" / "*")) == []  # not even a half-written wav


def test_parse_timestamp_is_still_exported_from_the_render_step():
    assert parse_timestamp("00:01:30") == 90
