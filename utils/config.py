import os
from dotenv import load_dotenv  # type: ignore
from utils.helpers import print_error
from utils.time import get_formatted_time

load_dotenv()


def parse_audio_parameters():
    """Parse and format parameters from the env file."""
    try:
        youtube_url = os.getenv("URL")
        start_time = get_formatted_time(os.getenv("START"))
        end_time = get_formatted_time(os.getenv("END"))
    except KeyError as e:
        print_error(f"Missing necessary env parameter: {e}")
        exit(1)
    return youtube_url, start_time, end_time


def parse_video_parameters():
    """Parse and format parameters from the env file."""
    try:
        youtube_url = os.getenv("URL")
        start_time = get_formatted_time(os.getenv("START"))
        end_time = get_formatted_time(os.getenv("END"))
        intro_url = os.getenv("VIDEO_INTRO")
        outro_url = os.getenv("VIDEO_OUTRO")
    except KeyError as e:
        print_error(f"Missing necessary env parameter: {e}")
        exit(1)
    return youtube_url, start_time, end_time, intro_url, outro_url
