from app.archive.manifest import classify, report, s3_key

LEADER = {"firstName": "Donny", "lastName": "Cho", "isMetroLeadership": True}
GUEST = {"firstName": "Guest", "lastName": "Speaker", "isMetroLeadership": False}


def doc(sermon_id="a", date="2022-06-26T15:30:00Z", s3="/2022/2022-06-26.mp3", speaker=LEADER, published=True):
    return {
        "_id": sermon_id, "title": "T", "slug": "t", "isPublished": published, "spokenDate": date,
        "passage": "John 1", "speaker": speaker, "series": "S", "s3": s3, "yt": None,
    }


def run(docs, files):
    return classify(docs, lambda key: key in files)


def test_ok_sermon_with_encoded_path():
    rows, _ = run([doc(s3="/2012/2012-08/1-01%20Repent.mp3", date="2012-08-05T15:30:00Z")], {"2012/2012-08/1-01 Repent.mp3"})
    assert rows[0]["status"] == "ready"
    assert rows[0]["s3_key"] == "2012/2012-08/1-01 Repent.mp3"


def test_drafts_unpublished_and_guests_are_excluded():
    rows, excluded = run(
        [doc("drafts.a"), doc("b", published=False), doc("c", speaker=GUEST), doc("d")],
        {"2022/2022-06-26.mp3"},
    )
    assert [r["sermon_id"] for r in rows] == ["d"]
    assert excluded["draft_document"] == 1 and excluded["unpublished"] == 1 and excluded["guest_speaker"] == 1


def test_missing_path_and_missing_date_are_reported():
    rows, _ = run([doc("a", s3=None), doc("b", date=None)], {"2022/2022-06-26.mp3"})
    by_id = {r["sermon_id"]: r for r in rows}
    assert "missing_audio_path" in by_id["a"]["problems"]
    assert "missing_date" in by_id["b"]["problems"]


def test_wrong_folder_is_a_proposed_fix_not_silently_used():
    rows, _ = run([doc(s3="/2020/2020-07-05/x.mp3", date="2020-07-05T15:30:00Z")], {"2020/2020-07-05.mp3"})
    row = rows[0]
    assert row["problems"] == ["path_not_found_fixable"]
    assert row["proposed_path"] == "/2020/2020-07-05.mp3"
    assert row["audio_exists"] is False and row["status"] == "problem"


def test_file_not_found_anywhere():
    rows, _ = run([doc()], set())
    assert rows[0]["problems"] == ["file_not_found"]


def test_two_sermons_sharing_one_file_and_swapped_dates():
    rows, _ = run(
        [doc("a", date="2020-10-04T15:30:00Z", s3="/2020/2020-10-11.mp3"), doc("b", date="2020-10-11T15:30:00Z", s3="/2020/2020-10-11.mp3")],
        {"2020/2020-10-11.mp3"},
    )
    assert all("shared_audio_file" in r["warnings"] for r in rows)
    assert "date_mismatch" in rows[0]["warnings"] and "date_mismatch" not in rows[1]["warnings"]
    assert all(r["status"] == "ready" for r in rows)


def test_two_sermons_on_one_date_are_flagged():
    rows, _ = run([doc("a", s3="/a.mp3"), doc("b", s3="/b.mp3")], {"a.mp3", "b.mp3"})
    assert all("same_date_as_other_sermon" in r["warnings"] for r in rows)


def test_report_counts_by_year():
    rows, excluded = run([doc()], {"2022/2022-06-26.mp3"})
    text = report(rows, excluded)
    assert "2022: 1 / 1" in text and "Eligible sermons" in text


def test_s3_key_decodes_and_strips_slash():
    assert s3_key("/a%20b/c.mp3") == "a b/c.mp3" and s3_key(None) == ""
