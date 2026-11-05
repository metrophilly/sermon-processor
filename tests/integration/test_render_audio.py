"""
Runs render_audio_step through real ffmpeg on tiny generated files.

Covers every input container, optional intro/outro, mp3 output, and the early
validation errors. Skipped if ffmpeg is not installed.
"""

import glob
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
    assert _duration(data.active_file_path) == pytest.approx(10, abs=0.3)  # 2 + 6 + 2


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
    assert _duration(data.active_file_path) == pytest.approx(10, abs=0.3)


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

    assert _duration(data.active_file_path) == pytest.approx(7, abs=0.3)


def test_rerun_overwrites_previous_render(clips):
    tmp_path, intro, outro = clips
    main = tmp_path / "sermon.wav"
    _tone(main, 6)
    (tmp_path / "sermon_rendered.wav").write_bytes(b"")  # stale leftover

    data = render_audio_step(
        _data(main, intro, outro), start_time="00:00:01", end_time="00:00:05"
    )

    assert _duration(data.active_file_path) == pytest.approx(8, abs=0.3)


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


def test_parse_timestamp_is_still_exported_from_the_render_step():
    assert parse_timestamp("00:01:30") == 90
