# Run the eval

The eval measures how well each model extracts event details from a request. It sends
20 fixed requests to each extractor, captures the tool arguments from the first turn,
and scores them. **It never runs the confirmation step or touches any calendar.**

## Run it

From the repo root:

```bash
python evals/run_evals.py                          # every extractor with credentials set
python evals/run_evals.py --models baseline        # free: no API keys, no network
python evals/run_evals.py --models baseline,claude
```

An **extractor** is anything that turns a request into event details: the no-AI
baseline, Claude, or Gemini. The eval scores each one the same way.

| Extractor | Needs |
|---|---|
| `baseline` | Nothing. It's regex and the standard library. |
| `gemini` | `GEMINI_API_KEY` (and optionally `GEMINI_MODEL`) |
| `claude` | `ANTHROPIC_API_KEY` and `CLAUDE_MODEL` ([choose one](switch-models.md)) |

Claude is skipped if `CLAUDE_MODEL` isn't set, and Gemini if `GEMINI_API_KEY` isn't. A
full run is about 40 model calls and costs well under a dollar.

### Options

| Option | What it does |
|---|---|
| `--models baseline,claude,gemini` | Which extractors to run (default: all three) |
| `--replay FILE` | Score saved responses instead of calling models. Free; try `evals/recordings/sample_run.json` |
| `--repeat N` | Run each case N times, to find *flaky* cases that pass on some runs and fail on others |
| `--no-boundary` | Leave the "use only what's in the request" instruction out of the prompt, to measure what it's worth |
| `--cases FILE` | Use a different case file, such as a held-out set |
| `--out FILE` | Where to save results (default `evals/results/latest.json`) |

## What gets scored

"Today" is pinned to **Tuesday, 2026-12-01, in America/Los_Angeles** (the model is told
the date, not the time), so results
don't change with the date you run them.

| Check | Passes when |
|---|---|
| `attendees` | The set of emails matches exactly (order and case ignored) |
| `start`, `end` | The times are the same moment as expected (`15:00-05:00` equals `12:00-08:00`) |
| `zoom_link` | It matches the link in the request, or is absent when there isn't one |
| `agenda` | It's present when the request gives a topic, absent when it doesn't, unscored when it's unclear |
| `no_call` | On an incomplete request, the model asked instead of calling the tool |

A case passes only if all its checks pass. For the ambiguous case (c17, "next Friday"),
either Friday is accepted, and so is asking which one was meant.

The **made-up-field rate** is the share of tool calls that include an email or Zoom
link not in the request, or an agenda the request never gave. Lower is better.

## Read the output

The run prints three things:

1. **A table**: one row per case, `PASS` or `FAIL: <checks>` per extractor.
2. **A summary**: the pass rate and per-check accuracy for each extractor.
3. **"Why each failure failed"**: expected vs. actual for every failed check.

Full results, including every model's tool arguments and token usage, are written to
`evals/results/latest.json`. Use `--out` to write elsewhere.

To see the results as charts, with token usage and pass rate over time, run
`python evals/dashboard.py`. See [Eval dashboard](../eval-dashboard.md).

## Latest results

From the saved run (Claude `claude-opus-5-5`, Gemini `gemini-3.6-flash`). See them as
charts on the [eval dashboard](../eval-dashboard.md).

| Metric | Baseline (no AI) | Claude | Gemini |
|---|---|---|---|
| Cases passed | 17/20 | 20/20 | 20/20 |
| Start / end time | 16/17 | 17/17 | 17/17 |
| Agenda | 7/9 | 9/9 | 9/9 |
| Attendees, Zoom link | 100% | 100% | 100% |
| Asks when info is missing | 3/3 | 3/3 | 3/3 |
| Made-up-field rate | 0% | 0% | 0% |

**What this shows.** The baseline matches both models on emails, Zoom links,
durations, and simple dates. The models earn their cost on two things: times in
another timezone ("3pm Eastern") and agendas the baseline's patterns can't spot
("We'll walk through the Q4 incident report..."). It also shows the limits of the set:
both models score 100%, so these cases can no longer tell them apart. The next step
is [harder cases](add-eval-cases.md).

## What the eval doesn't measure

- **The reply text.** Only the tool arguments are scored, not how well the model words
  its question or confirmation.
- **The event title.** Titles vary legitimately ("Q3 Planning" vs. "Q3 Planning
  Discussion"), so they're not compared.
- **Consistency,** unless you ask. By default each case runs once, and a case that passes
  on one run can fail on the next. Use `--repeat 3` to find those flaky cases.
- **Hard inputs.** The 20 cases are cleanly written. Both models currently score 100%,
  which means the set can no longer tell them apart. [Add harder cases](add-eval-cases.md).

## Related

- [How an eval works](../overview.md#how-an-eval-works)
- [Add eval cases](add-eval-cases.md)
- [Compare models](switch-models.md)
- [Glossary: eval terms](../glossary.md#evals)
- [Troubleshooting: eval](../troubleshooting.md#eval)
