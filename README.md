# PM Employee

Drop raw customer feedback into this repository and get a sprint brief back: insights with evidence, user stories, a stakeholder email and the top three risks. It runs entirely on GitHub Actions, using the free tier of Google's Gemini API. There is no app to open, nothing to install and nothing to pay for.

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
The script sends the goal and the feedback to Gemini through Google's API
        |
Every evidence quote is checked against the original feedback
        |
reports/new-file.md is saved back to the repository and shown on the run's summary page
```

The script only writes briefs for feedback files that do not have one yet, so the Monday run does nothing when there is no new feedback.

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

1. Copy this repository.
2. Create a free API key at [Google AI Studio](https://aistudio.google.com/apikey).
3. In the repository, go to **Settings > Secrets and variables > Actions** and add a secret named `GEMINI_API_KEY`.
4. Add a feedback file to `feedback/` and push it. The brief appears in `reports/` about a minute later.

To set the product goal, start a feedback file with a line such as `Goal: Reduce checkout drop-off`. Files without that line use the goal in [`goal.md`](goal.md).

### Choosing the model

| Setting | Effect |
| --- | --- |
| Secret `GEMINI_API_KEY` only | Tries `gemini-3.8-flash`, then `gemini-3.6-flash`, then `gemini-3.5-flash-lite` |
| Repository variable `PM_EMPLOYEE_MODEL` | Uses that model instead |
| Secret `ANTHROPIC_API_KEY` | Uses Claude through the Anthropic API (paid) instead of Gemini |

Each brief names the model that wrote it.

## Run it on your own machine

```
export GEMINI_API_KEY=your-key
python pm_employee.py            # briefs for new feedback files
python pm_employee.py --all      # rebuild every brief
```

To try it with no key at all, use the saved test reply:

```
python pm_employee.py --mock tests/fixtures/mock_reply.json
```

## Tests

```
pip install pytest
pytest
```

The 16 tests cover goal handling, the request sent to the model, falling back to a second model, parsing the reply, the evidence check, the report layout and a full run using a saved reply. They need no key and run on every push.

## Files

| File | Purpose |
| --- | --- |
| `pm_employee.py` | The whole workflow: read feedback, call the AI model, check quotes, write the brief |
| `.github/workflows/pm-employee.yml` | Runs the script on new feedback, on Mondays and on demand |
| `.github/workflows/tests.yml` | Runs the tests on every push |
| `feedback/` | Input: one file per batch of feedback |
| `reports/` | Output: one brief per feedback file |
| `goal.md` | The default product goal |
| `tests/` | Tests and the saved reply they use |

## Time saved

About 40 minutes per batch of feedback.

| | Time per batch |
| --- | --- |
| By hand: themes with quotes, user stories, stakeholder email, risks | About 45 minutes (my estimate) |
| With the workflow: the run itself, unattended | 1 to 2 minutes |
| With the workflow: reading and checking the brief | About 5 minutes |

## How it was built

I defined the workflow, its four outputs and the evidence-check rule. The code was written with Claude, Anthropic's AI assistant, and I reviewed and ran it.

## Limits

- The brief is a first draft. A person should read it before anything is sent or scheduled.
- The evidence check confirms a quote exists in the feedback. It does not judge whether the theme drawn from it is right.
- Gemini's free tier has rate limits, and its list of free models changes over time. If the default models are retired, set `PM_EMPLOYEE_MODEL` to a current one.
- Google uses free-tier content to improve its products, so do not put confidential customer feedback through the free tier. Use a paid key for real data.
- GitHub pauses scheduled workflows in repositories with no activity for 60 days.
