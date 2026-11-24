# Add eval cases

Each line of `evals/cases.jsonl` is one test case in JSON. Add a line, [run the eval](run-the-eval.md),
and the new case is scored like the others.

## Case format

A request the model **should** act on:

```json
{"id": "c21", "category": "relative_date", "request": "Same day next week at 9am with dana@example.com for 30 min to review the budget.", "expect_call": true, "expected": {"attendees": ["dana@example.com"], "times": [["2026-12-08T09:00:00-08:00", "2026-12-08T09:30:00-08:00"]], "zoom_link": null, "agenda": true}}
```

A request the model **should not** act on, because something required is missing:

```json
{"id": "c22", "category": "incomplete", "request": "Book the usual sync with the design team.", "expect_call": false}
```

| Field | Meaning |
|---|---|
| `id` | Unique id, shown in the results table |
| `category` | Free-text label for grouping (`relative_date`, `zoom`, `incomplete`, ...) |
| `request` | Exactly what a user would type |
| `expect_call` | `true` if the model should call the tool, `false` if it should ask instead |
| `clarify_ok` | Optional. `true` if asking a question also counts as a pass |
| `expected.attendees` | Every email that should be invited, lowercase |
| `expected.times` | A list of acceptable `[start, end]` pairs, in RFC3339 with offsets |
| `expected.zoom_link` | The exact link, or `null` if the request has none |
| `expected.agenda` | `true` (must be present), `false` (must be absent), or `null` (not scored) |

Remember that "today" is **Tuesday, 2026-12-01, in America/Los_Angeles**. The model is
told the date but not the time of day, so avoid requests like "in two hours" that
depend on the current time. Work out
expected dates from that, and check the UTC offset for the event's date, not today's.

## Write cases that teach you something

A case that every extractor already passes doesn't add much. Good new cases are ones
you're not sure about:

- Messy phrasing: typos, "EOD Thursday", "after lunch tomorrow" (decide what you'd accept,
  or set `"clarify_ok": true` if asking is the right answer)
- Relative dates that need care: "same day next week at 3pm", "the 1st"
- Links without a label: a Zoom URL pasted at the end with no "Zoom:" in front
- Two people named but only one email given
- Requests where the right answer is a question, not a guess

## Keep a held-out set

If you tune the prompt while watching the same cases, you'll overfit to them. Keep a
second file that you don't look at while making changes, and run it only to check:

```bash
python evals/run_evals.py --cases evals/heldout.jsonl --out evals/results/heldout.json
```

## Check your case before running the models

Run the free [baseline](../../evals/baseline_extractor.py) first. It catches typos in the JSON and in expected times
without spending any API calls:

```bash
python evals/run_evals.py --models baseline
```

## Related

- [Run the eval](run-the-eval.md)
- [Compare models](switch-models.md)
- [How an eval works](../overview.md#how-an-eval-works)
- [Glossary: eval terms](../glossary.md#evals)
