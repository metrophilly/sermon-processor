import codecs

from app.themes import demand


def themes():
    return [
        {"slug": "money", "group": "Money", "search_term": "money"},
        {"slug": "identity", "group": "Heart and self", "search_term": "identity", "extra_phrases": ["identity in christ"]},
    ]


def test_build_phrases_uses_templates_and_extra_phrases_without_duplicates():
    rows = demand.build_phrases(themes())
    phrases = [r["phrase"] for r in rows]
    assert "bible verses about money" in phrases and "identity in christ" in phrases
    assert len(phrases) == len(set(phrases)) == 9


def test_shipped_theme_list_loads_and_every_theme_has_a_group_and_term():
    loaded = demand.load_themes()
    assert len(loaded) >= 20 and all(t["group"] and t["search_term"] for t in loaded)
    assert len({t["slug"] for t in loaded}) == len(loaded)


def test_parse_volume_handles_ranges_exact_numbers_and_blanks():
    assert demand.parse_volume("10K - 100K") == (10_000, 100_000)
    assert demand.parse_volume("100 – 1K") == (100, 1_000)
    assert demand.parse_volume("1M - 10M") == (1_000_000, 10_000_000)
    assert demand.parse_volume("1,200") == (1200, 1200)
    assert demand.parse_volume("0") == (0, 0)
    assert demand.parse_volume("") is None and demand.parse_volume("n/a") is None


def test_read_planner_handles_utf16_tab_files_with_title_lines(tmp_path):
    text = "Keyword Stats 2026-11-14\nJan 2025 - Oct 2026\nKeyword\tCurrency\tAvg. monthly searches\tCompetition\nbible verses about money\tUSD\t10K – 100K\tLow\nsermon on money\tUSD\t100 – 1K\tLow\n"
    path = tmp_path / "planner.csv"
    path.write_bytes(codecs.BOM_UTF16_LE + text.encode("utf-16-le"))
    assert demand.read_planner(str(path)) == {"bible verses about money": (10_000, 100_000), "sermon on money": (100, 1_000)}


def test_join_flags_candidates_tag_only_and_no_data_and_adds_metro_numbers():
    rows = demand.build_phrases(themes())
    planner = {"bible verses about money": (10_000, 100_000), "sermon on identity": (10, 100)}
    gsc = {"sermon on money": (2, 50, 8.0)}
    summary = {s["theme"]: s for s in demand.join(rows, planner, gsc, threshold=1000)}
    assert summary["money"]["verdict"] == "landing page candidate" and summary["money"]["metro_impressions"] == 50
    assert summary["identity"]["verdict"] == "tag only"
    assert demand.join(rows, {}, {})[0]["verdict"] == "no data"
