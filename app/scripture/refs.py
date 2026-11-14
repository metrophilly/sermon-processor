"""
Scripture references as numbers (DT-261).

A reference is stored as book x 1,000,000 + chapter x 1,000 + verse, so ranges compare and sort
as plain integers. A range has a start and an end. Whole chapters end at verse 999.

`parse_authored` turns the authored `passage` string on a Sanity sermon into ranges. That is
transcription, and it is allowed. Nothing here reads a passage out of prose and stores it.
The spoken reader in `spoken.py` shares the book names and the number scheme, and only ever
feeds an audit report for a person to read.
"""

import re
from collections import namedtuple

Range = namedtuple("Range", "start end")


class RefError(ValueError):
    pass


BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua", "Judges", "Ruth",
    "1 Samuel", "2 Samuel", "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah",
    "Esther", "Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs", "Isaiah", "Jeremiah",
    "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum",
    "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
]
SINGLE_CHAPTER = {31, 57, 63, 64, 65}  # Obadiah, Philemon, 2 John, 3 John, Jude

_EXTRA = {
    "psalm": "Psalms", "song of solomon": "Song of Songs", "songs": "Song of Songs",
    "song of songs": "Song of Songs", "revelations": "Revelation", "ecclesiastes": "Ecclesiastes",
    "acts of the apostles": "Acts",
}
_ORDINAL = {"first": "1", "1st": "1", "i": "1", "second": "2", "2nd": "2", "ii": "2",
            "third": "3", "3rd": "3", "iii": "3"}


def _alias_map():
    aliases = {}
    for number, name in enumerate(BOOKS, 1):
        aliases[name.lower()] = number
    for alias, name in _EXTRA.items():
        aliases[alias] = BOOKS.index(name) + 1
    return aliases


ALIASES = _alias_map()
# Names without the number, for the spoken reader's pattern: "samuel", "john", "song of songs".
BASE_NAMES = sorted({re.sub(r"^[123] ", "", name.lower()) for name in BOOKS} | set(_EXTRA), key=len, reverse=True)
BOOK_PATTERN = r"(?:(?:[123]|first|second|third|1st|2nd|3rd|I{1,3})\s+)?(?:" + "|".join(re.escape(n) for n in BASE_NAMES) + r")"


def book_number(text):
    """'first Samuel', '1 Sam', 'Psalm' -> book number, or None."""
    words = re.sub(r"\s+", " ", text.strip().lower().rstrip(".")).split(" ")
    if len(words) > 1 and words[0] in _ORDINAL | {"1": "1", "2": "2", "3": "3"}:
        words[0] = {**_ORDINAL, "1": "1", "2": "2", "3": "3"}[words[0]]
    return ALIASES.get(" ".join(words))


def ref(book, chapter, verse):
    return book * 1_000_000 + chapter * 1_000 + verse


def book_of(value):
    return value // 1_000_000


def format_ref(value):
    return f"{BOOKS[book_of(value) - 1]} {value // 1_000 % 1_000}:{value % 1_000}"


def format_range(r):
    """'Genesis 1:1-2:3'. Whole chapters read 'John 13'."""
    book, c1, v1 = book_of(r.start), r.start // 1_000 % 1_000, r.start % 1_000
    c2, v2 = r.end // 1_000 % 1_000, r.end % 1_000
    name = BOOKS[book - 1]
    if v1 == 1 and v2 == 999:
        return f"{name} {c1}" if c1 == c2 else f"{name} {c1}-{c2}"
    if c1 == c2:
        return f"{name} {c1}:{v1}" if v1 == v2 else f"{name} {c1}:{v1}-{v2}"
    return f"{name} {c1}:{v1}-{c2}:{v2}"


def overlaps(a, b):
    return a.start <= b.end and b.start <= a.end


_BOOK_AT_START = re.compile(r"^((?:[123]\s+)?[A-Za-z]+(?:\s+(?:of\s+)?[A-Za-z]+)*)\s+(?=\d)")


def parse_authored(text):
    """Authored passage string -> list of Range. Raises RefError when it cannot be read.

    Handles: 'John 6:1-15, 25-35', 'Exodus 5:2; 12:12-13, 21-23', '1 Thessalonians 2:17-3:10',
    'Genesis 1:1-2, 26-2:3', 'Exodus 19:1-8, 20:1-3, 24:3-8', 'Luke 1:1-4 and 2:41-52',
    'Luke 10: 38-42', '1 Samuel 4-5', 'John 13', 'Psalm 115:4-8; 1 Corinthians 6:12-20',
    'Luke 24:49-53, Acts 1:1-11' (a new book after a comma), 'Esther 6:1-12 (3:1-6)' (a bracket).
    """
    if not text or not text.strip():
        raise RefError("empty passage")
    s = text.strip().replace("–", "-").replace("—", "-")
    s = re.sub(r":\s+", ":", s)
    s = re.sub(r"\s+and\s+(?=\d)", "; ", s)
    s = re.sub(r"\s*\(([^)]*)\)", r"; \1", s)  # 'Esther 6:1-12 (3:1-6)': the bracket is a second reference
    ranges, book, chapter = [], None, None
    for segment in (seg.strip() for seg in s.split(";") if seg.strip()):
        match = _BOOK_AT_START.match(segment)
        rest = segment
        if match:
            number = book_number(match.group(1))
            if number is None:
                raise RefError(f"unknown book {match.group(1)!r} in {text!r}")
            book, chapter, rest = number, (1 if number in SINGLE_CHAPTER else None), segment[match.end():]
        if book is None:
            raise RefError(f"no book in {text!r}")
        for item in (i.strip() for i in rest.split(",") if i.strip()):
            named = _BOOK_AT_START.match(item)  # 'Luke 24:49-53, Acts 1:1-11': a new book after a comma
            if named and book_number(named.group(1)):
                book, chapter, item = book_number(named.group(1)), (1 if book_number(named.group(1)) in SINGLE_CHAPTER else None), item[named.end():]
            r, chapter = _parse_item(item, book, chapter, text)
            ranges.append(r)
    if not ranges:
        raise RefError(f"no reference in {text!r}")
    return ranges


def _parse_item(item, book, chapter, source):
    try:
        colons = item.count(":")
        if colons == 0:
            parts = [int(x) for x in item.split("-")]
            if len(parts) > 2:
                raise ValueError
            if chapter is None:  # whole chapters
                return Range(ref(book, parts[0], 1), ref(book, parts[-1], 999)), None
            return Range(ref(book, chapter, parts[0]), ref(book, chapter, parts[-1])), chapter
        if colons == 1:
            if "-" in item and item.index("-") < item.index(":"):  # '26-2:3': verse 26 to chapter 2 verse 3
                first, rest = item.split("-", 1)
                end_chapter, end_verse = (int(x) for x in rest.split(":"))
                if chapter is None:
                    raise ValueError
                return Range(ref(book, chapter, int(first)), ref(book, end_chapter, end_verse)), end_chapter
            chap, verses = item.split(":")
            low, dash, high = verses.partition("-")
            if dash and not high:
                raise ValueError
            chapter = int(chap)
            return Range(ref(book, chapter, int(low)), ref(book, chapter, int(high or low))), chapter
        first, second = item.split("-", 1)
        c1, v1 = (int(x) for x in first.split(":"))
        c2, v2 = (int(x) for x in second.split(":"))
        return Range(ref(book, c1, v1), ref(book, c2, v2)), c2
    except ValueError:
        raise RefError(f"cannot read {item!r} in {source!r}") from None
