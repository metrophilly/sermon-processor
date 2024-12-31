import requests
import pytest
from unittest.mock import patch, MagicMock
from app.downloaders.s3_downloader import S3Downloader


@pytest.fixture
def s3_downloader():
    return S3Downloader()


def test_s3_download_success(s3_downloader, tmp_path):
    # Arrange
    url = "https://s3.amazonaws.com/bucket/intro.mp4"
    destination = tmp_path / "bucket/intro.mp4"
    mock_content = b"test content"

    # Mock the requests.get response
    mock_response = MagicMock()
    mock_response.iter_content.return_value = [mock_content]
    mock_response.raise_for_status = MagicMock()

    with patch(
        "app.downloaders.s3_downloader.requests.get", return_value=mock_response
    ) as mock_get:
        # Act
        result = s3_downloader.download(url, str(destination))

        # Assert
        mock_get.assert_called_once_with(url, stream=True)
        mock_response.raise_for_status.assert_called_once()
        assert destination.exists()  # Ensure file was created
        with open(destination, "rb") as f:
            assert f.read() == mock_content  # Validate file content
        assert result == str(destination)  # Ensure the returned path is correct


def test_s3_download_failure(s3_downloader):
    # Arrange
    url = "https://s3.amazonaws.com/bucket/intro.mp4"
    destination = "invalid/path/intro.mp4"

    # Mock the requests.get response to raise an HTTP error
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        "403 Forbidden"
    )

    with patch(
        "app.downloaders.s3_downloader.requests.get", return_value=mock_response
    ):
        # Act & Assert
        with pytest.raises(requests.exceptions.HTTPError, match="403 Forbidden"):
            s3_downloader.download(url, destination)
