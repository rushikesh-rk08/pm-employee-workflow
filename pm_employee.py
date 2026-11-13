"""PM Employee: turn raw customer feedback into a sprint brief.

Reads every file in feedback/, sends it to an AI model with the product goal,
and writes a Markdown brief to reports/ containing:

  1. Insights      - themes, each backed by quotes from the feedback
  2. User stories  - with acceptance criteria
  3. Stakeholder email - subject and body, ready to send
  4. Risks         - top three, with severity and mitigation

Every evidence quote is checked against the original feedback. A quote the
model did not copy word for word is flagged in the brief, not hidden.

The AI model is Google's Gemini on its free tier (GEMINI_API_KEY).
If an ANTHROPIC_API_KEY is set, Claude is used instead.

Run on GitHub: the workflow in .github/workflows/pm-employee.yml does this
               on every new feedback file and every Monday morning.
Run locally:   python pm_employee.py   (see the README for the key it needs)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FEEDBACK_DIR = ROOT / "feedback"
REPORTS_DIR = ROOT / "reports"
GOAL_FILE = ROOT / "goal.md"

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Tried in order until one answers; the list of free models changes over time.
GEMINI_DEFAULT_MODELS = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]
CLAUDE_DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 4000
FEEDBACK_SUFFIXES = {".md", ".txt"}
SEVERITIES = ("High", "Medium", "Low")

SYSTEM_PROMPT = """You are a product manager's assistant. You are given a \
product goal and a batch of raw customer feedback. Produce the working \
documents a product manager needs for the next sprint.

Rules:
- Use only what the feedback says. Do not invent customers, numbers or facts.
- Every evidence quote must be copied word for word from the feedback.
- Write user stories an engineer can pick up without a meeting.
- Keep the stakeholder email under 200 words.
- Give exactly three risks, ordered from most to least severe.

Reply with one JSON object and nothing else, in this shape:
{
  "insights": [
    {"theme": "...", "summary": "...", "evidence": ["exact quote", "..."]}
  ],
  "user_stories": [
    {"title": "...",
     "story": "As a ..., I want ..., so that ...",
     "acceptance_criteria": ["...", "..."]}
  ],
  "stakeholder_email": {"subject": "...", "body": "..."},
  "risks": [
    {"risk": "...", "severity": "High | Medium | Low", "mitigation": "..."}
  ]
}"""


# --------------------------------------------------------------------------
# Reading the inputs
# --------------------------------------------------------------------------

def strip_comments(text: str) -> str:
    """Remove HTML comments so notes to humans are not sent to the model."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def split_goal(text: str, default_goal: str) -> tuple[str, str]:
    """Return (goal, feedback). A first line 'Goal: ...' overrides goal.md."""
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("goal:"):
        goal = lines[0].split(":", 1)[1].strip()
        return goal or default_goal, "\n".join(lines[1:]).strip()
    return default_goal, text


def read_default_goal() -> str:
    if GOAL_FILE.exists():
        goal = strip_comments(GOAL_FILE.read_text(encoding="utf-8"))
        if goal:
            return goal
    return "Improve the product for the customers quoted below."


def pending_feedback(redo_all: bool) -> list[Path]:
    """Feedback files that do not yet have a report."""
    if not FEEDBACK_DIR.exists():
        return []
    files = sorted(
        p for p in FEEDBACK_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in FEEDBACK_SUFFIXES
    )
    if redo_all:
        return files
    return [p for p in files if not report_path(p).exists()]


def report_path(feedback_file: Path) -> Path:
    return REPORTS_DIR / f"{feedback_file.stem}.md"


# --------------------------------------------------------------------------
# Talking to the AI model
# --------------------------------------------------------------------------

def build_user_message(goal: str, feedback: str) -> str:
    return (
        f"Product goal:\n{goal}\n\n"
        f"Customer feedback:\n<feedback>\n{feedback}\n</feedback>"
    )


def choose_provider() -> str | None:
    """Claude if an Anthropic key is set, otherwise Gemini's free tier."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "claude"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return None


def _post_json(url: str, body: bytes, headers: dict) -> tuple[int, str]:
    """POST and return (status, text). Error statuses are returned, not raised."""
    request = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8", "replace")


def call_gemini(goal: str, feedback: str, model: str) -> str:
    """Ask one Gemini model through Google's API. Free tier, needs GEMINI_API_KEY."""
    body = json.dumps({
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": build_user_message(goal, feedback)}]}],
    }).encode("utf-8")
    headers = {
        "x-goog-api-key": os.environ["GEMINI_API_KEY"],
        "Content-Type": "application/json",
    }
    url = GEMINI_URL.format(model=model)

    for attempt in (1, 2):
        status, text = _post_json(url, body, headers)
        if status in (429, 500, 502, 503) and attempt == 1:
            time.sleep(30)  # rate limit or a brief outage: wait, try once more
            continue
        if status != 200:
            raise RuntimeError(f"Gemini returned {status} for {model}: {text[:300]}")
        try:
            parts = json.loads(text)["candidates"][0]["content"]["parts"]
            return "".join(part.get("text", "") for part in parts)
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as error:
            raise RuntimeError(
                f"Gemini gave an unexpected answer for {model}: {text[:300]!r}"
            ) from error
    raise RuntimeError(f"Gemini kept returning errors for {model}.")


def call_claude(goal: str, feedback: str, model: str) -> str:
    """Ask Claude through the Anthropic API. Needs ANTHROPIC_API_KEY."""
    import anthropic  # only needed on this path

    client = anthropic.Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(goal, feedback)}],
    )
    return "".join(b.text for b in message.content if b.type == "text")


def call_model(goal: str, feedback: str) -> tuple[str, str]:
    """Return (raw reply, name of the model that wrote it)."""
    chosen = os.environ.get("PM_EMPLOYEE_MODEL", "").strip()
    if choose_provider() == "claude":
        model = chosen or CLAUDE_DEFAULT_MODEL
        return call_claude(goal, feedback, model), model

    models = [chosen] if chosen else GEMINI_DEFAULT_MODELS
    last_error: Exception | None = None
    for model in models:
        try:
            return call_gemini(goal, feedback, model), model
        except RuntimeError as error:
            last_error = error
            print(f"{error}", file=sys.stderr)
    raise RuntimeError(f"No model answered. Last error: {last_error}")


def parse_reply(raw: str) -> dict:
    """Pull the JSON object out of the reply and check its shape."""
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("The model's reply did not contain a JSON object.")
    data = json.loads(raw[start:end + 1])

    for key in ("insights", "user_stories", "stakeholder_email", "risks"):
        if key not in data:
            raise ValueError(f"The model's reply is missing '{key}'.")
    if not isinstance(data["stakeholder_email"], dict):
        raise ValueError("'stakeholder_email' should be an object.")
    for key in ("insights", "user_stories", "risks"):
        if not isinstance(data[key], list):
            raise ValueError(f"'{key}' should be a list.")
    return data


# --------------------------------------------------------------------------
# Checking the evidence
# --------------------------------------------------------------------------

def normalise(text: str) -> str:
    """Lower-case, straighten quotes and collapse spaces for comparison."""
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.strip().strip('"').strip("'").rstrip(".")
    return re.sub(r"\s+", " ", text).lower()


def quote_is_in_feedback(quote: str, feedback: str) -> bool:
    cleaned = normalise(quote)
    return bool(cleaned) and cleaned in normalise(feedback)


def check_evidence(data: dict, feedback: str) -> tuple[int, int]:
    """Mark each quote as verified or not. Return (verified, total)."""
    verified = total = 0
    for insight in data["insights"]:
        checked = []
        for quote in insight.get("evidence", []):
            found = quote_is_in_feedback(str(quote), feedback)
            checked.append({"quote": str(quote), "verified": found})
            total += 1
            verified += found
        insight["evidence"] = checked
    return verified, total


# --------------------------------------------------------------------------
# Writing the brief
# --------------------------------------------------------------------------

def severity_rank(risk: dict) -> int:
    severity = str(risk.get("severity", "")).strip().capitalize()
    return SEVERITIES.index(severity) if severity in SEVERITIES else len(SEVERITIES)


def render_report(
    data: dict,
    *,
    goal: str,
    source: str,
    model: str,
    verified: int,
    total: int,
    today: dt.date,
) -> str:
    out: list[str] = []
    out.append(f"# Sprint brief: {source}")
    out.append("")
    out.append(f"**Goal:** {goal}")
    out.append("")
    out.append(
        f"Generated on {today.isoformat()} by PM Employee using `{model}`. "
        f"Evidence check: {verified} of {total} quotes found word for word "
        "in the feedback."
    )
    out.append("")

    out.append("## 1. Insights")
    out.append("")
    for insight in data["insights"]:
        out.append(f"### {insight.get('theme', 'Untitled theme')}")
        out.append("")
        out.append(str(insight.get("summary", "")).strip())
        out.append("")
        for item in insight.get("evidence", []):
            flag = "" if item["verified"] else " **(not found in the feedback - check before using)**"
            out.append(f"> \"{item['quote']}\"{flag}")
            out.append("")

    out.append("## 2. User stories")
    out.append("")
    for number, story in enumerate(data["user_stories"], start=1):
        out.append(f"### {number}. {story.get('title', 'Untitled story')}")
        out.append("")
        out.append(str(story.get("story", "")).strip())
        out.append("")
        out.append("Acceptance criteria:")
        out.append("")
        for criterion in story.get("acceptance_criteria", []):
            out.append(f"- [ ] {criterion}")
        out.append("")

    email = data["stakeholder_email"]
    out.append("## 3. Stakeholder email")
    out.append("")
    out.append(f"**Subject:** {email.get('subject', '')}")
    out.append("")
    out.append(str(email.get("body", "")).strip())
    out.append("")

    out.append("## 4. Risks")
    out.append("")
    out.append("| Severity | Risk | Mitigation |")
    out.append("| --- | --- | --- |")
    for risk in sorted(data["risks"], key=severity_rank):
        cells = [
            str(risk.get("severity", "")).strip().capitalize(),
            str(risk.get("risk", "")).strip(),
            str(risk.get("mitigation", "")).strip(),
        ]
        out.append("| " + " | ".join(c.replace("|", "/").replace("\n", " ") for c in cells) + " |")
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------

def process(feedback_file: Path, mock_reply: str | None) -> Path:
    default_goal = read_default_goal()
    text = strip_comments(feedback_file.read_text(encoding="utf-8"))
    goal, feedback = split_goal(text, default_goal)
    if not feedback:
        raise ValueError(f"{feedback_file.name} has no feedback in it.")

    if mock_reply is not None:
        raw, model = mock_reply, "mock reply (no AI call)"
    else:
        raw, model = call_model(goal, feedback)
    data = parse_reply(raw)
    verified, total = check_evidence(data, feedback)

    report = render_report(
        data,
        goal=goal,
        source=feedback_file.name,
        model=model,
        verified=verified,
        total=total,
        today=dt.datetime.now(dt.timezone.utc).date(),
    )
    REPORTS_DIR.mkdir(exist_ok=True)
    target = report_path(feedback_file)
    target.write_text(report, encoding="utf-8")

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a", encoding="utf-8") as handle:
            handle.write(report + "\n\n---\n\n")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true",
                        help="rebuild briefs for every feedback file")
    parser.add_argument("--mock", metavar="FILE",
                        help="use a saved reply instead of calling an AI model")
    args = parser.parse_args(argv)

    mock_reply = Path(args.mock).read_text(encoding="utf-8") if args.mock else None

    if mock_reply is None and choose_provider() is None:
        print("No AI key found. Add GEMINI_API_KEY (free) or ANTHROPIC_API_KEY "
              "as a repository secret, or export one locally, or use --mock.",
              file=sys.stderr)
        return 2

    files = pending_feedback(args.all)
    if not files:
        print("No new feedback files. Nothing to do.")
        return 0

    failures = 0
    for feedback_file in files:
        try:
            target = process(feedback_file, mock_reply)
            print(f"Wrote {target.relative_to(ROOT)}")
        except Exception as error:  # keep going so one bad file does not block the rest
            failures += 1
            print(f"Failed on {feedback_file.name}: {error}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
