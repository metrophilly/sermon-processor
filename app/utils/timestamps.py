import re

_DIGITS = re.compile(r"^\d+$")
_SECONDS_ALONE = re.compile(r"^\d+(\.\d+)?$")
_SECONDS_AFTER_COLON = re.compile(r"^[0-5]\d(\.\d+)?$")


def parse_timestamp(value):
    """
    Converts a human-typed time to seconds.

    Accepts plain seconds ("2620", "2620.5"), MM:SS ("43:40") and H:MM:SS
    ("1:17:24" or "01:17:24"). Seconds after a colon must be two digits and
    under 60, and minutes under 60 when hours are present, so typos like "1:2"
    or "00:61:00" are rejected instead of guessed at.
    """
    text = str(value).strip()
    parts = text.split(":")
    invalid = ValueError(
        f"Invalid time '{value}'. Use seconds (2620), MM:SS (43:40) or H:MM:SS (1:17:24)."
    )

    if not 1 <= len(parts) <= 3 or any(p == "" for p in parts):
        raise invalid

    *leading, last = parts
    if any(not _DIGITS.match(p) for p in leading):
        raise invalid
    if leading and not _SECONDS_AFTER_COLON.match(last):
        raise invalid
    if not leading and not _SECONDS_ALONE.match(last):
        raise invalid
    if len(parts) == 3 and int(parts[1]) >= 60:
        raise invalid

    total = float(last)
    if len(parts) == 3:
        total += int(parts[0]) * 3600 + int(parts[1]) * 60
    elif len(parts) == 2:
        total += int(parts[0]) * 60
    return total


def format_timestamp(seconds):
    """Formats seconds as H:MM:SS, with one decimal only when it matters."""
    seconds = max(0.0, float(seconds))
    tenths = round(seconds * 10)
    whole, frac = divmod(tenths, 10)
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    text = f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{text}.{frac}" if frac else text
