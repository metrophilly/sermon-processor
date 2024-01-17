import re
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def is_valid_time(time_str):
    """Check if the time string is in a valid HH:MM:SS, MM:SS, or SS format."""
    # Regular expression to match valid time formats
    time_pattern = re.compile(r'^(\d{1,2}:)?([0-5]?\d:)?[0-5]?\d$')
    return bool(time_pattern.match(time_str)) if time_str else False


def is_valid_audio_file(file_path):
    return os.path.exists(file_path) and os.path.getsize(file_path) > 1000


def is_audacity_installed():
    try:
        result = subprocess.run(
            ["mdfind", "kMDItemCFBundleIdentifier == 'org.audacityteam.audacity'"], stdout=subprocess.PIPE)
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        return False