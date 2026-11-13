from app.archive import db_search


def test_timestamp_formats_hours_minutes_seconds():
    assert db_search.timestamp(0) == "0:00:00"
    assert db_search.timestamp(765_000) == "0:12:45"
    assert db_search.timestamp(3_725_000) == "1:02:05"


def test_search_sql_only_adds_the_published_filter_when_asked():
    assert 'isPublished' not in db_search.search_sql(False)
    assert 'AND s."isPublished"' in db_search.search_sql(True)


def test_search_sql_uses_the_indexed_expression_and_never_pastes_the_text():
    sql = db_search.search_sql(False)
    assert "to_tsvector('english', p.\"textEdited\") @@ q.tsq" in sql
    assert ":'q'" in sql and "{" not in sql


def test_parse_rows_and_format_rows():
    line = "\t".join(["0.091", "2026-11-08", "Money as an Idol", "Donny Cho", "abc", "p013", "765000", "26", "a [[b]] c"])
    rows = db_search.parse_rows(line + "\nnot a result row\n")
    assert len(rows) == 1 and rows[0]["start_ms"] == 765000 and rows[0]["total"] == 26
    text = "\n".join(db_search.format_rows(rows))
    assert "26 matching paragraphs" in text and "abc p013 at 0:12:45" in text and "a [[b]] c" in text
    assert db_search.format_rows([]) == ["No matches."]
