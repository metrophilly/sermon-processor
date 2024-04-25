import re
import os

import requests

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OUTPUT_BASE_DIR = os.path.join(SCRIPT_DIR, 'data')

def is_valid_time(time_str):
    """Check if the time string is in a valid HH:MM:SS, MM:SS, or SS format."""
    # Regular expression to match valid time formats
    time_pattern = re.compile(r'^(\d{1,2}:)?([0-5]?\d:)?[0-5]?\d$')
    return bool(time_pattern.match(time_str)) if time_str else False


def is_valid_audio_file(file_path):
    return os.path.exists(file_path) and os.path.getsize(file_path) > 1000


def confirmation_printout(upload_date):
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RESET = '\033[0m'

    print(f"""{GREEN}
    ===================
    🎛️ SERMON PROCESSOR
    ===================

    Your file has been processed and saved to {YELLOW}./data/{upload_date}_ready_to_scrub.mp3{GREEN}.

    Please follow the manual finishing touches:

    1. Open the audio file in Audacity or a similar tool.
    2. Trim excess silence between clips, aiming for 1.5-second gaps (focus on the
      intro, scripture passage, and the sermon).
    3. Smooth out any rough transitions or "bumps" where clips are stitched
      together.
    4. Trim the pastor's final prayer at the end, while keeping Rhea's outro intact.
    5. Export the edited audio as an MP3 file named "yyyy-mm-dd.mp3".
    6. Send to the reviewer.

    Remember: Careful editing ensures a polished final product, and your attention to
    detail will enhance our listeners' experience. Thank you for your contribution!
    {RESET}""")


def get_formatted_time(time_input):
    return time_input if time_input else "00:00:00"


def read_config_file(config_file_path):
    """Read configuration from a file and return a dictionary of parameters."""
    config = {}
    try:
        with open(config_file_path, 'r') as file:
            for line in file:
                key, value = line.strip().split('=', 1)
                config[key.strip().lower()] = value.strip()
    except FileNotFoundError:
        print(f"Configuration file not found: {config_file_path}")
        print(f"Please run `cp config.example.txt config.txt` and adjust the config parameters")
        exit(1)
    except ValueError:
        print("Configuration file format error, should be 'key=value'")
        exit(1)
    return config


def parse_audio_parameters(config):
    """Parse and format parameters from the configuration dictionary."""
    try:
        youtube_url = config['url']
        start_time = get_formatted_time(config['start'])
        end_time = get_formatted_time(config['end'])
    except KeyError as e:
        print(f"Missing necessary configuration parameter: {e}")
        exit(1)
    return youtube_url, start_time, end_time


def parse_video_parameters(config):
    """Parse and format parameters from the configuration dictionary."""
    try:
        intro_url = config['video_intro']
        outro_url = config['video_outro']
    except KeyError as e:
        print(f"Missing necessary configuration parameter: {e}")
        exit(1)
    return intro_url, outro_url


def confirm_parameters(youtube_url, start_time, end_time):
    """Ask the user to confirm the parameters before proceeding."""
    print("Please confirm if these are the correct parameters:")
    print(f"URL: {youtube_url}")
    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    response = input("Continue with these parameters? [y/N]: ")
    if response.strip().lower() != 'y':
        print("Operation aborted by the user.")
        exit(0)


def download_video(s3_url, local_path):
    # Ensure the local directory exists
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    # Send a GET request to the S3 URL
    response = requests.get(s3_url, stream=True)
    response.raise_for_status()  # Raises stored HTTPError, if one occurred

    # Stream the video content into the local file
    with open(local_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    
    print(f"Video downloaded successfully to {local_path}")
