# utils/youtube.py
import subprocess
import json


def get_youtube_upload_date(youtube_url):
    """
    Fetches the upload date of a YouTube video using yt-dlp.

    Args:
        youtube_url (str): The URL of the YouTube video.

    Returns:
        str: The upload date in 'YYYY-MM-DD' format, or None if not retrievable.
    """
    try:
        # Use yt-dlp to fetch the metadata as JSON
        command = ["yt-dlp", "--dump-json", youtube_url]
        result = subprocess.run(command, stdout=subprocess.PIPE, check=True, text=True)
        video_data = json.loads(result.stdout)

        # Extract and format the upload date
        upload_date = video_data.get("upload_date")  # Format: 'YYYYMMDD'
        if upload_date:
            return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    except Exception as e:
        print(f"Failed to fetch upload date for {youtube_url}: {e}")
        return None
