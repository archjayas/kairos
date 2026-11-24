# Glossary

Plain-language definitions of the terms used in Kairos's code and docs. Stuck on an
error instead? See [Troubleshooting](troubleshooting.md).

## Agents

**Path 1 and Path 2.** Kairos's two ways to use the same tool. In Path 1 you run an
agent loop you wrote yourself ([Quickstart](quickstart.md#4-schedule-a-meeting-with-claude)). In Path 2 an MCP client
like Claude Code runs the loop ([Use Kairos over MCP](how-to/use-mcp.md)). See
[Which path should I choose?](overview.md#which-path-should-i-choose)

**Agent.** A program where a language model decides what to do next, such as calling a
tool or asking a question, instead of following a fixed script.

**Tool (or function).** Something your code can do that the model can ask for. Kairos
has one tool, `create_calendar_event`. The model never runs the tool itself. It asks,
and your code decides whether to run it.

**Messages API / Interactions API.** The APIs Kairos calls: Claude's Messages API and
Gemini's Interactions API. Both support tool calling; [PORTING.md](PORTING.md) compares them.

**Tool calling (function calling).** The model replying with *"call this tool with
these arguments"* instead of plain text. Claude calls this *tool use*; Gemini calls it
*function calling*.

**Tool schema.** A description of a tool's arguments: their names, types, and which are
required. It's written in **JSON Schema**, a standard format for describing JSON data.
The model reads it to know what to fill in.

**Arguments.** The values the model fills in when it calls a tool, for example
`start_datetime` and `attendees`.

**System prompt.** Instructions sent with every request that set the model's behavior,
separate from what the user typed. Kairos's system prompt states today's date and your
timezone.

**`stop_reason`.** A field in Claude's response saying why it stopped. `tool_use` means
it wants to call a tool; `end_turn` means it replied with text, such as a question.

**`tool_result`.** The message your code sends back to Claude with the tool's output, so
it can write its final reply.

**Human approval gate (confirmation step).** A point where the program stops and asks
you before doing something with real effects. In Kairos it's `Create this event? (y/n)`.

**Mock backend.** A stand-in for the real calendar that prints the event instead of
creating it. It's the default, so you can experiment safely.

**Source boundary.** An instruction telling the model what it may treat as fact. Kairos
tells it to use only details from your request and never invent an email, link, or
agenda.

## MCP

**MCP (Model Context Protocol).** An open standard for connecting AI apps to tools and
data. You write a tool once as an MCP server, and any app that speaks MCP can use it.

**MCP server.** A program that offers tools to AI apps. Kairos's is [`mcp_server.py`](../mcp_server.py); see
[Use Kairos over MCP](how-to/use-mcp.md).

**MCP client.** The AI app that connects to servers and uses their tools, such as
Claude Code or Claude Desktop. In Path 2, the client runs the agent loop for you.

**stdio transport.** The client starts the server as a program and they exchange
messages over its standard input and output. That's why an MCP server must never print
to standard output.

**Tool annotations.** Hints a server gives about a tool, such as "read-only" or
"reaches the outside world", so a client can decide how carefully to treat it.

**Confirmation id.** In Kairos's MCP server, a one-time code returned by
`preview_event`. `create_event` only creates an event that was previewed with that code.

## Evals

**Eval (evaluation).** A repeatable test of how well a model does a task
([run Kairos's](how-to/run-the-eval.md)). Unlike a
normal test, a model can pass on one run and fail on the next.

**Extractor.** Anything that turns a request into event details. The eval scores three:
the no-AI baseline, Claude, and Gemini.

**Case.** One test input with its expected result. Kairos's cases are in
`evals/cases.jsonl`, one per line ([add your own](how-to/add-eval-cases.md)).

**Golden set.** A fixed collection of cases with known-correct answers. Kept fixed so
results can be compared over time.

**Check.** One thing scored for a case, such as "are the attendees right?" A case passes
only if all its checks pass.

**Pass rate.** The share of cases (or case runs) that passed.

**Baseline.** A simple, non-AI way of doing the same task, scored the same way. If the
model can't beat it on a field, the model isn't needed for that field. Kairos's is
[`evals/baseline_extractor.py`](../evals/baseline_extractor.py).

**Made-up-field rate.** The share of tool calls containing a detail the request didn't
support, like an email address that wasn't in it. Lower is better. It's this project's
measure of *hallucination*: a model stating something with no basis in its input.

**Ablation.** Running the eval with one thing removed (here, the source boundary) to
measure how much that thing helps.

**Held-out set.** Cases you don't look at while improving your prompt, used only to
check. It shows whether an improvement is real or just tuned to the cases you watched
([how to keep one](how-to/add-eval-cases.md#keep-a-held-out-set)).

**Flaky case.** A case that passes on some runs and fails on others. Find them with
`--repeat`.

**Saturated eval.** One where everything scores (nearly) 100%. It can no longer tell
models or prompts apart, so it needs harder cases.

**Replay.** Scoring saved model responses again, without calling the model. Free and
instant, so you can change scoring rules or cases and see the effect.

**LLM-as-judge.** Using a model to grade answers that can't be checked by exact
matching, such as "was that clarifying question helpful?" It's only trustworthy once
you've measured how often it agrees with people.

## Dates and setup

**RFC3339.** The standard date-time format the tool uses, for example
`2026-12-02T14:00:00-08:00`. The ending `-08:00` is the **UTC offset**: how many hours
the local time is behind (or ahead of) UTC.

**IANA timezone.** A timezone name like `America/Los_Angeles`. Unlike abbreviations such
as `PST`, it knows when daylight saving starts and ends. See
[Change your timezone](how-to/change-timezone.md).

**Environment variable.** A named setting, like `CLAUDE_MODEL` ([choose a model](how-to/switch-models.md)), that a program reads when
it starts. Used for API keys so they're never written into the code.

**Virtual environment (venv).** A private folder of Python packages for one project, so
projects don't interfere with each other.

**OAuth.** The "sign in with Google and allow access" flow. Kairos uses it only for the
real Google Calendar backend ([set it up](how-to/use-google-calendar.md)).
