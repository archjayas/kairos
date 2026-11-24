# Bundle Kairos as a Claude Code plugin

A **Claude Code plugin** packages tools and instructions so anyone can install them
with two commands. This guide bundles Kairos's MCP server ([Path 2](use-mcp.md)), a
`/schedule-meeting` command, and a skill into one plugin, then shows how to use it in
the terminal and in VS Code.

This is an advanced guide. Do [Use Kairos over MCP](use-mcp.md) first: a plugin is
mostly that same MCP server, packaged.

## What's in a plugin

```text
kairos/
  .claude-plugin/
    plugin.json            # name, version, description
    marketplace.json       # lets this folder be installed as a plugin source
  .mcp.json                # the MCP server the plugin starts (already in the repo)
  commands/
    schedule-meeting.md    # the /schedule-meeting slash command
  skills/
    kairos-scheduling/
      SKILL.md             # when and how Claude should use the Kairos tools
  mcp_server.py, calendar_tools.py, ...   # the code the server runs
```

| Piece | What it adds |
|---|---|
| **MCP server** | The tools: `current_time`, `preview_event`, `create_event` |
| **Command** | A slash command that runs a fixed prompt, like `/schedule-meeting` |
| **Skill** | Instructions Claude loads when a task matches, for example "always preview first" |

## 1. Describe the plugin

Create `.claude-plugin/plugin.json`:

```json
{
  "name": "kairos",
  "version": "0.1.0",
  "description": "Schedule meetings from plain English, with a preview-then-confirm approval gate.",
  "author": { "name": "Your Name" },
  "keywords": ["calendar", "mcp", "agent", "learning"]
}
```

And `.claude-plugin/marketplace.json`, so the folder can be installed directly:

```json
{
  "name": "kairos-marketplace",
  "owner": { "name": "Your Name" },
  "plugins": [
    { "name": "kairos", "source": "./", "description": "Kairos calendar tools over MCP." }
  ]
}
```

## 2. Point the MCP server at the plugin's folder

When a plugin is installed, Claude Code copies it to its own plugin folder.
`${CLAUDE_PLUGIN_ROOT}` is that folder's path, so use it instead of relative paths.

The server also needs Python with the `mcp` package. The simplest way to give an
installed plugin its own packages is [uv](https://docs.astral.sh/uv/), which installs
them on the fly. Replace `.mcp.json` with:

```json
{
  "mcpServers": {
    "kairos": {
      "command": "uv",
      "args": ["run", "--with", "mcp==2.3.0", "${CLAUDE_PLUGIN_ROOT}/mcp_server.py"],
      "env": { "CALENDAR_BACKEND": "mock" }
    }
  }
}
```

If you'd rather not use uv, point `command` at a Python that already has the packages,
using an absolute path such as `/Users/you/kairos/.venv/bin/python`. That only works on
your own computer.

!!! note "This changes Path 2's setup"
    The repo's current `.mcp.json` uses `.venv/bin/python`, which works when you open
    the project folder in Claude Code. The plugin version above works from anywhere,
    but needs uv. Pick one, and update [Use Kairos over MCP](use-mcp.md) to match.

## 3. Add a slash command

Create `commands/schedule-meeting.md`:

```markdown
---
description: Schedule a meeting from a plain-English request, with a preview first
allowed-tools: mcp__plugin_kairos_kairos__current_time, mcp__plugin_kairos_kairos__preview_event
---

Schedule this meeting: $ARGUMENTS

1. Call `current_time` to get today's date and the user's timezone.
2. Call `preview_event` with the details from the request. Use only details the user
   gave; if an attendee email is missing, ask for it instead of guessing.
3. Show the user the summary from `preview_event`, word for word, and ask whether to
   create the event.
4. Only if they say yes, call `create_event` with the `confirmation_id`.
```

`allowed-tools` lets the command run the two **read-only** tools without asking.
`create_event` is deliberately left out, so Claude Code still asks you before anything
is created. That keeps the approval gate.

Tool names follow the pattern `mcp__plugin_<plugin>_<server>__<tool>`; here both the
plugin and the server are called `kairos`.

## 4. Add a skill

A skill is guidance Claude loads automatically when a task matches its description, so
it applies even without the slash command. Create `skills/kairos-scheduling/SKILL.md`:

```markdown
---
name: kairos-scheduling
description: Use when the user asks to schedule, book, or set up a meeting or calendar event.
---

When scheduling with the Kairos tools:

- Call `current_time` before turning "tomorrow" or "next Friday" into dates.
- If "next Friday" or a similar phrase could mean two dates, ask which one.
- Always call `preview_event` first and show its summary. Never call `create_event`
  until the user has seen the summary and said yes.
- Never invent attendee emails, links, or agendas.
```

## 5. Install it and try it

In Claude Code, from any folder:

```text
/plugin marketplace add /absolute/path/to/kairos
/plugin install kairos@kairos-marketplace
```

The first command registers the folder as a plugin source; the second installs the
plugin from it. Restart Claude Code, then:

1. Type `/mcp`: `kairos` should be connected, with three tools.
2. Try `/schedule-meeting 30 minutes with alice@example.com tomorrow at 2pm about the launch`.
3. Approve `create_event` when asked.

An installed plugin runs from Claude Code's own copy, so its progress is saved there,
not in your repo. To count it toward your [Connector badge](../progress.md), add
`"KAIROS_PROGRESS_FILE": "/absolute/path/to/kairos/.kairos/progress.json"` to the
server's `env` in `.mcp.json`.

To share it, push the repo to GitHub. Others install it with
`/plugin marketplace add archjayas/kairos`, then the same `/plugin install` line.

## Use it in VS Code

**Claude Code's VS Code extension uses the same plugins.** Once you've installed the
plugin in Claude Code, open the Claude Code panel in VS Code and the `kairos` tools,
`/schedule-meeting`, and the skill are available there too. You don't need a separate
VS Code extension.

**To use the server with VS Code's own AI features** (for example, agent mode in
Copilot Chat) instead of Claude Code, VS Code can start MCP servers listed in
`.vscode/mcp.json`:

```json
{
  "servers": {
    "kairos": {
      "type": "stdio",
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["${workspaceFolder}/mcp_server.py"],
      "env": { "CALENDAR_BACKEND": "mock" }
    }
  }
}
```

That gives VS Code the tools only. The slash command and skill are Claude Code
features.

**A real VS Code extension** (a `.vsix` on the Visual Studio Marketplace) is a separate,
larger project: an extension written in TypeScript that registers the MCP server with
VS Code. Start from VS Code's documentation on MCP servers in extensions if you want to
go that far. For Kairos, the plugin above covers both the terminal and VS Code.

## Check before you share

- [ ] `create_event` is **not** in any command's `allowed-tools`.
- [ ] `.mcp.json` sets `CALENDAR_BACKEND` to `mock`, so new users can't send real invites by accident.
- [ ] No `credentials.json`, `token.json`, or `.env` in the plugin folder.
- [ ] `/mcp` shows three tools after a fresh install.

## Related

- [Use Kairos over MCP](use-mcp.md)
- [Troubleshooting: MCP](../troubleshooting.md#mcp-path-2)
- [Glossary: MCP terms](../glossary.md#mcp)
- [Friction log: MCP SDK](../FRICTION_LOG_MCP.md)
