import os
from app.constants import PipelineKeys
import pytest
from unittest.mock import patch
from app.steps.move_step import move_step
from app.data_models.pipeline_data import PipelineData


@pytest.fixture
def pipeline_data_with_paths(tmp_path):
    """
    Fixture to create a PipelineData object with dummy source and output paths.
    """
    source_file = tmp_path / "source.wav"
    source_file.write_text("dummy audio content")

    output_dir = tmp_path / "output"
    output_filename = output_dir / "final_output.wav"

    return (
        PipelineData(
            active_file_path=str(source_file),
            final_output_path=None,
        ),
        str(source_file),
        str(output_filename),
    )


def test_move_step_success(pipeline_data_with_paths):
    """
    Test that move_step successfully moves a file to the destination.
    """
    data, source_file, output_filename = pipeline_data_with_paths

    # Act
    result = move_step(data=data, output_filename=output_filename)

    # Assert: File has been moved
    assert not os.path.exists(source_file), "Source file should no longer exist."
    assert os.path.exists(output_filename), "Destination file should exist."
    assert result.final_output_path == output_filename


def test_move_step_with_source_key(tmp_path):
    """
    Test move_step with a specified `source_key`.
    """
    source_key = PipelineKeys.MAIN_FILE_PATH
    source_file = tmp_path / "source.wav"
    source_file.write_text("dummy content")
    output_file = tmp_path / "final_output.wav"

    data = PipelineData(
        main_file_path=str(source_file),
        final_output_path=None,
    )

    # Act
    result = move_step(
        data=data, source_key=source_key, output_filename=str(output_file)
    )

    # Assert
    assert not os.path.exists(source_file)
    assert os.path.exists(output_file)
    assert result.final_output_path == str(output_file)


def test_move_step_missing_source_file(pipeline_data_with_paths):
    """
    Test that move_step raises a ValueError if the source file does not exist.
    """
    data, source_file, output_filename = pipeline_data_with_paths

    # Delete the source file to simulate a missing file
    os.remove(source_file)

    with pytest.raises(ValueError, match=f"Source file does not exist: {source_file}"):
        move_step(data=data, output_filename=output_filename)


def test_move_step_missing_output_filename(pipeline_data_with_paths):
    """
    Test that move_step raises a ValueError if no output filename is provided.
    """
    data, _, _ = pipeline_data_with_paths

    with pytest.raises(ValueError, match="Output filename must be specified."):
        move_step(data=data, output_filename=None)


@patch("shutil.move", side_effect=PermissionError("Permission denied"))
def test_move_step_permission_error(mock_move, pipeline_data_with_paths):
    """
    Test that move_step raises a PermissionError if the file cannot be moved.
    """
    data, source_file, output_filename = pipeline_data_with_paths

    with pytest.raises(PermissionError, match="Permission denied"):
        move_step(data=data, output_filename=output_filename)


def test_move_step_creates_output_directory(tmp_path):
    """
    Test that move_step creates the output directory if it doesn't exist.
    """
    source_file = tmp_path / "source.wav"
    source_file.write_text("dummy content")
    output_dir = tmp_path / "nonexistent_dir"
    output_file = output_dir / "final_output.wav"

    data = PipelineData(
        active_file_path=str(source_file),
        final_output_path=None,
    )

    # Act
    move_step(data=data, output_filename=str(output_file))

    # Assert: The directory should now exist, and the file should be moved
    assert os.path.exists(output_dir), "Output directory should be created."
    assert os.path.exists(output_file), "File should be moved to the output directory."
