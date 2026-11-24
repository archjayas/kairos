# See your progress

Kairos keeps track of what you've done as you learn, and awards
[five badges](../progress.md) along the way. You don't have to log anything: the
scripts notice when you reach a milestone and save it on your computer.

There are three ways to see where you are. All of them read the same progress file.

| Way | Command | Best for |
|---|---|---|
| [In the terminal](#1-in-the-terminal) | `python progress.py --no-open` | A quick check |
| [Your progress page](#2-your-progress-page) | `python progress.py` | Seeing your journey and badges at a glance |
| [On the Kairos site](#3-on-the-kairos-site) | `mkdocs serve` | Your badges on the site's home page, updating live |

Run every command from the `kairos` folder, with your virtual environment active
(see the [Quickstart](../quickstart.md)).

## When you earn a badge

You don't need to check: the moment a step unlocks a badge, the script you ran says so.

```text
🏅 Badge earned: First Agent! See your progress: python progress.py
```

## 1. In the terminal

```bash
python progress.py --no-open
```

You'll see a progress bar, each milestone with the date you reached it, each badge,
and what to do next:

```text
Kairos progress  [####................]  1 of 5 badges

  [x] Ran the eval for free (baseline or replay)  (2026-11-23)
  [x] Completed a full tool call with the Claude agent  (2026-11-23)
  [ ] Ran the eval on a live model
  [ ] Scheduled a meeting through the MCP server
  [ ] Ran Kairos on another LLM (Gemini)

  🚀  First Agent: earned
  🔒  Evaluator: Run the eval on a live model.  ->  python evals/run_evals.py --models baseline,claude
  ...

Next up: Evaluator. Run the eval on a live model. Try: python evals/run_evals.py --models baseline,claude
```

## 2. Your progress page

```bash
python progress.py
```

This prints the same summary, then opens a page in your browser with:

- **A progress bar:** how many of the five badges you have.
- **Your journey:** one stop per milestone, filled in with the date you reached it.
- **What's next:** the next badge, and the command to try.
- **Your badges:** earned ones in color; locked ones in red, with how to earn them.

The page is saved as `.kairos/progress.html`. Run `python progress.py` again to
refresh it after you earn something.

## 3. On the Kairos site

Preview the site on your computer, and your badges appear on the home page (under
**Your badges**) and on the **My progress** tab:

```bash
pip install -r requirements-docs.txt     # first time only
mkdocs serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Hover a badge to see what it's
for, when you earned it, or how to earn it.

**Leave `mkdocs serve` running.** When you earn a badge, the page reloads by itself
within a second or two. You don't need to rebuild anything.

### Why a published site shows a preview

A published copy of the site (on GitHub Pages, for example) shows all five badges in
color, marked as a preview. That's because your progress is saved on **your** computer,
and a website on the internet can't read it. This is deliberate: your progress is never
uploaded, and if you publish the site yourself, your personal badges aren't included.

## What gets recorded

| Milestone | Recorded when |
|---|---|
| Ran the eval for free | `run_evals.py` runs with `--models baseline` or `--replay` |
| Completed a full tool call with Claude | `claude_agent.py` reaches Claude's final reply after the confirmation step (typing `y` or `n` both count) |
| Ran the eval on a live model | `run_evals.py` calls Claude or Gemini |
| Scheduled a meeting through MCP | The MCP server's `create_event` creates an event |
| Ran Kairos on another LLM | `gemini_agent.py` reaches Gemini's final reply, or the eval runs Gemini |

Progress is saved in `.kairos/progress.json` in the project folder. It's git-ignored,
so it's never committed, and nothing in Kairos sends it anywhere.

## Start over, or keep progress somewhere else

```bash
python progress.py --reset                          # forget all progress
export KAIROS_PROGRESS_FILE=~/kairos-progress.json   # save progress to another file
```

If you set `KAIROS_PROGRESS_FILE`, set it the same way every time, or Kairos reads a
different file and your badges seem to disappear.

## Related

- [Progress and badges](../progress.md): the five badges and what each one means
- [Troubleshooting: progress and badges](../troubleshooting.md#progress-and-badges)
- [Quickstart](../quickstart.md): earn your first badge
