# Eval dashboard

The dashboard turns an eval run into one page: pass rate, accuracy per check, the
made-up-field rate, token usage, every case's result, and pass rate over time.

Below is the dashboard for the saved sample run. It's the same run you can
[replay for free](how-to/run-the-eval.md).

<iframe src="../assets/dashboard/sample.html" title="Sample Kairos eval dashboard"
  style="width: 100%; height: 900px; border: 1px solid var(--md-default-fg-color--lightest); border-radius: 8px;"></iframe>

[Open the sample dashboard in its own tab](assets/dashboard/sample.html){ .md-button }

## Make your own

After any eval run:

```bash
python evals/run_evals.py --models baseline,claude    # or --models baseline (free)
python evals/dashboard.py
```

A replay doesn't save results, so to see a saved run, point the dashboard at it:
`python evals/dashboard.py --results evals/recordings/sample_run.json`.

`dashboard.py` reads your latest results (`evals/results/latest.json`), writes
`evals/results/dashboard.html`, and opens it in your browser. It makes no API calls and
needs no extra packages.

| Option | What it does |
|---|---|
| `--results FILE` | Use a different results file, for example `evals/recordings/sample_run.json` |
| `--out FILE` | Write the page somewhere else |
| `--no-open` | Don't open a browser |

## What each section shows

| Section | What it tells you |
|---|---|
| **At a glance** | Each extractor's pass rate, made-up-field rate, tokens, and errors |
| **Accuracy by check** | Which fields each extractor gets right: attendees, times, Zoom link, agenda, and asking when info is missing |
| **Pass rate over time** | One point per eval run, so you can see whether a prompt or model change helped. It appears after your second run |
| **Every case** | Pass or fail for each request; hover a result to see why |
| **Why each failure failed** | Expected vs. actual, for every failed check |
| **Table view** | The same numbers as a table |

## Token usage and cost

Every live run records the tokens each model used, and the dashboard totals them.
Multiply by your model's current price per million tokens (see your provider's pricing
page) to estimate a run's cost. The sample run was recorded before token tracking was
added, so it shows "not recorded".

To keep costs down while you learn:

- **Iterate for free.** `--models baseline` and `--replay` make no API calls.
- **Run live only when you'll keep the result,** for example to check a change.
- **Set a monthly spend limit** in your provider's console.
- **Watch the "Tokens" line** in the dashboard, and compare it across models.

## Related

- [Run the eval](how-to/run-the-eval.md)
- [Write your own eval cases](how-to/add-eval-cases.md)
- [Compare models](how-to/switch-models.md)
- [Progress and badges](progress.md): running a live eval earns the Evaluator badge
