import pytest

from app.utils.timestamps import format_timestamp, parse_timestamp


@pytest.mark.parametrize(
    "value,seconds",
    [
        ("10", 10),
        ("2620", 2620),
        ("43:40", 2620),
        ("0:43:40", 2620),
        ("00:43:40", 2620),
        ("1:17:24", 4644),
        ("01:17:24", 4644),
        ("00:00:01.5", 1.5),
        ("0:05.5", 5.5),
        (" 43:40 ", 2620),
    ],
)
def test_parse_timestamp(value, seconds):
    assert parse_timestamp(value) == pytest.approx(seconds)


@pytest.mark.parametrize(
    "bad", ["", "abc", "1:2", "00:61:00", "1:60", "1:2:3:4", "-5", "1::2", ":30", "4:30:"]
)
def test_parse_timestamp_rejects_typos(bad):
    with pytest.raises(ValueError):
        parse_timestamp(bad)


@pytest.mark.parametrize(
    "seconds,text",
    [(0, "0:00:00"), (2620, "0:43:40"), (4644, "1:17:24"), (1.5, "0:00:01.5"), (3600, "1:00:00")],
)
def test_format_timestamp(seconds, text):
    assert format_timestamp(seconds) == text


def test_format_then_parse_round_trips():
    for seconds in (0, 59, 2620, 4644, 7322):
        assert parse_timestamp(format_timestamp(seconds)) == seconds
