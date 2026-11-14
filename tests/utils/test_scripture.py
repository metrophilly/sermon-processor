import pytest

from app.scripture import refs, spoken


def fmt(text):
    return [refs.format_range(r) for r in refs.parse_authored(text)]


@pytest.mark.parametrize("text,expected", [
    ("Exodus 3:1-15", ["Exodus 3:1-15"]),
    ("1 Peter 2:4-10", ["1 Peter 2:4-10"]),
    ("Matthew 13:1-9, 18-23", ["Matthew 13:1-9", "Matthew 13:18-23"]),
    ("Exodus 5:2; 7:14-18; 9:15-16; 10:21-23", ["Exodus 5:2", "Exodus 7:14-18", "Exodus 9:15-16", "Exodus 10:21-23"]),
    ("Genesis 10:32-11:9", ["Genesis 10:32-11:9"]),
    ("Exodus 1:8-10, 12-17, 22; 2:1-7, 10-15", ["Exodus 1:8-10", "Exodus 1:12-17", "Exodus 1:22", "Exodus 2:1-7", "Exodus 2:10-15"]),
    # a comma element that crosses a chapter: verse 26 of chapter 1 to chapter 2 verse 3
    ("Genesis 1:1-2, 26-2:3", ["Genesis 1:1-2", "Genesis 1:26-2:3"]),
    # a comma list that changes chapter with no semicolon
    ("Exodus 19:1-8, 20:1-3, 24:3-8", ["Exodus 19:1-8", "Exodus 20:1-3", "Exodus 24:3-8"]),
    ("Luke 1:1-4 and 2:41-52", ["Luke 1:1-4", "Luke 2:41-52"]),
    ("Luke 10: 38-42", ["Luke 10:38-42"]),
    ("1 Samuel 4-5", ["1 Samuel 4-5"]),
    ("John 13", ["John 13"]),
    ("Psalm 115:4-8; 1 Corinthians 6:12-20", ["Psalms 115:4-8", "1 Corinthians 6:12-20"]),
    ("Luke 24:49-53, Acts 1:1-11", ["Luke 24:49-53", "Acts 1:1-11"]),
    ("Esther 6:1-12 (3:1-6)", ["Esther 6:1-12", "Esther 3:1-6"]),
    ("Jude 3-5", ["Jude 1:3-5"]),
    ("2 Samuel 11:1-12:13", ["2 Samuel 11:1-12:13"]),
])
def test_authored_passages_parse(text, expected):
    assert fmt(text) == expected


def test_authored_numbers_are_book_chapter_verse_integers_and_a_chapter_spans_to_999():
    assert refs.parse_authored("John 3:16")[0] == refs.Range(43_003_016, 43_003_016)
    assert refs.parse_authored("John 13")[0] == refs.Range(43_013_001, 43_013_999)


@pytest.mark.parametrize("bad", ["", "Number 21:1-9", "Genesis", "Foo 1:1", "John 3:16-"])
def test_unreadable_passages_raise(bad):
    with pytest.raises(refs.RefError):
        refs.parse_authored(bad)


def test_book_names_and_spoken_ordinals():
    assert refs.book_number("first Samuel") == refs.book_number("1 Samuel") == 9
    assert refs.book_number("Psalm") == refs.book_number("Psalms") == 19
    assert refs.book_number("Second Corinthians") == 47 and refs.book_number("Nonsense") is None


def para(text, n=1):
    return [{"id": f"p{n:03d}", "start_ms": 0, "text": text}]


@pytest.mark.parametrize("text,expected", [
    ("Today's scripture reading comes from Philippians chapter 4, verses 4 through 12. Rejoice.", "Philippians 4:4-12"),
    ("This is the passage preached today, Genesis chapter 11, verse 27, through chapter 12, verse 9.", "Genesis 11:27-12:9"),
    ("It comes from the book of Judges, chapter 3, verses 7 to 30.", "Judges 3:7-30"),
    ("the passage will be coming from Matthew chapter 16. Matthew chapter 16, I'm going to read from verses 13 to 26.", "Matthew 16:13-26"),
    ("The reading comes from the gospel according to Luke. And I'll be reading from chapter 15, verses 11 to 32.", "Luke 15:11-32"),
    ("Our reading is from the book of Exodus. I'll be reading excerpts from chapters 1 and 2.", "Exodus 1-2"),
    ("Read along in 1 Thessalonians 2:12-3:10 this morning", "1 Thessalonians 2:12-3:10"),
    ("We turn to Genesis 13:1-18 today.", "Genesis 13:1-18"),
])
def test_spoken_announcements_are_found(text, expected):
    found = spoken.find_spoken(para(text))
    assert expected in [refs.format_range(f["range"]) for f in found]


def test_spoken_reader_only_looks_at_the_opening():
    paragraphs = [{"id": f"p{i:03d}", "start_ms": 0, "text": "words " * 5} for i in range(1, 7)]
    paragraphs[5]["text"] = "Later we turn to Romans chapter 8, verses 1 to 4."
    assert spoken.find_spoken(paragraphs) == []


def classify(authored_text, spoken_text):
    return spoken.classify(refs.parse_authored(authored_text), spoken.find_spoken(para(spoken_text)))


def test_classification_of_how_audio_and_record_compare():
    assert classify("Genesis 13:1-18", "reading from Genesis chapter 13, verses 1 to 18") == "exact"
    assert classify("Isaiah 9:1-7", "Isaiah chapter 9 is the most famous passage") == "chapter only"
    assert classify("John 14:1-14", "from John chapter 14, and I'll be reading from verse 1") == "start only"
    assert classify("Genesis 13:1-17", "Genesis chapter 13, verses 1 to 18") == "overlap"
    assert classify("Luke 1:26-38", "Matthew chapter 1, verses 1 to 17") == "different passage"
    assert classify("Genesis 9:1-9", "Genesis chapter 11, verses 1 to 9") == "same book"
    assert classify("Genesis 9:1-9", "Welcome to the podcast.") == "no reading found"


@pytest.mark.parametrize("text,expected", [
    ("comes from 1 Thessalonians 2, verse 12 to 3, verse 10. you can", "1 Thessalonians 2:12-3:10"),
    ("comes from Genesis chapter 10 to chapter 11, verse 9. You can", "Genesis 10:1-11:9"),
])
def test_spoken_ranges_that_cross_chapters_without_the_word_chapter(text, expected):
    assert expected in [refs.format_range(f["range"]) for f in spoken.find_spoken(para(text))]
