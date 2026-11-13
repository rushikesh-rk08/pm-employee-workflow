"""Tests that run without an API key or network access."""

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pm_employee as pm  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "mock_reply.json"
SAMPLE = ROOT / "feedback" / "2026-11-student-housing-sample.md"


def sample_feedback() -> tuple[str, str]:
    text = pm.strip_comments(SAMPLE.read_text(encoding="utf-8"))
    return pm.split_goal(text, "default goal")


def test_comments_are_not_sent_to_the_model():
    _, feedback = sample_feedback()
    assert "SAMPLE DATA" not in feedback
    assert "guarantor" in feedback


def test_goal_line_overrides_the_default():
    goal, feedback = sample_feedback()
    assert goal.startswith("Raise the share of students")
    assert not feedback.lower().startswith("goal:")


def test_default_goal_is_used_when_no_goal_line():
    goal, feedback = pm.split_goal("Just a comment.", "default goal")
    assert goal == "default goal"
    assert feedback == "Just a comment."


def test_reply_wrapped_in_extra_text_is_still_parsed():
    raw = "Here you go:\n```json\n" + FIXTURE.read_text(encoding="utf-8") + "\n```"
    data = pm.parse_reply(raw)
    assert len(data["risks"]) == 3


def test_reply_missing_a_section_is_rejected():
    with pytest.raises(ValueError, match="risks"):
        pm.parse_reply(json.dumps(
            {"insights": [], "user_stories": [], "stakeholder_email": {}}
        ))


def test_reply_without_json_is_rejected():
    with pytest.raises(ValueError):
        pm.parse_reply("Sorry, I cannot help with that.")


def test_real_quotes_pass_and_invented_quotes_are_flagged():
    _, feedback = sample_feedback()
    data = pm.parse_reply(FIXTURE.read_text(encoding="utf-8"))
    verified, total = pm.check_evidence(data, feedback)
    assert (verified, total) == (3, 4)
    flagged = [
        item["quote"]
        for insight in data["insights"]
        for item in insight["evidence"]
        if not item["verified"]
    ]
    assert flagged == ["The upload button is broken on every phone."]


def test_quote_check_ignores_case_spacing_and_curly_quotes():
    feedback = "She said: I didn’t   get the Email."
    assert pm.quote_is_in_feedback("i didn't get the email", feedback)
    assert not pm.quote_is_in_feedback("", feedback)


def test_report_has_all_four_sections_and_sorts_risks():
    goal, feedback = sample_feedback()
    data = pm.parse_reply(FIXTURE.read_text(encoding="utf-8"))
    verified, total = pm.check_evidence(data, feedback)
    report = pm.render_report(
        data, goal=goal, source="sample.md", model="test-model",
        verified=verified, total=total, today=dt.date(2026, 11, 13),
    )
    for heading in ("## 1. Insights", "## 2. User stories",
                    "## 3. Stakeholder email", "## 4. Risks"):
        assert heading in report
    assert "3 of 4 quotes" in report
    assert "not found in the feedback" in report
    assert report.index("| High |") < report.index("| Medium |") < report.index("| Low |")


def test_end_to_end_with_mock_reply(tmp_path, monkeypatch):
    feedback_dir = tmp_path / "feedback"
    feedback_dir.mkdir()
    (feedback_dir / "batch.md").write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(pm, "ROOT", tmp_path)
    monkeypatch.setattr(pm, "FEEDBACK_DIR", feedback_dir)
    monkeypatch.setattr(pm, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(pm, "GOAL_FILE", tmp_path / "goal.md")
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    assert pm.main(["--mock", str(FIXTURE)]) == 0
    report = (tmp_path / "reports" / "batch.md").read_text(encoding="utf-8")
    assert "# Sprint brief: batch.md" in report

    # A second run finds nothing new and leaves the brief alone.
    assert pm.pending_feedback(redo_all=False) == []
    assert pm.pending_feedback(redo_all=True) == [feedback_dir / "batch.md"]


def test_no_ai_access_stops_with_a_clear_message(monkeypatch, capsys):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    assert pm.main([]) == 2
    assert "GITHUB_TOKEN" in capsys.readouterr().err


def test_provider_choice(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    assert pm.choose_provider() == "github"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    assert pm.choose_provider() == "claude"


def test_falls_back_to_the_next_free_model(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("PM_EMPLOYEE_MODEL", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    tried = []

    def fake_call(goal, feedback, model):
        tried.append(model)
        if len(tried) == 1:
            raise RuntimeError("unknown model")
        return "{}"

    monkeypatch.setattr(pm, "call_github_models", fake_call)
    raw, model = pm.call_model("goal", "feedback")
    assert raw == "{}"
    assert tried == pm.GITHUB_DEFAULT_MODELS[:2]
    assert model == f"{pm.GITHUB_DEFAULT_MODELS[1]} (GitHub Models)"


def test_github_models_request_shape(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    seen = {}

    def fake_post(url, body, token):
        seen.update(url=url, body=json.loads(body), token=token)
        return 200, "application/json", json.dumps(
            {"choices": [{"message": {"content": "hello"}}]})

    monkeypatch.setattr(pm, "_post_json", fake_post)
    assert pm.call_github_models("goal", "feedback text", "some/model") == "hello"
    assert seen["url"] == pm.GITHUB_MODELS_URL
    assert seen["token"] == "secret-token"
    assert seen["body"]["model"] == "some/model"
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]
    assert "feedback text" in seen["body"]["messages"][1]["content"]


def test_non_json_answer_is_reported_not_crashed(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setattr(pm, "_post_json", lambda *a: (200, "text/plain", "OK"))
    with pytest.raises(RuntimeError, match="unexpected answer"):
        pm.call_github_models("goal", "feedback", "some/model")


def test_error_status_is_reported(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setattr(pm, "_post_json", lambda *a: (404, "application/json", "no such model"))
    with pytest.raises(RuntimeError, match="404"):
        pm.call_github_models("goal", "feedback", "some/model")
