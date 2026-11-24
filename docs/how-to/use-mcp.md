# Use Kairos over MCP (Path 2)

In [Path 1](../quickstart.md#4-schedule-a-meeting-with-claude) you run [`claude_agent.py`](../../claude_agent.py), an agent loop you wrote yourself. In Path 2 you
don't write a loop at all. [`mcp_server.py`](../../mcp_server.py) offers Kairos's calendar tools over the
**Model Context Protocol (MCP)**, and an MCP client, such as Claude Code or Claude
Desktop, runs the agent for you.

Both paths share [`calendar_tools.py`](../../calendar_tools.py): the same field descriptions, date handling,
summary, and mock calendar.

Not sure which path is for you? See
[Which path should I choose?](../overview.md#which-path-should-i-choose)

## What the server offers

| Tool | What it does | Changes anything? |
|---|---|---|
| `current_time` | Returns today's date, your timezone, and its UTC offset | No |
| `preview_event` | Checks the event details, returns a plain summary and a one-time `confirmation_id` | No |
| `create_event` | Creates a previewed event, given its `confirmation_id` | Yes (mock calendar by default) |

### Why the approval gate is two tools

Path 1 asks `Create this event? (y/n)` in the terminal. An MCP server can't do that:
its standard input and output carry the protocol messages, so there's no terminal to
type into. So the gate is split:

1. `preview_event` returns exactly what would be created, and creates nothing.
2. `create_event` only creates an event that was previewed, unchanged. Each
   `confirmation_id` works once, and only the newest preview can be created: if you ask
   for a change, the earlier preview is cancelled.

The model can't create anything you weren't shown. Whether you're asked in between is
up to the client: Claude Code asks permission before running a tool unless you've
allowed it. **Don't auto-allow `create_event`**, or the gate is gone.

### Why there's a `current_time` tool

In Path 1, today's date and your timezone go in the system prompt. An MCP server
doesn't control the client's prompt, so it offers the same facts as a tool, and its
instructions tell the client to call it before working out "tomorrow at 3pm". Set your
timezone with `TIMEZONE` in the server's `env` (see below, and
[Change your timezone](change-timezone.md)).

## Use it from Claude Code

The repo includes a `.mcp.json` file, so Claude Code finds the server when you open the
project:

```json
{
  "mcpServers": {
    "kairos": {
      "command": ".venv/bin/python",
      "args": ["mcp_server.py"],
      "env": { "CALENDAR_BACKEND": "mock" }
    }
  }
}
```

1. Finish the [Quickstart](../quickstart.md) setup, so `.venv` exists with the packages
   installed.
2. Start Claude Code in the repo folder (`claude`). The first time, it asks whether to
   trust the project's MCP server. Approve it.
3. Type `/mcp` to check that `kairos` is connected and shows three tools.
4. Ask: *"Schedule 45 minutes with alice@example.com tomorrow at 2pm to discuss Q3
   planning."*
5. Claude calls `current_time` and `preview_event`, then shows you the summary. Say
   yes, and approve the `create_event` call when asked.

**On Windows**, change `command` in `.mcp.json` to `.venv\\Scripts\\python.exe` (JSON needs each
backslash written twice). If Claude Code can't
start the server, use the absolute path to the Python inside `.venv` instead.

To use your own timezone, add it to `env`, for example
`"TIMEZONE": "Europe/London"`.

## Use it from Claude Desktop

Claude Desktop starts servers listed in its config file. Open it from **Settings →
Developer → Edit Config**, and add Kairos with **absolute paths** (Desktop doesn't
start in your project folder):

```json
{
  "mcpServers": {
    "kairos": {
      "command": "/absolute/path/to/kairos/.venv/bin/python",
      "args": ["/absolute/path/to/kairos/mcp_server.py"],
      "env": { "CALENDAR_BACKEND": "mock", "TIMEZONE": "America/Los_Angeles" }
    }
  }
}
```

Restart Claude Desktop, then ask it to schedule a meeting.

## Debug it with the MCP Inspector

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) is a browser UI
for calling a server's tools by hand, with no model involved. It needs Node.js:

```bash
npx @modelcontextprotocol/inspector .venv/bin/python mcp_server.py
```

Try `create_event` with a made-up id (it's refused), then `preview_event`, then
`create_event` with the id it returned (it works once).

## Things to know

- **Never `print()` to standard output in an MCP server.** Standard output carries the
  protocol, so a stray print corrupts it. Kairos's mock calendar prints to standard
  error for this reason.
- **Previews are kept in memory.** If the server restarts, old `confirmation_id`s stop
  working. Preview again.
- **The real calendar works here too, after one setup step.** Sign in to Google once
  outside MCP, by running `CALENDAR_BACKEND=google python claude_agent.py` from the repo
  folder (see [Use your real Google Calendar](use-google-calendar.md)). The sign-in
  can't happen inside the MCP server, because it needs your terminal and browser. Then
  set `"CALENDAR_BACKEND": "google"` in `env`, plus `GOOGLE_CREDENTIALS_FILE` and
  `GOOGLE_TOKEN_FILE` as **absolute paths** (Claude Desktop doesn't start in your
  project folder). `create_event` then sends real invites, so keep approving it by hand.

## Related

- [Two paths: with and without MCP](../overview.md#two-paths-with-and-without-mcp)
- [Path 1: run the agent yourself](../quickstart.md#4-schedule-a-meeting-with-claude)
- [Glossary: MCP terms](../glossary.md#mcp)
- [Troubleshooting: MCP](../troubleshooting.md#mcp-path-2)
- [Friction log: MCP SDK](../FRICTION_LOG_MCP.md)
