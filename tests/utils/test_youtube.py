# tests/utils/test_youtube.py
import pytest
from app.utils.youtube import get_youtube_upload_date


@pytest.mark.parametrize(
    "youtube_url,expected_date",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "2009-10-25"),
        ("https://www.youtube.com/watch?v=abcdefghijk", None),  # Simulate failure
    ],
)
def test_get_youtube_upload_date(youtube_url, expected_date, mocker):
    """
    Test fetching the upload date from a YouTube video URL.
    """
    mock_subprocess = mocker.patch("subprocess.run")
    if expected_date:
        # Simulate successful yt-dlp JSON output
        mock_subprocess.return_value.stdout = (
            f'{{"upload_date": "{expected_date.replace("-", "")}"}}'
        )
    else:
        # Simulate yt-dlp failure
        mock_subprocess.side_effect = Exception("yt-dlp error")

    date = get_youtube_upload_date(youtube_url)
    assert date == expected_date
