"""
Spoken passage announcements in a transcript (DT-261 audit).

Sermons open with the reader naming the passage: "Today's scripture reading comes from
Genesis chapter 13, verses 1 to 18." This module finds those references in the opening and
turns them into ranges, so an AUDIT can compare them with the authored passage on the sermon.

Boundary: the result is a report for a person. It is never stored as the sermon's passage,
never as an exposition, and never used to fill a missing passage. Spoken references are
unreliable (speech to text damages them), which is why a person reads every mismatch.
"""

import re

from app.scripture.refs import BOOK_PATTERN, Range, SINGLE_CHAPTER, book_number, overlaps, ref

OPENING_PARAGRAPHS = 4
OPENING_CHARS = 2500

_NUMBER = r"\d{1,3}"
_FIND = re.compile(
    rf"\b(?P<book>{BOOK_PATTERN})[\s,]+(?:chapter\s+)?(?P<ch>{_NUMBER})\b(?P<colon>\s*:\s*(?P<cv1>{_NUMBER})(?:\s*-\s*(?P<cv2>{_NUMBER})(?:\s*:\s*(?P<cv3>{_NUMBER}))?)?)?",
    re.I,
)
_VERSES = (
    rf"(?:verses?|vs\.?)\s*(?P<v1>{_NUMBER})"
    rf"(?:[\s,]*(?:to|through|thru|until|-|and)\s*(?:(?:chapter\s*)?(?P<c2>{_NUMBER})\s*[,:]?\s*verses?\s*)?(?P<v2>{_NUMBER}))?"
)
_CHAPTER_TO = re.compile(
    rf"^[\s,.]*(?:to|through|thru|until)\s*chapter\s*(?P<c2>{_NUMBER})\s*[,:]?\s*verses?\s*(?P<v2>{_NUMBER})", re.I
)
_VERSES_NEXT = re.compile(rf"^[\s,.]*{_VERSES}", re.I)
_VERSES_NEAR = re.compile(_VERSES, re.I)
LOOKAHEAD = 160
_BOOK_ONLY = re.compile(rf"\b(?P<book>{BOOK_PATTERN})\b", re.I)
_CHAPTERS = re.compile(rf"chapters?\s+(?P<a>{_NUMBER})(?:\s*(?:and|through|thru|to|-)\s*(?P<b>{_NUMBER}))?", re.I)
_CHAPTERS_WINDOW = 110


def opening_text(paragraphs):
    """(paragraph, offset) pieces of the first few paragraphs, up to OPENING_CHARS."""
    pieces, used = [], 0
    for paragraph in paragraphs[:OPENING_PARAGRAPHS]:
        if used >= OPENING_CHARS:
            break
        pieces.append(paragraph)
        used += len(paragraph["text"])
    return pieces


def find_spoken(paragraphs):
    """Spoken references in the opening: list of dicts with range, text, paragraph, kind, excerpt."""
    found, seen = [], set()
    for paragraph in opening_text(paragraphs):
        text = paragraph["text"]
        spans = []
        for match in _FIND.finditer(text):
            book = book_number(match.group("book"))
            if not book:
                continue
            spans.append(match.span())
            chapter = int(match.group("ch"))
            end, kind = match.end(), "chapter"
            if match.group("colon"):
                low = int(match.group("cv1"))
                if match.group("cv3"):  # 2:12-3:10
                    r = Range(ref(book, chapter, low), ref(book, int(match.group("cv2")), int(match.group("cv3"))))
                else:
                    r = Range(ref(book, chapter, low), ref(book, chapter, int(match.group("cv2") or low)))
                kind = "colon"
            else:
                chapter_to = _CHAPTER_TO.match(text[end:])  # "chapter 10 to chapter 11, verse 9"
                if chapter_to:
                    r = Range(ref(book, chapter, 1), ref(book, int(chapter_to.group("c2")), int(chapter_to.group("v2"))))
                    if r not in seen:
                        seen.add(r)
                        found.append({"range": r, "text": match.group(0), "paragraph_id": paragraph["id"],
                                      "start_ms": paragraph["start_ms"], "kind": "chapter-to",
                                      "excerpt": text[max(0, match.start() - 60) : min(len(text), end + 120)]})
                    continue
                tail = _VERSES_NEXT.match(text[end:])
                if not tail:  # "Matthew chapter 16. Matthew chapter 16, I'm going to read from verses 13 to 26."
                    tail = _VERSES_NEAR.search(text[end : end + LOOKAHEAD])
                    kind = "verses-nearby" if tail else "chapter"
                else:
                    kind = "verses"
                if tail:
                    v1 = int(tail.group("v1"))
                    c2 = int(tail.group("c2") or chapter)
                    v2 = int(tail.group("v2") or v1)
                    r = Range(ref(book, chapter, v1), ref(book, c2, v2))
                elif book in SINGLE_CHAPTER:
                    r = Range(ref(book, 1, chapter), ref(book, 1, chapter))
                else:
                    r = Range(ref(book, chapter, 1), ref(book, chapter, 999))
            if r in seen:
                continue
            seen.add(r)
            start = max(0, match.start() - 60)
            found.append({"range": r, "text": match.group(0), "paragraph_id": paragraph["id"],
                          "start_ms": paragraph["start_ms"], "kind": kind,
                          "excerpt": text[start : min(len(text), end + 120)]})
        # "the book of Exodus. I'll be reading excerpts from chapters 1 and 2."
        for match in _BOOK_ONLY.finditer(text):
            book = book_number(match.group("book"))
            if not book or any(a <= match.start() < b for a, b in spans):
                continue
            after = text[match.end() : match.end() + _CHAPTERS_WINDOW]
            window = _CHAPTERS.search(after)
            if not window:
                continue
            first = int(window.group("a"))
            if window.group("b"):
                r = Range(ref(book, first, 1), ref(book, int(window.group("b")), 999))
            else:
                tail = _VERSES_NEXT.match(after[window.end() :])
                if tail:  # "the gospel according to Luke. I'll be reading from chapter 15, verses 11 to 32."
                    v1 = int(tail.group("v1"))
                    r = Range(ref(book, first, v1), ref(book, int(tail.group("c2") or first), int(tail.group("v2") or v1)))
                else:
                    r = Range(ref(book, first, 1), ref(book, first, 999))
            if r not in seen:
                seen.add(r)
                found.append({"range": r, "text": match.group(0) + " ... " + window.group(0), "paragraph_id": paragraph["id"],
                              "start_ms": paragraph["start_ms"], "kind": "chapters",
                              "excerpt": text[max(0, match.start() - 60) : match.end() + _CHAPTERS_WINDOW]})
    return found


CLASSES = ["different passage", "same book", "no reading found", "overlap", "start only", "chapter only", "partial", "exact"]


def _is_whole_chapters(r):
    return r.start % 1_000 == 1 and r.end % 1_000 == 999


def classify(authored, found):
    """How the spoken announcement compares with the authored passage. Reports only.

    `found` is the list from `find_spoken`. 'chapter only' means the reader named just the chapter
    and the authored passage lies inside it. That agrees, so it is not flagged.
    """
    if not found:
        return "no reading found"
    spoken = {f["range"] for f in found}
    matched = [a for a in authored if a in spoken]
    if len(matched) == len(authored):
        return "exact"
    if matched:
        return "partial"
    first = authored[0]
    if first.end > first.start and any(f["range"].start == f["range"].end == first.start for f in found):
        return "start only"  # "I'll be reading from verse 1": names where it starts, not where it ends
    touching = [f for f in found if any(overlaps(a, f["range"]) for a in authored)]
    if touching:
        if all(_is_whole_chapters(f["range"]) and any(f["range"].start <= a.start and a.end <= f["range"].end for a in authored)
               for f in touching):
            return "chapter only"
        return "overlap"
    books = {a.start // 1_000_000 for a in authored}
    if any(f["range"].start // 1_000_000 in books for f in found):
        return "same book"
    return "different passage"
