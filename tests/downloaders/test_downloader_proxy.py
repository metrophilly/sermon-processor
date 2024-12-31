import os
from unittest.mock import MagicMock
import pytest
from app.downloaders.downloader_proxy import DownloaderProxy


@pytest.fixture
def mock_downloader():
    return MagicMock()


@pytest.fixture
def downloader_proxy(mock_downloader, tmp_path):
    # Use tmp_path for a temporary cache directory
    return DownloaderProxy(real_downloader=mock_downloader, cache_dir=str(tmp_path))


def test_get_cache_path_with_date_and_stream_id(downloader_proxy, tmp_path):
    date = "2024-12-26"
    stream_id = "test_stream"
    filename = "test_file.wav"

    cache_path = downloader_proxy._get_cache_path(date, stream_id, filename)

    expected_path = os.path.join(tmp_path, date, stream_id, filename)
    assert cache_path == expected_path
    assert os.path.exists(os.path.dirname(cache_path))


def test_get_cache_path_without_stream_id(downloader_proxy, tmp_path):
    date = None
    stream_id = None
    filename = "test_file.wav"

    cache_path = downloader_proxy._get_cache_path(date, stream_id, filename)

    expected_path = os.path.join(tmp_path, filename)
    assert cache_path == expected_path
    assert os.path.exists(os.path.dirname(cache_path))


def test_download_with_cache_hit_youtube(downloader_proxy, mock_downloader, tmp_path):
    url = "https://example.com/test_file.m4a"
    date = "2024-12-26"
    stream_id = "test_stream"
    filename = "test_file.m4a"
    cached_file_path = downloader_proxy._get_cache_path(date, stream_id, filename)

    # Mock `get_output_path` for YouTubeDownloader
    mock_downloader.get_output_path.return_value = cached_file_path

    # Create cached file
    os.makedirs(os.path.dirname(cached_file_path), exist_ok=True)
    with open(cached_file_path, "w") as f:
        f.write("cached content")

    # Act
    result_path = downloader_proxy.download(url, date, stream_id, filename)

    # Assert
    mock_downloader.get_output_path.assert_called_once_with(url, cached_file_path)
    mock_downloader.download.assert_not_called()
    assert result_path == cached_file_path


def test_download_with_cache_hit_s3(downloader_proxy, mock_downloader, tmp_path):
    url = "https://example.com/test_file.m4a"
    date = "2024-12-26"
    stream_id = "test_stream"
    filename = "test_file.m4a"
    cached_file_path = downloader_proxy._get_cache_path(date, stream_id, filename)

    # Mock behavior for a non-YouTubeDownloader (e.g., S3Downloader)
    del mock_downloader.get_output_path  # Simulate `get_output_path` not existing

    # Create cached file
    os.makedirs(os.path.dirname(cached_file_path), exist_ok=True)
    with open(cached_file_path, "w") as f:
        f.write("cached content")

    # Act
    result_path = downloader_proxy.download(url, date, stream_id, filename)

    # Assert
    mock_downloader.download.assert_not_called()
    assert result_path == cached_file_path


def test_download_with_cache_miss_youtube(downloader_proxy, mock_downloader, tmp_path):
    url = "https://example.com/test_file.m4a"
    date = "2024-12-26"
    stream_id = "test_stream"
    filename = "test_file.m4a"
    cache_path = downloader_proxy._get_cache_path(date, stream_id, filename)
    resolved_path = os.path.join(tmp_path, date, stream_id, filename)

    # Mock `get_output_path` and `download` behavior
    mock_downloader.get_output_path.return_value = resolved_path
    mock_downloader.download.return_value = resolved_path

    # Act
    result_path = downloader_proxy.download(url, date, stream_id, filename)

    # Assert
    mock_downloader.get_output_path.assert_called_once_with(url, cache_path)
    mock_downloader.download.assert_called_once_with(url, resolved_path)
    assert result_path == resolved_path


def test_download_with_cache_miss_s3(downloader_proxy, mock_downloader, tmp_path):
    url = "https://example.com/test_file.m4a"
    date = "2024-12-26"
    stream_id = "test_stream"
    filename = "test_file.m4a"
    expected_path = downloader_proxy._get_cache_path(date, stream_id, filename)

    # Mock behavior for a non-YouTubeDownloader
    del mock_downloader.get_output_path  # Simulate `get_output_path` not existing
    mock_downloader.download.return_value = expected_path

    # Act
    result_path = downloader_proxy.download(url, date, stream_id, filename)

    # Assert
    mock_downloader.download.assert_called_once_with(url, expected_path)
    assert result_path == expected_path


def test_download_with_get_output_path(downloader_proxy, mock_downloader, tmp_path):
    url = "https://example.com/test_file.mp3"
    date = "2024-12-26"
    stream_id = "test_stream"
    filename = "test_file.mp3"
    cache_path = downloader_proxy._get_cache_path(date, stream_id, filename)
    expected_path = os.path.join(tmp_path, date, stream_id, filename)

    # Mock real_downloader behavior
    mock_downloader.get_output_path.return_value = expected_path
    mock_downloader.download.return_value = expected_path

    result_path = downloader_proxy.download(url, date, stream_id, filename)

    mock_downloader.get_output_path.assert_called_once_with(url, cache_path)
    mock_downloader.download.assert_called_once_with(url, expected_path)
    assert result_path == expected_path
