# Release notes

Kairos follows [semantic versioning](https://semver.org): the first number changes for
breaking changes, the second for new features, the third for fixes.

## 0.1.0 (Nov 23, 2026)

The first public version.

### Path 1: build the agent yourself

- A Claude agent ([`claude_agent.py`](../claude_agent.py)) on the Messages API with tool
  use. Try it in the [Quickstart](quickstart.md).
- The same agent on Gemini ([`gemini_agent.py`](../gemini_agent.py)), to show how an agent moves between
  LLM APIs ([compare them](PORTING.md)).
- A human approval step: nothing is created until you type `y`.
- Dates and timezones handled in code, including daylight saving.
- A mock calendar by default; [Google Calendar](how-to/use-google-calendar.md) when you opt in.

### Path 2: use the tool over MCP

- An MCP server ([`mcp_server.py`](../mcp_server.py)) with `current_time`, `preview_event`, and
  `create_event`, usable from Claude Code or Claude Desktop ([how](how-to/use-mcp.md)).
- A two-step approval gate: an event can only be created after it's been previewed,
  unchanged, with a one-time confirmation id.

### Evals

- 20 [test cases](how-to/add-eval-cases.md), scored field by field
  ([run the eval](how-to/run-the-eval.md)), with a made-up-field rate.
- A no-AI [baseline](../evals/baseline_extractor.py) scored the same way, to show where the LLM earns its cost.
- `--repeat` to find flaky cases, `--no-boundary` to measure the source-boundary
  instruction, and `--replay` to score a saved run with no API key.

### Dashboard and progress

- An [eval dashboard](eval-dashboard.md) (`evals/dashboard.py`): pass rate, accuracy per
  check, made-up fields, token usage, every case, and pass rate over time.
- Token usage recorded for every live eval run.
- [Progress and badges](progress.md): Kairos records your milestones locally and awards
  five badges (`python progress.py`).

### Docs

- This website, an [overview](overview.md), a [quickstart](quickstart.md), ten how-to
  guides, a [glossary](glossary.md), [troubleshooting](troubleshooting.md), a
  [Claude/Gemini comparison](PORTING.md), and friction logs for three APIs.

### Known limits

- The 20 cases are cleanly written, and both models currently score 100%, so the eval
  can no longer tell them apart. Harder cases are next.
- The agents handle one tool call per reply, so a request for two meetings books only
  one. Ask for the second separately.
