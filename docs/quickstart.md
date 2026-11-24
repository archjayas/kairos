# Quickstart

Clone Kairos, try it without an API key, then schedule your first meeting with Claude.
Everything here uses the **mock calendar**: nothing is sent to a real calendar, and no
invites go out.

New to some of the terms? See the [Glossary](glossary.md).

## Before you start

You need:

- **Python 3.11 or later.** Check with:

  ```bash
  python3 --version
  ```

  If it says 3.10 or lower, or "command not found", install a current Python from
  [python.org/downloads](https://www.python.org/downloads/).

  **On a Mac, check this even if Python is installed.** macOS includes an older Python
  (3.9), and `python3` may point to it. After installing a newer one, run its versioned
  command instead, for example `python3.12 --version`, and use `python3.12` in place of
  `python3` in step 1.
- **git**, to download the code. Check with `git --version`.
- **An Anthropic API key**, for step 4 only. Steps 1 to 3 work without one. Get a key at
  [console.anthropic.com](https://console.anthropic.com) under **API Keys**. Model calls
  cost money; this whole quickstart costs a few cents.

On Windows, use PowerShell, and type `python` wherever this page says `python3`.

## 1. Download and install

```bash
git clone https://github.com/archjayas/kairos.git
cd kairos
python3 -m venv .venv
```

The last line creates a **virtual environment**: a private folder (`.venv`) for this
project's packages, so they don't mix with anything else on your computer. Turn it on:

```bash
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\Activate.ps1         # Windows PowerShell (if it says scripts are disabled,
                                   # run: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
```

Your prompt now starts with `(.venv)`. Run the activate command again whenever you open
a new terminal for this project. Then install the packages:

```bash
pip install -r requirements.txt
```

## 2. Try the eval, free (no API key)

The eval checks how well something turns a request into event details. The
**baseline** is plain pattern matching, with no AI, so it runs instantly and for free:

```bash
python evals/run_evals.py --models baseline
```

You'll see a table of 20 test requests, each marked `PASS` or `FAIL`, then a summary and
an explanation of every failure. The baseline gets 17 of 20. The three it misses are the
ones that need a model: a time in another timezone, and agendas the baseline's simple
patterns can't spot.

## 3. See how Claude did, free (no API key)

The repo includes a saved run of Claude and Gemini on the same 20 requests. **Replay**
scores it again without calling any model:

```bash
python evals/run_evals.py --replay evals/recordings/sample_run.json
```

Both models pass all 20. Compare their column with the baseline's to see where the
model earns its cost. [Run the eval](how-to/run-the-eval.md) explains every column.

To see the same results as charts, open them in the dashboard:

```bash
python evals/dashboard.py --results evals/recordings/sample_run.json
```

## 4. Schedule a meeting with Claude

Now you need your API key. Set it, plus the model to use, in your terminal:

```bash
export ANTHROPIC_API_KEY="paste-your-key-here"     # macOS / Linux
export CLAUDE_MODEL="claude-opus-5-5"
```

```powershell
$env:ANTHROPIC_API_KEY = "paste-your-key-here"     # Windows PowerShell
$env:CLAUDE_MODEL = "claude-opus-5-5"
```

These are **environment variables**: settings the program reads when it starts. Keeping
the key there means it's never written into the code. They last until you close the
terminal. To keep them, see
[Troubleshooting](troubleshooting.md#my-api-key-is-set-but-the-agent-says-it-isnt).
To use a different Claude model, see [Switch models](how-to/switch-models.md).

Run the agent:

```bash
python claude_agent.py
```

At `Your request:`, paste this and press Enter:

```text
Schedule a meeting with alice@example.com and bob@example.com tomorrow at 2pm for 45 minutes to discuss Q3 planning. Zoom link: https://zoom.us/j/123456789
```

Claude reads the request and fills in the event details. Before anything is created,
you'll see a summary like this, with tomorrow's date:

```text
About to create this event:
  Title:     Q3 Planning Discussion
  Start:     Tue Dec 1, 2026 2:00 PM PST      (your date will be tomorrow's)
  End:       Tue Dec 1, 2026 2:45 PM PST
  Attendees: alice@example.com, bob@example.com
  Agenda:    Discuss Q3 planning.
  Zoom link: https://zoom.us/j/123456789
Create this event? (y/n)
```

Check the date and time, then type `y`. The mock calendar prints the event it would have
created, and Claude confirms in plain language.

## 5. Say no, and leave something out

- **Say no.** Run it again and type `n`. Nothing is created, and Claude offers to
  change something.
- **Leave something out.** Try *"Set up a 30 minute sync with Alice tomorrow at 3pm."*
  There's no email address, so Claude asks for one instead of guessing.

## What just happened

1. Your request went to Claude, together with a description of a tool called
   `create_calendar_event`.
2. Claude replied by asking to call that tool, with the details it found: title, times,
   attendees, agenda, Zoom link.
3. Kairos's code checked the times, showed you the summary, and waited for your `y`.
4. The result went back to Claude, which wrote the confirmation you read.

That loop is the core of every tool-using agent. The [Overview](overview.md#how-an-agent-works-in-six-steps)
explains it step by step, and [`claude_agent.py`](../claude_agent.py) is the code:
about 150 lines with comments, worth reading top to bottom.

You just used **Path 1**: an agent loop you run yourself. Kairos has a second path.

## 6. Optional: the same tool in Claude Code (Path 2)

In Path 2 you don't run an agent script. Claude Code runs the loop, and Kairos's tools
reach it through an **MCP server** ([`mcp_server.py`](../mcp_server.py)). If you have
[Claude Code](https://claude.com/claude-code) installed, from the `kairos` folder run:

```bash
claude
```

Approve the `kairos` MCP server when asked, type `/mcp` to check it's connected, then
ask Claude Code to schedule the same meeting. It shows you a preview first and creates
nothing until you approve. See [Use Kairos over MCP](how-to/use-mcp.md) for details,
Claude Desktop, and debugging.

**On Windows**, first change `command` in `.mcp.json` to `.venv\\Scripts\\python.exe`
(JSON needs each backslash written twice).

## See your progress

Kairos notices what you've done. After steps 2 and 4 you've earned your first badge,
**First Agent**: you'll see a message when it happens. To see all your badges and what's next:

```bash
python progress.py
```

See [Progress and badges](progress.md) for the full list, and
[See your progress](how-to/see-your-progress.md) for every way to check.

## Next steps

- [Overview](overview.md): how the pieces fit together, and the two paths compared
- [Eval dashboard](eval-dashboard.md): see the eval's results as charts
- [Run the eval](how-to/run-the-eval.md) on Claude yourself, and read the results
- [Add eval cases](how-to/add-eval-cases.md): write requests you think might trip Claude up
- [Use your real Google Calendar](how-to/use-google-calendar.md)
