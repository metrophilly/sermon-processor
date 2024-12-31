import pytest
from unittest.mock import patch, MagicMock
from app.downloaders.youtube_downloader import YouTubeDownloader


@pytest.fixture
def youtube_downloader():
    return YouTubeDownloader(audio_only=True, quiet=True)


@patch("app.downloaders.youtube_downloader.YoutubeDL")
def test_get_output_path(mock_ytdl, youtube_downloader):
    # Arrange
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    destination = "output/test_audio.%(ext)s"
    mock_ytdl_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_ytdl_instance
    mock_ytdl_instance.extract_info.return_value = {"id": "dQw4w9WgXcQ"}
    mock_ytdl_instance.prepare_filename.return_value = "output/test_audio.mp3"

    # Act
    output_path = youtube_downloader.get_output_path(url, destination)

    # Assert
    mock_ytdl_instance.extract_info.assert_called_once_with(url, download=False)
    assert output_path == "output/test_audio.mp3"


@patch("app.downloaders.youtube_downloader.YoutubeDL")
def test_download(mock_ytdl, youtube_downloader, tmp_path):
    # Arrange
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    destination = str(tmp_path / "test_audio.%(ext)s")
    mock_ytdl_instance = MagicMock()
    mock_ytdl.return_value.__enter__.return_value = mock_ytdl_instance
    mock_ytdl_instance.extract_info.return_value = {"id": "dQw4w9WgXcQ"}
    mock_ytdl_instance.prepare_filename.return_value = str(tmp_path / "test_audio.mp3")

    # Act
    output_path = youtube_downloader.download(url, destination)

    # Assert
    mock_ytdl_instance.extract_info.assert_called_once_with(url)
    assert output_path == str(tmp_path / "test_audio.mp3")
