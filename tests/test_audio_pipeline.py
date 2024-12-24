import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.pipelines.audio_pipeline_factory import create_audio_pipeline


class TestAudioPipeline(unittest.TestCase):
    @patch("app.downloaders.youtube_downloader.YouTubeDownloader")
    @patch("app.downloaders.s3_downloader.S3Downloader")
    @patch("app.steps.merge_step.subprocess.run")  # Mock FFmpeg calls
    @patch("app.steps.move_step.shutil.move")  # Mock file move
    def test_audio_pipeline(
        self, mock_move, mock_subprocess_run, MockS3Downloader, MockYouTubeDownloader
    ):
        # Mock datetime to ensure consistent date in tests
        mock_date = "2024-12-24"
        with patch("app.pipelines.audio_pipeline_factory.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = mock_date

            # Mock YouTube downloader behavior
            mock_youtube = MockYouTubeDownloader.return_value
            mock_youtube.download.return_value = (
                f"cache/audio/{mock_date}/my-weekly-sermon/audio.mp3"
            )

            # Mock S3 downloader behavior
            mock_s3 = MockS3Downloader.return_value
            mock_s3.download.side_effect = [
                "cache/s3/audio_intro.mp3",
                "cache/s3/audio_outro.mp3",
            ]

            # Configuration for the pipeline
            config = {
                "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "stream_id": "my-weekly-sermon",
                "audio": {
                    "intro_url": "https://example.com/audio_intro.mp3",
                    "outro_url": "https://example.com/audio_outro.mp3",
                    "trim": {
                        "start_time": "00:00:10",
                        "end_time": "00:01:00",
                    },
                },
            }

            # Create pipeline and execute it
            pipeline = create_audio_pipeline(config)
            pipeline_data = pipeline.execute({})

            # Assertions
            self.assertEqual(
                pipeline_data["audio_file_path"],
                f"cache/audio/{mock_date}/my-weekly-sermon/audio.mp3",
            )
            self.assertEqual(
                pipeline_data["audio_intro_path"], "cache/s3/audio_intro.mp3"
            )
            self.assertEqual(
                pipeline_data["audio_outro_path"], "cache/s3/audio_outro.mp3"
            )
            self.assertEqual(
                pipeline_data["merged_audio_file_path"],
                f"cache/audio/{mock_date}/my-weekly-sermon/merged_audio.mp3",
            )
            self.assertEqual(
                pipeline_data["final_output_path"],
                f"output/my-weekly-sermon/{mock_date}.mp3",
            )

            # Verify steps were called
            mock_youtube.download.assert_called_once_with(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                f"cache/audio/{mock_date}/my-weekly-sermon/audio.%(ext)s",
            )
            self.assertEqual(mock_s3.download.call_count, 2)
            mock_s3.download.assert_any_call(
                "https://example.com/audio_intro.mp3", "cache/s3/audio_intro.mp3"
            )
            mock_s3.download.assert_any_call(
                "https://example.com/audio_outro.mp3", "cache/s3/audio_outro.mp3"
            )
            mock_subprocess_run.assert_called()  # Ensure FFmpeg was called
            mock_move.assert_called_once_with(
                f"cache/audio/{mock_date}/my-weekly-sermon/merged_audio.mp3",
                f"output/my-weekly-sermon/{mock_date}.mp3",
            )


if __name__ == "__main__":
    unittest.main()
