import json
import pytest

from app.themes import pilot

PARAGRAPHS = [
    {"id": "p001", "start_ms": 0, "text": "Welcome to the Metro Church Podcast.", "raw": "Welcome to the Metro Church Podcast."},
    {"id": "p002", "start_ms": 65000, "text": "Money is the gospel -centered test.", "raw": "Money is the gospel -centered test."},
]


def result(**theme):
    base = {"label": "money", "why": "It is developed.", "confidence": "high",
            "evidence": [{"paragraph_id": "p002", "quote": "Money is the gospel -centered test."}]}
    base.update(theme)
    return {"themes": [base], "frames_not_themes": []}


def test_build_input_numbers_paragraphs_and_states_the_authored_passage():
    ctx = {"date": "2026-11-08", "speaker": "A B", "series": "S", "title": "T", "passage": "Genesis 13:1-18", "paragraphs": PARAGRAPHS}
    text = pilot.build_input(ctx)
    assert "Authored passage: Genesis 13:1-18" in text and "[p002] Money is" in text


def test_parse_output_tolerates_a_code_fence_and_rejects_non_json():
    assert pilot.parse_output('```json\n{"themes": []}\n```') == {"themes": []}
    with pytest.raises(pilot.ThemeError):
        pilot.parse_output("no json here")


def test_quote_check_keeps_a_real_quote_and_ignores_case_and_spacing():
    checked = pilot.check_result(result(evidence=[{"paragraph_id": "p002", "quote": "money  is the GOSPEL -centered"}]), PARAGRAPHS)
    assert len(checked["themes"]) == 1 and not checked["problems"]


def test_quote_check_drops_an_invented_quote_a_wrong_paragraph_and_bad_fields():
    for bad in (
        {"evidence": [{"paragraph_id": "p002", "quote": "Money is a sin."}]},
        {"evidence": [{"paragraph_id": "p001", "quote": "Money is the gospel -centered test."}]},
        {"evidence": [{"paragraph_id": "p999", "quote": "x"}]},
        {"evidence": []},
        {"confidence": "certain"},
    ):
        checked = pilot.check_result(result(**bad), PARAGRAPHS)
        assert checked["themes"] == [] and len(checked["dropped"]) == 1 and checked["problems"]


def test_no_themes_needs_a_reason():
    assert pilot.check_result({"themes": []}, PARAGRAPHS)["problems"]
    assert not pilot.check_result({"themes": [], "none_reason": "thin"}, PARAGRAPHS)["problems"]


def test_runners_share_one_interface_and_the_subagent_runner_is_manual():
    assert set(pilot.RUNNERS) == {"subagent", "api"}
    with pytest.raises(pilot.ThemeError):
        pilot.SubagentRunner().run("p", "i")
    assert "raw.json" in pilot.SubagentRunner.task_text("p.md", "i.md", "raw.json")


def test_v2_check_enforces_the_list_the_series_rule_and_proposals():
    allowed = ["money", "generosity", "identity", "ambition"]

    def theme(label):
        return {"label": label, "why": "w", "confidence": "high",
                "evidence": [{"paragraph_id": "p002", "quote": "Money is the gospel -centered test."}]}

    checked = pilot.check_result({"themes": [theme("money"), theme("generosity")]}, PARAGRAPHS, allowed=allowed,
                                 series_themes=["money", "generosity"], max_themes=4)
    assert any("no theme specific" in p for p in checked["problems"])
    checked = pilot.check_result({"themes": [theme("money"), theme("identity")]}, PARAGRAPHS, allowed=allowed,
                                 series_themes=["money", "generosity"])
    assert not checked["problems"]
    checked = pilot.check_result({"themes": [theme("worship")]}, PARAGRAPHS, allowed=allowed)
    assert checked["themes"] == [] and "not on the theme list" in checked["dropped"][0]["problems"]
    proposal = {"label": "wealth and power", "meaning": "m", "why_no_listed_theme_fits": "w",
                "evidence": [{"paragraph_id": "p002", "quote": "Money is the gospel -centered test."}]}
    checked = pilot.check_result({"themes": [theme("money")], "proposed_themes": [proposal, {**proposal, "label": "status"}]},
                                 PARAGRAPHS, allowed=allowed)
    assert [p["label"] for p in checked["proposed_themes"]] == ["status"] and len(checked["dropped_proposals"]) == 1


def test_v2_input_lists_the_approved_themes_and_the_series_hint():
    ctx = {"date": "d", "speaker": "s", "series": "A Culture of Giving", "title": "t", "passage": "p", "paragraphs": PARAGRAPHS}
    text = pilot.build_input(ctx, [{"slug": "money", "definition": "Wealth."}], {"A Culture of Giving": ["money", "generosity"]})
    assert "- money: Wealth." in text and "money, generosity" in text
    assert "Approved theme list" not in pilot.build_input(ctx)
