import unittest
import os
from unittest.mock import patch, MagicMock
from app.downloaders.youtube_downloader import YouTubeDownloader
from app.downloaders.s3_downloader import S3Downloader
import pytest


class TestYouTubeDownloader(unittest.TestCase):
    @patch("app.downloaders.youtube_downloader.YoutubeDL")
    def test_download_audio_only(self, MockYoutubeDL):
        downloader = YouTubeDownloader(audio_only=True)
        test_url = "https://youtube.com/test"
        destination = "test_audio.mp3"

        mock_ydl_instance = MockYoutubeDL.return_value.__enter__.return_value
        mock_ydl_instance.download.return_value = None

        downloader.download(test_url, destination)

        # Verify we used "bestaudio/best"
        MockYoutubeDL.assert_called_once_with(
            {
                "format": "bestaudio/best",
                "outtmpl": "./test_audio.mp3",
                "quiet": False,
                "postprocessors": {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                    "nopostoverwrites": False,
                },
            }
        )
        mock_ydl_instance.download.assert_called_once_with([test_url])

    @pytest.mark.skip
    @patch("app.downloaders.youtube_downloader.YoutubeDL")
    def test_download_video_audio(self, MockYoutubeDL):
        downloader = YouTubeDownloader(audio_only=False)
        test_url = "https://youtube.com/test"
        destination = "test_video.mp4"

        mock_ydl_instance = MockYoutubeDL.return_value.__enter__.return_value
        mock_ydl_instance.download.return_value = None

        downloader.download(test_url, destination)

        # Verify we used "bestvideo+bestaudio/best"
        MockYoutubeDL.assert_called_once_with(
            {
                "format": "bestvideo+bestaudio/best",
                "outtmpl": "./test_video.mp4",
                "quiet": False,
            }
        )
        mock_ydl_instance.download.assert_called_once_with([test_url])


class TestS3Downloader(unittest.TestCase):
    """
    Tests for the S3Downloader using requests with a mock.
    """

    @patch("app.downloaders.s3_downloader.requests.get")
    def test_s3_downloader(self, mock_get):
        """
        Test that the S3 downloader correctly downloads a file.
        """
        downloader = S3Downloader()
        test_url = "https://example.s3.amazonaws.com/test.mp4"
        destination = "test_file.mp4"

        # Mock requests.get
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_get.return_value = mock_response

        # Perform the download
        downloader.download(test_url, destination)

        # Assert requests.get was called properly
        mock_get.assert_called_once_with(test_url, stream=True)

        # Verify file content
        with open(destination, "rb") as f:
            content = f.read()
            self.assertEqual(content, b"chunk1chunk2")

        # Cleanup
        if os.path.exists(destination):
            os.remove(destination)


if __name__ == "__main__":
    unittest.main()
