import os
import pytest
from unittest.mock import patch, MagicMock
from app.steps.trim_step import trim_step
from app.data_models.pipeline_data import PipelineData
from app.constants import PipelineKeys


@pytest.fixture
def pipeline_data(tmp_path):
    """Fixture for PipelineData with a temporary input file."""
    data = PipelineData()
    input_file = tmp_path / "input_audio.wav"
    input_file.write_text("dummy content")  # Simulate a file
    data.active_file_path = str(input_file)
    return data


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run to prevent actual ffmpeg calls."""
    with patch("app.steps.trim_step.subprocess.run") as mock_run:
        yield mock_run


@pytest.fixture
def mock_os_path_exists():
    """Mock os.path.exists to control file existence checks."""
    with patch("app.steps.trim_step.os.path.exists") as mock_exists:
        yield mock_exists


def test_trim_step_success_audio(
    pipeline_data, mock_subprocess_run, mock_os_path_exists
):
    # Arrange
    start_time = "00:00:01"
    end_time = "00:00:05"
    overwrite = False
    input_file = pipeline_data.active_file_path
    output_file = input_file.replace(".wav", "_trimmed.wav")

    mock_os_path_exists.side_effect = (
        lambda path: path == input_file
    )  # Input exists, output does not

    # Act
    result = trim_step(
        data=pipeline_data,
        start_time=start_time,
        end_time=end_time,
        overwrite=overwrite,
    )

    # Assert
    mock_subprocess_run.assert_called_once_with(
        [
            "ffmpeg",
            "-i",
            input_file,
            "-ss",
            start_time,
            "-to",
            end_time,
            "-c",
            "copy",
            output_file,
        ],
        check=True,
    )
    assert result.active_file_path == output_file


def test_trim_step_overwrite(pipeline_data, mock_subprocess_run, mock_os_path_exists):
    # Arrange
    start_time = "00:00:01"
    end_time = "00:00:05"
    overwrite = True
    input_file = pipeline_data.active_file_path
    output_file = input_file.replace(".wav", "_trimmed.wav")

    mock_os_path_exists.side_effect = lambda path: path in {
        input_file,
        output_file,
    }

    # Act
    result = trim_step(
        data=pipeline_data,
        start_time=start_time,
        end_time=end_time,
        overwrite=overwrite,
    )

    # Assert
    mock_subprocess_run.assert_called_once_with(
        [
            "ffmpeg",
            "-i",
            input_file,
            "-ss",
            start_time,
            "-to",
            end_time,
            "-c",
            "copy",
            output_file,
        ],
        check=True,
    )
    assert result.active_file_path == output_file


def test_trim_step_no_input_file(mock_subprocess_run):
    # Arrange
    data = PipelineData()  # No input file set
    start_time = "00:00:01"
    end_time = "00:00:05"

    # Act & Assert
    with pytest.raises(ValueError, match="No input file found"):
        trim_step(data, start_time, end_time)


def test_trim_step_output_already_exists(
    pipeline_data, mock_subprocess_run, mock_os_path_exists
):
    # Arrange
    start_time = "00:00:01"
    end_time = "00:00:05"
    overwrite = False
    output_file = pipeline_data.active_file_path.replace(".wav", "_trimmed.wav")
    mock_os_path_exists.return_value = True  # Simulate output file exists

    # Act
    result = trim_step(
        data=pipeline_data,
        start_time=start_time,
        end_time=end_time,
        overwrite=overwrite,
    )

    # Assert
    mock_subprocess_run.assert_not_called()
    assert result.active_file_path == output_file
