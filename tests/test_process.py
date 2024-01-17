import unittest
from unittest.mock import patch
from process import get_video_upload_date, get_formatted_time, download_audio_from_youtube

class TestDownloadAudioFromYoutube(unittest.TestCase):

    def setUp(self):
        self.valid_youtube_url = "https://www.youtube.com/watch?v=1PG_7DmGoHw"
        self.valid_start_time = "00:00:10"
        self.valid_end_time = "00:01:00"
        self.expected_upload_date = "2024-01-14"

    @patch('process.subprocess.run')
    def test_download_with_valid_parameters(self, mock_subprocess_run):
        download_audio_from_youtube(self.valid_youtube_url, self.valid_start_time, self.valid_end_time, self.expected_upload_date)
        mock_subprocess_run.assert_called_once()


class TestAudioProcessingScript(unittest.TestCase):
    
    def setUp(self):
        self.youtube_url = 'https://www.youtube.com/watch?v=1PG_7DmGoHw'
        self.expected_date = '2024-01-14'

    def test_get_video_upload_date(self):
        actual_date = get_video_upload_date(self.youtube_url)
        self.assertEqual(actual_date, self.expected_date)


class TestFormattedTime(unittest.TestCase):
    
    def setUp(self):
        self.valid_time_input = '01:02:03'
        self.empty_time_input = ''
        self.default_time_output = '00:00:00'

    def test_get_formatted_time_for_valid_input(self):
        self.assertEqual(get_formatted_time(self.valid_time_input), self.valid_time_input)

    def test_get_formatted_time_for_empty_input(self):
        self.assertEqual(get_formatted_time(self.empty_time_input), self.default_time_output)
        self.assertEqual(get_formatted_time(None), self.default_time_output)



if __name__ == '__main__':
    unittest.main()
