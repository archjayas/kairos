# Overview

**Kairos is a learning project for people who want to build their first AI agent and
learn to evaluate it, but haven't known where to start.**

If agents and evals feel like something only AI specialists build, this project is
meant to change that. The whole agent is a few hundred lines of plain Python. The eval
is one script you can run for free. Every piece is small enough to read in one sitting
and change yourself.

Kairos is built mainly on **Claude**. The same agent is also built on **Gemini**, to show
that once you understand the pattern, moving it to another LLM API is a small job, not
a rewrite.

## Why a calendar?

The example agent turns a plain-English request ("45 minutes with alice@example.com
tomorrow at 2pm") into a calendar event. That's the *example*, not the point. Scheduling
was chosen because it's a good teacher:

- **Everyone understands the task**, so you can focus on how the agent works rather
  than on the domain.
- **The output is checkable.** A date is right or wrong, which makes it ideal for
  learning evals.
- **It has real stakes.** An event sends invites to real people, so you learn why an
  agent should ask before it acts.
- **It has a classic weak spot.** Models are confidently wrong about dates and
  timezones, which shows what code should own instead.

Swap the calendar for a support ticket, a database query, or an email draft, and every
idea below still applies.

## What you'll learn

| Skill | What it means | Where to see it in Kairos |
|---|---|---|
| **Build a tool-calling agent** | Describe a tool to the model, let it fill in the arguments, run the tool in your code, send the result back | [`claude_agent.py`](../claude_agent.py) |
| **Add a human approval gate** | Stop and ask the user before the agent does anything with real effects | `run_tool_call()` in [`calendar_tools.py`](../calendar_tools.py) |
| **Let code own what code does best** | The model reads language; code does date math and timezones | `normalize_datetime()` in [`calendar_tools.py`](../calendar_tools.py) |
| **Write your first eval** | A fixed set of test requests, each with the answer you expect, scored automatically | [`evals/`](../evals/) |
| **Check whether you need an LLM at all** | Score a simple non-AI baseline the same way, and see where the model actually earns its cost | [`evals/baseline_extractor.py`](../evals/baseline_extractor.py) |
| **Measure made-up answers** | Count how often the model fills in a detail the request never gave | The made-up-field rate in [`evals/run_evals.py`](../evals/run_evals.py) |
| **Read results, not just scores** | See pass rates, failures, token usage, and trends on a dashboard | [`evals/dashboard.py`](../evals/dashboard.py) and the [eval dashboard](eval-dashboard.md) |
| **Run the same agent on another LLM API** | Keep the shared logic, change only the API calls | [`gemini_agent.py`](../gemini_agent.py) and [Claude and Gemini side by side](PORTING.md) |
| **Expose a tool over MCP** | Turn the same tool into a server that any MCP client (Claude Code, Claude Desktop) can use | [`mcp_server.py`](../mcp_server.py) and [Use Kairos over MCP](how-to/use-mcp.md) |
| **Package it for others** *(advanced)* | Bundle the MCP server, a slash command, and a skill as a Claude Code plugin | [Bundle Kairos as a Claude Code plugin](how-to/package-as-plugin.md) |

As you go, Kairos tracks what you've done and awards [five badges](progress.md), from
**First Agent** to **Kairos Complete**. Run `python progress.py` any time to see where
you are.

## How an agent works, in six steps

Every tool-using agent follows the same loop. Here it is with Kairos as the example.

1. **The user asks for something.** *"45 minutes with alice@example.com tomorrow at 2pm
   to discuss Q3 planning."*
2. **Your code sends the request to the model, along with a description of a tool**:
   its name, what it does, and the arguments it takes. Kairos has one tool,
   `create_calendar_event`.
3. **The model decides.** If it has what it needs, it replies by asking to call the
   tool, with the arguments filled in. If something required is missing (here, usually
   an email address), it asks the user instead.
4. **Your code checks and confirms.** The model never runs anything itself. Your code
   checks the arguments (Kairos fixes timezones, and rejects a missing field or an end
   time before the start), shows them to the user, and waits for `y`.
5. **Your code runs the tool.** Kairos creates the event, on a mock calendar by default.
6. **Your code sends the result back to the model,** which tells the user what happened
   in plain language.

That's it. Kairos asks the model for one tool call at a time, which keeps the loop easy
to follow. Bigger agents add more tools and repeat steps 3 to 6 in a loop, but the
pattern doesn't change.

## Two paths: with and without MCP

Kairos lets you use the same tool in two ways. The difference is **who runs the loop
above**.

| | **Path 1: Build the agent yourself** | **Path 2: Use the tool over MCP** |
|---|---|---|
| You run | `python claude_agent.py` | Claude Code or Claude Desktop, with `mcp_server.py` |
| Who runs the loop | Your code, step by step | The MCP client |
| Approval gate | `Create this event? (y/n)` in your terminal | `preview_event`, then `create_event` with a one-time id (only the newest preview counts) |
| Today's date and timezone | In the system prompt | From a `current_time` tool |
| What you learn | How an agent works under the hood | How to make a tool reusable by any AI app |

```
                     calendar_tools.py
        (field descriptions · dates · summary · calendars)
                 /                           \
   Path 1: claude_agent.py              Path 2: mcp_server.py
   your loop, Claude Messages API       Claude Code / Desktop runs the loop
```

**MCP (Model Context Protocol)** is an open standard for connecting AI apps to tools
and data. Write a tool once as an MCP server, and any MCP client can use it, without
the client's developers writing code for your tool.

## Which path should I choose?

Ask yourself one question: **am I building my own app, or adding a capability to an AI
app I already use?**

**Choose Path 1 (build the agent yourself) if:**

- You're new to agents and want to see what happens at every step
- You're building your own program: a script, a backend service, a bot
- You want full control of the prompt, the approval step, logging, and errors
- You want to measure the agent with the eval (it tests Path 1 directly)
- You have an Anthropic API key, and don't use Claude Code or Claude Desktop

**Choose Path 2 (MCP) if:**

- You already use Claude Code or Claude Desktop and want it to schedule meetings
- You want one tool that several AI apps can use
- You'd rather not write or maintain an agent loop
- You don't have an Anthropic API key: the server makes no model calls itself, so your
  existing Claude Code or Claude Desktop sign-in is enough

| | Path 1: build the agent | Path 2: MCP |
|---|---|---|
| You write | The loop and the tool | Only the tool |
| You need | An Anthropic API key | Claude Code or Claude Desktop |
| Who controls the prompt | You (`build_system_prompt()`) | The client, plus the server's instructions |
| How you approve | Type `y` in the terminal | Approve the tool call in the client's chat |
| Measured by the eval | Yes, directly | Partly: same field descriptions, but the client adds its own prompt |
| Best for | Learning how agents work; building your own app | Extending an AI app you already use |

**Not sure? Do Path 1 first, then Path 2.** Writing the loop yourself once makes it
clear what an MCP client does for you. After that, Path 2 is mostly setup: your
tool code stays the same.

## How an eval works

An eval answers one question: *how often does the agent get it right?*

1. **Write down test requests and the answers you expect.** Kairos has 20, in
   [`evals/cases.jsonl`](../evals/cases.jsonl). Three are deliberately incomplete; the
   right answer for those is a question, not a tool call.
2. **Run each request through the model, but stop before anything happens.** The eval
   captures the tool arguments from step 3 above and never touches a calendar.
3. **Compare what the model returned with what you expected,** field by field:
   attendees, start, end, Zoom link, agenda.
4. **Run a simple baseline the same way.** If plain pattern matching scores as well on
   a field, the model isn't needed for it.
5. **Read the failures.** The point of an eval isn't the score. It's learning *why*
   each case failed.
6. **Run it again, and watch the trend.** Models aren't fully predictable, so
   `--repeat 3` shows which cases are *flaky*. The [eval dashboard](eval-dashboard.md)
   charts every run, including the tokens each one used, so you can see whether a
   change helped and what it cost.

You can run the baseline and replay a saved Claude run without an API key, so you can
explore all of this for free before spending anything. Today's results, and what they
show, are in [Run the eval](how-to/run-the-eval.md#latest-results).

## Design decisions

### Why a confirmation step

The model writes to your calendar and emails invites to real people, so a wrong guess
has a cost. Every event is shown in plain language, with times converted to your own
timezone, before anything is created. Only an explicit `y` proceeds. Anything else
cancels, and the model is told you declined, so it doesn't claim the event exists.
Converting times for display matters too: if the model picks the wrong offset, you see
a wrong-looking local time before saying yes, not after the invite goes out. Details that
can't be right, such as a missing field or an end before the start, are caught before
you're asked at all.

Over MCP there's no terminal to type `y` into, so the same gate is two tools: a preview
that creates nothing, then a create step that accepts only the newest preview, once.
[Why the gate is two tools](how-to/use-mcp.md#why-the-approval-gate-is-two-tools).

### Why code handles the dates

Models are good at reading "next Monday after lunch" and less reliable at date
arithmetic and UTC offsets. So the work is split:

- **The prompt** states today's date, your timezone, and its current UTC offset. The
  model has no other way to know what "tomorrow" means. (Over MCP, the `current_time`
  tool provides the same facts.)
- **The code** normalizes every time the model returns. A time without an offset is
  given your timezone instead of silently becoming UTC. Daylight saving is resolved by
  Python's `zoneinfo`: March 15, 2027 correctly becomes `-07:00` while December stays
  `-08:00`. The eval checks both.

## What lives where

| File | What it does | Provider-specific? |
|---|---|---|
| [`calendar_tools.py`](../calendar_tools.py) | The tool schema, the system prompt, date handling, the approval gate, the calendar backends | No: shared by both agents |
| [`claude_agent.py`](../claude_agent.py) | The agent loop on Claude's Messages API | Claude |
| [`gemini_agent.py`](../gemini_agent.py) | The same loop on Gemini's Interactions API | Gemini |
| [`mcp_server.py`](../mcp_server.py) | Path 2: the same tool as an MCP server | No: works with any MCP client |
| `.mcp.json` | Tells Claude Code how to start the MCP server | No |
| [`evals/cases.jsonl`](../evals/cases.jsonl) | The test requests and expected answers | No |
| [`evals/baseline_extractor.py`](../evals/baseline_extractor.py) | The non-AI baseline | No |
| [`evals/run_evals.py`](../evals/run_evals.py) | Runs and scores everything; never writes to a calendar | No |
| [`evals/dashboard.py`](../evals/dashboard.py) | Turns results into a dashboard page: charts, tokens, trends | No |
| [`evals/recordings/sample_run.json`](../evals/recordings/sample_run.json) | A saved Claude and Gemini run, to replay for free | No |
| [`progress.py`](../progress.py), [`kairos_progress.py`](../kairos_progress.py) | Track your milestones and award badges, locally | No |
| `mkdocs.yml`, `mkdocs_hooks.py`, `docs/` | This website: its menu, its home page badges, and every page | No |

Most of the code isn't tied to any provider. The two agent files are the only parts that
change between Claude and Gemini, and they're about 120 to 150 lines each, including
comments. Read them side by side to see how little changes. The README lists
[every file in the repo](../README.md#every-file-in-this-repo).

## Settings

Kairos reads its settings from environment variables. Only the first two are needed for
the Claude agent; everything else has a sensible default.

| Variable | Needed for | Default | Meaning |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Claude agent, Claude eval | (none) | Your key from console.anthropic.com |
| `CLAUDE_MODEL` | Claude agent, Claude eval | (none) | Which Claude model, e.g. `claude-opus-5-5` ([switch models](how-to/switch-models.md)) |
| `GEMINI_API_KEY` | Gemini agent, Gemini eval | (none) | Your key from aistudio.google.com (`GOOGLE_API_KEY` also works) |
| `GEMINI_MODEL` | Gemini | `gemini-3.6-flash` | Which Gemini model |
| `CALENDAR_BACKEND` | Everything | `mock` | `mock` prints the event; `google` writes to your [Google Calendar](how-to/use-google-calendar.md) |
| `TIMEZONE` | Everything | `America/Los_Angeles` | Your timezone, as `Region/City` ([change it](how-to/change-timezone.md)) |
| `GOOGLE_CREDENTIALS_FILE` | Google backend | `credentials.json` | OAuth client file |
| `GOOGLE_TOKEN_FILE` | Google backend | `token.json` | Saved sign-in token |
| `KAIROS_PROGRESS_FILE` | Progress and badges | `.kairos/progress.json` | Where your [progress](how-to/see-your-progress.md) is saved |

## Key ideas

**The model never runs your tool.** It only asks. Your code decides whether to run it,
which is what makes an approval gate possible.

**One tool schema, two wrappers.** The tool's arguments are described once, in JSON
Schema (`TOOL_PARAMETERS`). Each provider wants it wrapped slightly differently, so
`CLAUDE_TOOL` and `GEMINI_TOOL` each add their own few lines.

**The system prompt gives the model facts it can't know.** The model has no idea what
today's date is or which timezone you're in, so Kairos tells it. The prompt also sets a
*source boundary*: use only what's in the request, and never invent an email or link.

**Safe by default.** The mock calendar is the default, so nothing you try sends a real
invite. Switch to [Google Calendar](how-to/use-google-calendar.md) only when you're ready.

**Evals compare meaning, not text.** `3pm Eastern` and `12pm Pacific` are the same
meeting, so the eval compares moments in time, not strings.

## Where to start

1. [Quickstart](quickstart.md): clone the project, try the eval for free, then run the
   Claude agent.
2. Read [`claude_agent.py`](../claude_agent.py) top to bottom. It follows the six steps
   above.
3. [Run the eval](how-to/run-the-eval.md), read why each failure failed, and open the
   [eval dashboard](eval-dashboard.md).
4. [Add eval cases](how-to/add-eval-cases.md) of your own, especially ones you think
   might trip the model up.
5. [Use Kairos over MCP](how-to/use-mcp.md): Path 2, the same tool in Claude Code.
6. [Claude and Gemini side by side](PORTING.md): see what changes, and how little, on
   another LLM API.
7. [See your progress](how-to/see-your-progress.md): check which badges you've earned and
   what's next.

New to a term? The [Glossary](glossary.md) explains them in plain language. Stuck?
See [Troubleshooting](troubleshooting.md).
