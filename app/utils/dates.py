import datetime


def last_sunday(today=None):
    """
    Returns the most recent Sunday as YYYY-MM-DD. If `today` is a Sunday it is
    returned as-is, so running the script on a Sunday uses that same day.
    """
    today = today or datetime.date.today()
    # Monday == 0 ... Sunday == 6, so days since Sunday is (weekday + 1) % 7.
    days_back = (today.weekday() + 1) % 7
    return (today - datetime.timedelta(days=days_back)).isoformat()


def validate_date(value):
    """Returns `value` if it is a real YYYY-MM-DD date, else raises ValueError."""
    try:
        datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(f"Invalid date '{value}'. Use YYYY-MM-DD, e.g. 2026-11-01.")
    return value
