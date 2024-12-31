import os
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from app.steps.merge_audio_step import merge_audio_step
from app.data_models.pipeline_data import PipelineData


@pytest.fixture
def pipeline_data_with_audio_paths(tmp_path):
    """
    Creates temporary intro, main, and outro audio files, placing them into
    a PipelineData instance.
    """
    intro = tmp_path / "intro.wav"
    main = tmp_path / "main.wav"
    outro = tmp_path / "outro.wav"

    for f in [intro, main, outro]:
        f.write_text("dummy audio content")

    data = PipelineData(
        intro_file_path=str(intro),
        active_file_path=str(main),
        outro_file_path=str(outro),
    )
    return data


@patch("app.steps.merge_audio_step.normalize_audio")
@patch("subprocess.run")
def test_merge_step_success(
    mock_subprocess_run, mock_normalize_audio, pipeline_data_with_audio_paths
):
    """
    Verifies a successful merge scenario:
    1) Three calls to normalize_audio (intro, main, outro).
    2) One ffmpeg call via subprocess.run for merging.
    3) Final output is set to <main>_merged.mp3 in PipelineData.
    """
    data = pipeline_data_with_audio_paths
    output_format = "mp3"

    # Mock out normalize_audio so it doesn't actually run ffmpeg
    mock_normalize_audio.side_effect = lambda in_path, out_path, **kwargs: out_path

    # Act
    result = merge_audio_step(data=data, output_format=output_format)

    # Assert: normalize_audio should be called exactly 3 times
    assert mock_normalize_audio.call_count == 3

    main_base, _ = os.path.splitext(data.active_file_path)
    merged_file = f"{main_base}.{output_format}"

    mock_subprocess_run.assert_called_once()

    assert result.active_file_path == merged_file


@patch(
    "app.steps.merge_audio_step.normalize_audio",
    side_effect=PermissionError("Permission denied"),
)
def test_merge_step_normalize_permission_error(
    mock_normalize, pipeline_data_with_audio_paths
):
    """
    If we get a permission error during normalization, ensure it propagates.
    """
    data = pipeline_data_with_audio_paths
    with pytest.raises(PermissionError, match="Permission denied"):
        merge_audio_step(data=data, output_format="mp3")


@patch("app.steps.merge_audio_step.normalize_audio")
@patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffmpeg"))
def test_merge_step_ffmpeg_failure(
    mock_subprocess_run, mock_normalize, pipeline_data_with_audio_paths
):
    """
    If ffmpeg fails during the merge step, a CalledProcessError should be raised.
    """
    data = pipeline_data_with_audio_paths
    with pytest.raises(subprocess.CalledProcessError):
        merge_audio_step(data=data, output_format="mp3")
