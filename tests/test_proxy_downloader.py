import unittest
import os
from unittest.mock import patch, MagicMock
from app.downloaders.downloader_proxy import DownloaderProxy


class TestProxyDownloader(unittest.TestCase):
    """
    Tests for DownloaderProxy with separate cache directories for YouTube and S3.
    """

    def setUp(self):
        # Create mock downloaders
        self.mock_yt_downloader = MagicMock()
        self.mock_s3_downloader = MagicMock()

        # Create separate proxies for YouTube and S3
        self.youtube_proxy = DownloaderProxy(
            self.mock_yt_downloader, cache_dir="test_cache/youtube"
        )
        self.s3_proxy = DownloaderProxy(
            self.mock_s3_downloader, cache_dir="test_cache/s3"
        )

        # Create test directories
        os.makedirs("test_cache/youtube/2024-12-23/weekly-sermon", exist_ok=True)
        os.makedirs("test_cache/s3/2024-12-23/weekly-sermon", exist_ok=True)

    def tearDown(self):
        # Clean up test directory
        import shutil

        shutil.rmtree("test_cache", ignore_errors=True)

    def test_youtube_proxy_uses_cache(self):
        """
        Verify that the YouTube proxy doesn't re-download when a file is cached.
        """
        test_url = "https://youtube.com/video"
        date = "2024-12-23"
        stream_id = "weekly-sermon"
        filename = "video.mp4"

        cached_path = f"test_cache/youtube/{date}/{stream_id}/{filename}"

        # Create a dummy cached file
        with open(cached_path, "w") as f:
            f.write("cached data")

        result = self.youtube_proxy.download(test_url, date, stream_id, filename)
        self.assertEqual(result, cached_path)
        self.mock_yt_downloader.download.assert_not_called()

    def test_youtube_proxy_downloads_if_not_cached(self):
        """
        Verify that the YouTube proxy calls the real downloader if no cache file exists.
        """
        test_url = "https://youtube.com/video"
        date = "2024-12-23"
        stream_id = "weekly-sermon"
        filename = "video.mp4"

        with patch("builtins.open", new_callable=MagicMock):
            result = self.youtube_proxy.download(test_url, date, stream_id, filename)

        # Verify the real downloader was called
        self.mock_yt_downloader.download.assert_called_once()
        cached_path = f"test_cache/youtube/{date}/{stream_id}/{filename}"
        self.assertEqual(result, cached_path)

    def test_s3_proxy_uses_cache(self):
        """
        Verify that the S3 proxy doesn't re-download when a file is cached.
        """
        test_url = "https://example.s3.amazonaws.com/intro.mp4"
        date = "2024-12-23"
        stream_id = "weekly-sermon"
        filename = "intro.mp4"

        cached_path = f"test_cache/s3/{date}/{stream_id}/{filename}"

        # Create a dummy cached file
        with open(cached_path, "w") as f:
            f.write("cached data")

        result = self.s3_proxy.download(test_url, date, stream_id, filename)
        self.assertEqual(result, cached_path)
        self.mock_s3_downloader.download.assert_not_called()

    def test_s3_proxy_downloads_if_not_cached(self):
        """
        Verify that the S3 proxy calls the real downloader if no cache file exists.
        """
        test_url = "https://example.s3.amazonaws.com/intro.mp4"
        date = "2024-12-23"
        stream_id = "weekly-sermon"
        filename = "intro.mp4"

        with patch("builtins.open", new_callable=MagicMock):
            result = self.s3_proxy.download(test_url, date, stream_id, filename)

        # Verify the real downloader was called
        self.mock_s3_downloader.download.assert_called_once()
        cached_path = f"test_cache/s3/{date}/{stream_id}/{filename}"
        self.assertEqual(result, cached_path)


if __name__ == "__main__":
    unittest.main()
