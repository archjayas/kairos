# Friction log: MCP Python SDK

> *Notes from building Kairos; to be expanded.*

Things that slowed me down while building Kairos's MCP server ([`mcp_server.py`](../mcp_server.py),
[Path 2](how-to/use-mcp.md)).
SDK: `mcp` 2.3.0 (Python).

Format per entry: what I tried / what happened / what I expected / suggested fix.

---

## 1. Most examples online use an API that no longer exists

- **Tried:** `from mcp.server.fastmcp import FastMCP`, as most tutorials show.
- **Happened:** `ModuleNotFoundError`. In 2.x, `FastMCP` was renamed to `MCPServer`
  (`from mcp.server.mcpserver import MCPServer`). To its credit, the error message names
  the new import and links to the migration guide.
- **Expected:** The tutorials I found to match the current major version.
- **Suggested fix:** Keep the error message as it is (it's a model of how to break an
  API kindly), and put the version prominently at the top of examples.

## 2. Returning a `dict` doesn't give structured output

- **Tried:** A tool annotated `-> dict`, then reading `result.structured_content` in a
  client.
- **Happened:** `structured_content` was `None`. The dict arrived as JSON text in
  `result.content[0].text`. Structured output needs a more specific return type.
- **Expected:** A plain `dict` return to count as structured, or a warning that it doesn't.
- **Suggested fix:** Say in the `@tool()` docs which return types produce structured
  output, with a `dict` example.

## 3. An uncaught exception reaches the model as a generic message

- **Tried:** Letting `preview_event` raise `ValueError` on a bad time string.
- **Happened:** The client got `is_error: true` with only "Error executing tool
  preview_event", so the model had nothing to correct.
- **Expected:** The exception message passed through, or guidance on how to return one.
- **Suggested fix:** Document the pattern for model-readable tool errors. Kairos now
  catches the error and returns a message saying what's wrong and the expected format.

## 4. An MCP server can't ask the user "y/n"

- **Tried:** Reusing [Path 1](quickstart.md#4-schedule-a-meeting-with-claude)'s `input()` confirmation step in the server.
- **Happened:** Not possible: stdin and stdout carry the protocol. Any `print()` to
  stdout (including the mock calendar's) corrupts it.
- **Expected:** This to be called out early for people coming from command-line agents.
- **Suggested fix:** A "human approval in MCP servers" pattern in the docs. Kairos uses
  a preview tool plus a one-time confirmation id, and prints only to stderr.
