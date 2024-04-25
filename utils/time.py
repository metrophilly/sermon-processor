import re


def is_valid_time(time_str):
    """Check if the time string is in a valid HH:MM:SS, MM:SS, or SS format."""
    # Regular expression to match valid time formats
    time_pattern = re.compile(r'^(\d{1,2}:)?([0-5]?\d:)?[0-5]?\d$')
    return bool(time_pattern.match(time_str)) if time_str else False

def get_formatted_time(time_input):
    return time_input if time_input else "00:00:00"