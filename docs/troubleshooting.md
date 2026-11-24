# Troubleshooting and FAQ

Each answer quotes the exact message you'll see. New to a term? See the
[Glossary](glossary.md).

## Setup and keys

### `No matching distribution found for anthropic==...` during `pip install`

**Cause:** your virtual environment was made with a Python that's too old. Kairos needs
Python 3.11 or later. On macOS, `python3` often points to the built-in Python 3.9.

**Fix:** delete the old environment and make a new one with a newer Python:

```bash
deactivate                      # if the environment is active
rm -rf .venv
python3.12 -m venv .venv        # or whichever 3.11+ version you installed
source .venv/bin/activate
python --version                # should say 3.11 or later
pip install -r requirements.txt
```

Don't have 3.11 or later? Install it from
[python.org/downloads](https://www.python.org/downloads/).

### My API key is set, but the agent says it isn't

**Symptom:** `export` worked in one terminal, but the agent (or your editor) can't see
the key. For Gemini you'll see:

```text
ValueError: No API key was provided. Please pass a valid API key.
```

**Cause:** `export` only applies to the terminal you ran it in. Other terminals, and
apps like VS Code that were already open, don't see it.

**Fix:** add the key to your shell profile, then open a new terminal:

```bash
echo 'export GEMINI_API_KEY="your-key"' >> ~/.zshrc      # bash: ~/.bashrc
```

Check that it saved without printing the key: `grep -c GEMINI_API_KEY ~/.zshrc` should
print `1`. If you work in VS Code, quit it fully (Cmd+Q on macOS) and reopen it so it
reads the profile again.

### `Set CLAUDE_MODEL to a Claude model id`

The Claude agent doesn't hard-code a model. Set one:

```bash
export CLAUDE_MODEL=claude-opus-5-5
```

See [Switch models](how-to/switch-models.md).

### `Model '...' not found: check CLAUDE_MODEL`

The id is misspelled, retired, or not available to your key. List the ones you can use:

```bash
python -c "import anthropic; [print(m.id) for m in anthropic.Anthropic().models.list()]"
```

### `Set ANTHROPIC_API_KEY to your key from console.anthropic.com.`

The Claude agent checks for your key before asking for a request. Set it (see
[My API key is set, but the agent says it isn't](#my-api-key-is-set-but-the-agent-says-it-isnt)
if you already did). The Gemini agent shows the same kind of message for
`GEMINI_API_KEY`.

### `Authentication failed: check ANTHROPIC_API_KEY`

The key is set, but it's mistyped or revoked. Create a new one at
[console.anthropic.com](https://console.anthropic.com) and set it again.

### I ran out of usage credits

Model calls are paid from your API account, so an empty balance stops them. What you'll
see:

- **Claude agent:** `Bad request: ...` with a message saying your credit balance is too
  low.
- **Gemini agent:** `Gemini API error: ...` with a 429 saying your prepayment credits are
  depleted. A 429 can also mean a rate limit, which clears if you wait; a credits 429
  doesn't.
- **The eval:** every call to that model fails, followed by
  `Warning: every claude call failed`. The run isn't saved, so your last good results
  are kept.

Add credits in [console.anthropic.com](https://console.anthropic.com) (Plans & Billing)
or, for Gemini, in [aistudio.google.com](https://aistudio.google.com), then run the step
again. To avoid surprises, set a monthly spend limit in the same place.

While you top up, the free steps still work: `--models baseline` and `--replay` make no
model calls, and [Path 2](how-to/use-mcp.md) uses your Claude Code or Claude Desktop plan,
not API credits.

### `zsh: command not found: code`

That's the VS Code shell command, which isn't installed by default on macOS. In VS
Code, open the Command Palette (Cmd+Shift+P) and run **Shell Command: Install 'code'
command in PATH**. You don't need it for this project.

## Dates and times

### The time is off by a few hours

`TIMEZONE` probably doesn't match where you are. It defaults to `America/Los_Angeles`:

```bash
export TIMEZONE=America/New_York
```

See [Change your timezone](how-to/change-timezone.md).

### `TIMEZONE='...' isn't a timezone Kairos recognizes`

`TIMEZONE` must be a `Region/City` name like `America/Chicago`, not a word like
`Pacific`. Avoid abbreviations too: some, like `EST`, are accepted but ignore daylight
saving. See [Change your timezone](how-to/change-timezone.md).

### "Next Friday" picked a different Friday than I meant

It's ambiguous: on a Tuesday, "next Friday" can mean this week's or next week's.
Models sometimes ask and sometimes pick one. Check the date in the confirmation
summary before typing `y`, or say the date: *"Friday, December 11."*

## Model behavior

### The model asked a question instead of creating the event

That's intended when a required detail is missing, usually an attendee email. The
model is told never to invent emails. Run it again with the details it asked for.

### The model says the event was created, but it's not on my calendar

You're on the mock backend, the default. It prints the event instead of sending it.
Set `CALENDAR_BACKEND=google` to write to your real calendar; see
[Use your real Google Calendar](how-to/use-google-calendar.md).

### I typed `yes` and it cancelled

Only `y` creates the event, in either case and ignoring spaces. Anything else,
including `yes`, cancels. That's deliberate: a confirmation step that guesses what you
meant isn't a confirmation step.

## MCP (Path 2)

### `/mcp` doesn't list `kairos`, or says it failed to start

- **Start Claude Code in the `kairos` folder.** It reads `.mcp.json` from the folder
  it starts in.
- **Create the virtual environment first.** `.mcp.json` runs `.venv/bin/python`, so
  `.venv` must exist with the packages installed (see the [Quickstart](quickstart.md)).
- **On Windows**, change `command` in `.mcp.json` to `.venv\\Scripts\\python.exe` (JSON needs
  each backslash written twice).
- **Still failing?** Use the absolute path to the Python inside `.venv`. See
  [Use Kairos over MCP](how-to/use-mcp.md).

### `Unknown, already-used, or replaced confirmation_id`

Only the newest preview can be created, and each one only once. If you asked for a
change, Claude previews again, and the earlier preview is cancelled. Ask Claude to
preview the event again, then approve it.

### Claude created the event without asking me

You've probably allowed `create_event` to run without approval. Remove that
permission in Claude Code so it asks every time; the server's two-step gate relies on
it. See [why the gate is two tools](how-to/use-mcp.md#why-the-approval-gate-is-two-tools).

## Google Calendar

### `FileNotFoundError: ... credentials.json`

With `CALENDAR_BACKEND=google`, the app needs an OAuth client file. Either save it as
`credentials.json` in the directory you run from, or point to it with
`GOOGLE_CREDENTIALS_FILE`. See [Use your real Google Calendar](how-to/use-google-calendar.md).

### It worked before, but now authorization fails

The saved token in `token.json` expired or was revoked. Delete it and run again; a
browser window asks you to approve access once more.

### `Error 403: access_denied` in the browser

Your OAuth consent screen is in testing mode and your account isn't listed as a test
user. Add it under **OAuth consent screen → Test users** in the Google Cloud console.

### `ValueError: Unknown CALENDAR_BACKEND '...'`

Only `mock` and `google` are supported.

## Eval

### `Skipping gemini: set GEMINI_API_KEY to run it.`

The [eval](how-to/run-the-eval.md) skips any model it can't call: `claude` needs
`CLAUDE_MODEL` and `ANTHROPIC_API_KEY`, and `gemini` needs `GEMINI_API_KEY`. `baseline`
always runs. If nothing is left to run, the eval says so and suggests `--models baseline`.

### `Unknown --models ...`

Model names are `baseline`, `claude`, and `gemini`, separated by commas, for example
`--models baseline,claude`.

### `Warning: every claude call failed`

Every call to that model returned an error, usually a wrong API key or model id. Check
the error messages above the warning. The run isn't saved, so your last good results
and your trend chart aren't affected, and it doesn't count toward the Evaluator badge.

### A case passed last time and failed this time

Models aren't fully deterministic, and by default each case runs once. Look at the
"Why each failure failed" section and `evals/results/latest.json` to see what the model
returned. Run with `--repeat 3` to see how often each case passes. If a case keeps
changing, it's telling you the request is ambiguous.

### Does the eval create calendar events?

No. It stops after the model's first turn and never calls the confirmation step or
any calendar backend, mock or real.

## Progress and badges

For every way to check your progress, see [See your progress](how-to/see-your-progress.md).

### Do I need to rebuild the site to see a new badge?

No. Preview the site with `mkdocs serve` and leave it running: when you earn a badge,
the page reloads by itself within a second or two. If it doesn't, stop `mkdocs serve`
(Ctrl+C) and start it again.

A **published** site (`mkdocs build` or `mkdocs gh-deploy`) never shows your personal
badges, so rebuilding or republishing won't change it. That's deliberate: your progress
stays on your computer.

### The home page shows all five badges in color, but I haven't earned them

You're looking at a published or built copy of the site, which shows the badges as a
preview of what you can earn. To see your own, run `mkdocs serve` and open
`http://127.0.0.1:8000`. Opening files from the `site/` folder directly shows the
preview too.

### I did the step, but the badge didn't unlock

Check what Kairos recorded:

```bash
python progress.py --no-open
```

Then compare with what counts for each milestone:

- **Free eval:** `run_evals.py` with `--models baseline` or `--replay`.
- **Claude agent:** `claude_agent.py` has to reach Claude's final reply after the
  confirmation step. If you stopped it early (Ctrl+C), or Claude asked a question
  instead of calling the tool, it doesn't count. Run it again with a complete request.
- **Live eval:** `run_evals.py` has to call Claude or Gemini. Replay doesn't count here,
  because it makes no model calls.
- **MCP:** an event has to be created through the MCP server. Previewing isn't enough;
  approve the `create_event` call.
- **Gemini:** `gemini_agent.py` has to reach Gemini's final reply, or the eval has to
  run `--models gemini`.

The **First Agent** badge needs two milestones: the free eval *and* the Claude agent.

### My badges disappeared

Progress is saved in `.kairos/progress.json` inside the project folder. A new clone, a
deleted `.kairos` folder, or `python progress.py --reset` starts you over. If you set
`KAIROS_PROGRESS_FILE`, Kairos reads and writes that file instead, so check it's set the
same way each time.

### Is my progress sent anywhere?

No. It's a small file on your computer, it's git-ignored so it isn't committed, and
nothing in Kairos uploads it.

### How do I start over?

```bash
python progress.py --reset
```
