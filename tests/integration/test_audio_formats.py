"""
Runs the real audio steps (trim -> fade -> merge) through ffmpeg on tiny
generated files, once per input format. Regression test for the pipeline
breaking when a .wav or .mp3 is dropped into the cache (the fade step used to
write AAC into whatever container the input had).

Takes a few seconds. Skipped if ffmpeg is not installed.
"""

import shutil
import subprocess

import pytest

from app.data_models.pipeline_data import PipelineData
from app.steps.fade_in_out_step import fade_in_out_step
from app.steps.merge_audio_step import merge_audio_step
from app.steps.trim_step import trim_step

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not installed"
)


def _make_tone(path, seconds, freq=440):
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
         f"sine=frequency={freq}:duration={seconds}", "-ar", "48000", str(path)],
        check=True,
    )


def _probe(path, entry):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", entry,
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return out


@pytest.mark.parametrize("name", ["sermon.wav", "sermon.mp3", "sermon.m4a", "Sermon.WAV"])
def test_trim_fade_merge_for_each_format(tmp_path, name):
    main = tmp_path / name
    intro = tmp_path / "intro.wav"
    outro = tmp_path / "outro.wav"
    _make_tone(main, 10)
    _make_tone(intro, 2, 880)
    _make_tone(outro, 2, 660)

    data = PipelineData(
        intro_file_path=str(intro),
        outro_file_path=str(outro),
        main_file_path=str(main),
        active_file_path=str(main),
    )

    data = trim_step(data, start_time="00:00:02", end_time="00:00:08", overwrite=True)
    assert data.active_file_path != str(main)  # never writes over its input

    data = fade_in_out_step(data, fade_duration=1)
    # The faded file must be decodable and use a codec valid for its container.
    assert float(_probe(data.active_file_path, "format=duration")) == pytest.approx(6, abs=0.2)

    data = merge_audio_step(data, output_format="wav")
    assert _probe(data.active_file_path, "stream=codec_name") == "pcm_s16le"
    # 2s intro + 6s trimmed sermon + 2s outro
    assert float(_probe(data.active_file_path, "format=duration")) == pytest.approx(10, abs=0.3)


def test_rerun_over_leftover_files_does_not_fail(tmp_path):
    """A failed earlier run leaves *_faded / *_trimmed files behind. Re-running must overwrite them."""
    main = tmp_path / "sermon.wav"
    _make_tone(main, 6)
    (tmp_path / "sermon_trimmed.wav").write_bytes(b"")          # stale, empty
    (tmp_path / "sermon_trimmed_faded.wav").write_bytes(b"")    # stale, empty

    data = PipelineData(main_file_path=str(main), active_file_path=str(main))
    data = trim_step(data, start_time="00:00:01", end_time="00:00:05", overwrite=True)
    data = fade_in_out_step(data, fade_duration=1)
    assert float(_probe(data.active_file_path, "format=duration")) == pytest.approx(4, abs=0.2)
