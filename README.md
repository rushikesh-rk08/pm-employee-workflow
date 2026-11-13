# PM Employee

Drop raw customer feedback into this repository and get a sprint brief back: insights with evidence, user stories, a stakeholder email and the top three risks. It runs entirely on GitHub Actions. There is no app to open and nothing to install.

## What it does

A product manager reads interviews, support tickets and survey comments, then turns them into working documents for the next sprint. This workflow does the first draft of that work.

| Input | Output |
| --- | --- |
| A text or Markdown file of customer feedback in `feedback/` | A sprint brief in `reports/` with the same file name |

Each brief has four parts:

1. **Insights**: the main themes, each backed by quotes from the feedback.
2. **User stories**: written for engineers, with acceptance criteria as a checklist.
3. **Stakeholder email**: a subject line and a body under 200 words.
4. **Risks**: the top three, with severity and a mitigation for each.

## How it works

```
feedback/new-file.md is added      (or it is Monday 09:00 India time, or you press "Run workflow")
        |
GitHub Actions starts pm_employee.py
        |
The script sends the goal and the feedback to Claude through the Anthropic API
        |
Every evidence quote is checked against the original feedback
        |
reports/new-file.md is saved back to the repository and shown on the run's summary page
```

The script only writes briefs for feedback files that do not have one yet, so the Monday run costs nothing when there is no new feedback.

## The evidence check

AI models sometimes paraphrase a quote or invent one. A brief that misquotes a customer is worse than no brief, so the script compares every quote the model returns with the original feedback, ignoring only case, spacing and quote style.

- A quote found word for word is shown as normal.
- A quote that is not found stays in the brief, marked **"not found in the feedback - check before using"**.
- The top of every brief states the count, for example "11 of 12 quotes found word for word".

The model drafts; the person reading the brief decides what to trust.

## See it run

- **Input:** [`feedback/2026-11-student-housing-sample.md`](feedback/2026-11-student-housing-sample.md)
- **Output:** the matching file in [`reports/`](reports/)
- **Run history:** the **Actions** tab of this repository

The sample feedback is invented for this demonstration. It does not come from a real company or real customers.

## Set it up in your own repository

1. Create an API key at the Anthropic Console.
2. In the repository, go to **Settings > Secrets and variables > Actions** and add a secret named `ANTHROPIC_API_KEY`.
3. Add a feedback file to `feedback/` and push it. The brief appears in `reports/` about a minute later.

To set the product goal, start a feedback file with a line such as `Goal: Reduce checkout drop-off`. Files without that line use the goal in [`goal.md`](goal.md).

The model defaults to `claude-sonnet-5-5`. To change it, add a repository variable named `PM_EMPLOYEE_MODEL`.

## Run it on your own machine

```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your-key
python pm_employee.py            # briefs for new feedback files
python pm_employee.py --all      # rebuild every brief
```

To try it without an API key, use the saved test reply:

```
python pm_employee.py --mock tests/fixtures/mock_reply.json
```

## Tests

```
pip install pytest
pytest
```

The 11 tests cover goal handling, parsing the model's reply, the evidence check, the report layout and a full run using a saved reply. They need no API key and run on every push.

## Files

| File | Purpose |
| --- | --- |
| `pm_employee.py` | The whole workflow: read feedback, call Claude, check quotes, write the brief |
| `.github/workflows/pm-employee.yml` | Runs the script on new feedback, on Mondays and on demand |
| `.github/workflows/tests.yml` | Runs the tests on every push |
| `feedback/` | Input: one file per batch of feedback |
| `reports/` | Output: one brief per feedback file |
| `goal.md` | The default product goal |
| `tests/` | Tests and the saved reply they use |

## Time saved

<!-- Fill this in after timing one batch by hand and one with the workflow. -->
To be measured: time for one batch of feedback by hand versus with this workflow.

## How it was built

I defined the workflow, its four outputs and the evidence-check rule. The code was written with Claude, Anthropic's AI assistant, and I reviewed and ran it.

## Limits

- The brief is a first draft. A person should read it before anything is sent or scheduled.
- The evidence check confirms a quote exists in the feedback. It does not judge whether the theme drawn from it is right.
- GitHub pauses scheduled workflows in repositories with no activity for 60 days.
