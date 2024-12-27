import pytest
import subprocess
from unittest.mock import patch
from app.utils.normalize_audio import normalize_audio


@pytest.fixture
def dummy_audio_file(tmp_path):
    input_file = tmp_path / "input.wav"
    output_file = tmp_path / "output_normalized.wav"
    input_file.write_text("dummy audio data")
    return input_file, output_file


@patch("subprocess.run")
def test_normalize_audio_success(mock_run, dummy_audio_file):
    input_path, output_path = dummy_audio_file
    normalize_audio(str(input_path), str(output_path))

    mock_run.assert_called_once_with(
        [
            "ffmpeg",
            "-loglevel",
            "info",
            "-i",
            str(input_path),
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-b:a",
            "192k",
            "-af",
            "loudnorm=I=-16:TP=-1:LRA=11:linear=true",
            str(output_path),
        ],
        check=True,
    )


def test_normalize_audio_missing_file(tmp_path):
    non_existent_path = tmp_path / "nonexistent.wav"
    output_path = tmp_path / "output_normalized.wav"
    with pytest.raises((subprocess.CalledProcessError, FileNotFoundError)):
        normalize_audio(str(non_existent_path), str(output_path))


@patch("subprocess.run", side_effect=PermissionError("Permission denied"))
def test_normalize_audio_permission_error(mock_run, dummy_audio_file):
    input_path, output_path = dummy_audio_file
    with pytest.raises(PermissionError, match="Permission denied"):
        normalize_audio(str(input_path), str(output_path))


@patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffmpeg"))
def test_normalize_audio_ffmpeg_failure(mock_run, dummy_audio_file):
    input_path, output_path = dummy_audio_file
    with pytest.raises(subprocess.CalledProcessError):
        normalize_audio(str(input_path), str(output_path))
