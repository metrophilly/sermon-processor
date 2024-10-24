from datetime import datetime
import re


def is_valid_time(time_str):
    """Check if the time string is in a valid HH:MM:SS, MM:SS, or SS format."""
    # Regular expression to match valid time formats
    time_pattern = re.compile(r"^(\d{1,2}:)?([0-5]?\d:)?[0-5]?\d$")
    return bool(time_pattern.match(time_str)) if time_str else False


def get_formatted_time(time_input):
    return time_input if time_input else "00:00:00"


def get_formatted_date(input_date):
    # Parse the input date string
    date_obj = datetime.strptime(input_date, "%Y-%m-%d")

    # Format the date as "Sunday, October 29, 2023"
    formatted_date = date_obj.strftime("%A, %B %d, %Y")

    return formatted_date


def format_seconds_to_readable(seconds):
    """Converts a number of seconds to a formatted string showing hours, minutes, and seconds."""
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)} hours, {int(minutes)} minutes, {seconds:.2f} seconds"
