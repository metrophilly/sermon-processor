import pytest
from unittest.mock import MagicMock
from app.data_models.pipeline_data import PipelineData
from app.constants import PipelineKeys
from app.steps.download_step import download_step


@pytest.fixture
def mock_downloader():
    """Fixture to create a mock downloader."""
    return MagicMock()


@pytest.fixture
def pipeline_data():
    """Fixture to create a fresh PipelineData object."""
    return PipelineData()


def test_successful_download(mock_downloader, pipeline_data, tmp_path):
    # Arrange
    url = "https://example.com/file"
    filename = "test_file.txt"
    key = "test_key"
    file_path = tmp_path / filename
    file_path.write_text("dummy content")  # Create a temporary file
    mock_downloader.download.return_value = str(file_path)

    # Act
    result = download_step(
        data=pipeline_data,
        downloader=mock_downloader,
        url=url,
        filename=filename,
        key=key,
    )

    # Assert
    assert getattr(result, key) == str(file_path)
    assert getattr(result, PipelineKeys.ACTIVE_FILE_PATH) == str(file_path)
    assert str(file_path) in result.downloaded_files


def test_file_not_found_error(mock_downloader, pipeline_data):
    # Arrange
    url = "https://example.com/nonexistent_file"
    filename = "nonexistent_file.txt"
    key = "test_key"
    mock_downloader.download.return_value = "/invalid/path/nonexistent_file.txt"

    # Act & Assert
    with pytest.raises(FileNotFoundError):
        download_step(
            data=pipeline_data,
            downloader=mock_downloader,
            url=url,
            filename=filename,
            key=key,
        )


def test_invalid_file_extension(mock_downloader, pipeline_data, tmp_path):
    # Arrange
    url = "https://example.com/file"
    filename = "invalid_file"
    key = "test_key"
    file_path = tmp_path / filename  # No file extension
    file_path.write_text("dummy content")  # Create a temporary file
    mock_downloader.download.return_value = str(file_path)

    # Act & Assert
    with pytest.raises(ValueError, match="No extension found for file:"):
        download_step(
            data=pipeline_data,
            downloader=mock_downloader,
            url=url,
            filename=filename,
            key=key,
        )
