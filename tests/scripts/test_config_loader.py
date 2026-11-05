import unittest
import json
from scripts.config_loader import load_and_validate_config


class TestConfigLoader(unittest.TestCase):
    def setUp(self):
        # Sample config for testing
        self.sample_json_path = "tests/sample_pipeline_config.json"
        self.sample_config = {
            "youtube_url": "https://www.youtube.com/watch?v=example",
            "manual_download": False,
            "stream_id": "my-weekly-sermon",
            "trim": {"start_time": "00:00:10", "end_time": "00:00:20"},
            "audio": {
                "intro_url": "https://s3.example.com/audio_intro.mp3",
                "outro_url": "https://s3.example.com/audio_outro.mp3",
            },
            "video": {
                "intro_url": "https://s3.example.com/video_intro.mp4",
                "outro_url": "https://s3.example.com/video_outro.mp4",
            },
        }

        with open(self.sample_json_path, "w") as f:
            json.dump(self.sample_config, f)

    def tearDown(self):
        # Clean up the sample config file
        import os

        if os.path.exists(self.sample_json_path):
            os.remove(self.sample_json_path)

    def test_load_config(self):
        # Load the JSON config
        config = load_and_validate_config(self.sample_json_path)

        # Verify the fields
        self.assertEqual(
            config["youtube_url"], "https://www.youtube.com/watch?v=example"
        )
        self.assertEqual(config["stream_id"], "my-weekly-sermon")
        self.assertEqual(
            config["audio"]["intro_url"], "https://s3.example.com/audio_intro.mp3"
        )
        self.assertEqual(
            config["audio"]["outro_url"], "https://s3.example.com/audio_outro.mp3"
        )
        self.assertEqual(config["trim"]["start_time"], "00:00:10")
        self.assertEqual(config["trim"]["end_time"], "00:00:20")

        self.assertEqual(
            config["video"]["intro_url"], "https://s3.example.com/video_intro.mp4"
        )
        self.assertEqual(
            config["video"]["outro_url"], "https://s3.example.com/video_outro.mp4"
        )

    def test_missing_config_file(self):
        # Verify that a missing file raises an exception
        with self.assertRaises(FileNotFoundError):
            load_and_validate_config("tests/non_existent_config.json")


if __name__ == "__main__":
    unittest.main()
