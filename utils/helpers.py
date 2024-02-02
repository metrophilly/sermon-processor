import re
import os

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
      intro, scripture passage & reading, and the sermon).
    3. Smooth out any rough transitions or "bumps" where clips are stitched
      together.
    4. Trim the pastor's final prayer at the end, while keeping Rhea's outro intact.
    5. Export the edited audio as an MP3 file named "yyyy-mm-dd.mp3".
    6. Send to the reviewer.

    Remember: Careful editing ensures a polished final product, and your attention to
    detail will enhance our listeners' experience. Thank you for your contribution!
    {RESET}""")