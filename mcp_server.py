"""Path 2: expose the Kairos calendar tool over MCP (Model Context Protocol).

In Path 1 (claude_agent.py) you write the agent loop yourself. Here you don't:
an MCP client such as Claude Code or Claude Desktop runs the loop, and this
server only offers tools. Everything else (dates, the summary, the calendar
backends) comes from the same calendar_tools.py.

Tools:
    current_time    today's date, timezone, and UTC offset (read-only)
    preview_event   step 1 of the approval gate (read-only)
    create_event    step 2 of the approval gate

Why two tools for one action?
  The Path 1 agent asks "Create this event? (y/n)" with input(). An MCP server
  can't: stdin/stdout carry the protocol, so there's no terminal to type into.
  So the approval gate is split in two:
    1. preview_event   checks the details and returns a plain summary plus a
                       one-time confirmation_id. Nothing is created.
    2. create_event    creates ONLY an event that was previewed, unchanged,
                       using that confirmation_id. Each id works once.
  The model can't create anything the user wasn't shown. Whether the user is
  actually asked in between is up to the client: Claude Code asks before
  running a tool unless you've allowed it, so don't auto-allow create_event.

Run it directly to check it starts (it then waits for a client):
    python mcp_server.py
Normally a client starts it for you; see docs/how-to/use-mcp.md.
"""

import datetime
import uuid
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import Field

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from kairos_progress import record
from calendar_tools import (
    SOURCE_BOUNDARY,
    TOOL_PARAMETERS,
    build_event_body,
    create_calendar_event,
    format_event_summary,
    get_backend_name,
    get_timezone_name,
)

server = MCPServer(
    "kairos",
    instructions=(
        "To schedule a meeting: call current_time first so relative dates like "
        "'tomorrow' resolve in the user's timezone, then call preview_event, show "
        "the user the summary it returns, and call create_event only after the "
        "user explicitly says yes. " + SOURCE_BOUNDARY
    ),
)

# Argument descriptions come from the shared schema, so the MCP tool and the
# Path 1 agents describe every field to the model in exactly the same words.
FIELD = {name: spec["description"] for name, spec in TOOL_PARAMETERS["properties"].items()}

# Previewed events waiting for approval: confirmation_id -> tool arguments.
# Kept in memory, so they're lost if the server restarts. That's fine: the
# user just previews again.
pending = {}


@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def current_time() -> dict:
    """Get the user's current date, time, timezone, and UTC offset. Call this before
    turning a relative date like 'tomorrow at 3pm' into start/end times."""
    # In Path 1 this goes in the system prompt. An MCP server doesn't control
    # the client's prompt, so it offers the same facts as a tool instead.
    try:
        timezone_name = get_timezone_name()
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    now = datetime.datetime.now(ZoneInfo(timezone_name))
    return {
        "now": now.isoformat(timespec="minutes"),
        "weekday": now.strftime("%A"),
        "timezone": timezone_name,
        "utc_offset": now.strftime("%z"),
        "note": "Use the UTC offset that applies on the event's date (daylight saving).",
    }


@server.tool(annotations=ToolAnnotations(read_only_hint=True))
def preview_event(
    summary: Annotated[str, Field(description=FIELD["summary"])],
    start_datetime: Annotated[str, Field(description=FIELD["start_datetime"])],
    end_datetime: Annotated[str, Field(description=FIELD["end_datetime"])],
    attendees: Annotated[list[str], Field(description=FIELD["attendees"])],
    agenda: Annotated[str | None, Field(description=FIELD["agenda"])] = None,
    zoom_link: Annotated[str | None, Field(description=FIELD["zoom_link"])] = None,
) -> dict:
    """Step 1 of 2: check a calendar event and get a summary to show the user.
    Creates nothing. Returns a confirmation_id for create_event."""
    args = {
        "summary": summary,
        "start_datetime": start_datetime,
        "end_datetime": end_datetime,
        "attendees": attendees,
        "agenda": agenda,
        "zoom_link": zoom_link,
    }
    try:
        build_event_body(**args)  # parses and normalizes the times
    except ValueError as e:
        # A specific message lets the model fix its arguments and try again;
        # an uncaught exception would only say "Error executing tool".
        return {
            "status": "error",
            "message": f"Couldn't read the times ({e}). Use RFC3339, "
                       "e.g. 2026-12-02T15:00:00-08:00.",
        }

    confirmation_id = uuid.uuid4().hex[:8]
    # Only the newest preview can be created. If the user asked for changes, an
    # older preview they didn't approve can't be created by mistake.
    pending.clear()
    pending[confirmation_id] = args
    return {
        "confirmation_id": confirmation_id,
        "summary": format_event_summary(args),
        "calendar": get_backend_name(),
        "next_step": (
            "Show this summary to the user and ask whether to create the event. "
            "Call create_event with this confirmation_id only if they say yes."
        ),
    }


# Annotations are hints for the client: this tool adds (doesn't delete or
# overwrite) data, calling it twice makes two events, and it reaches the
# outside world (invites go to real people on the Google backend).
@server.tool(annotations=ToolAnnotations(
    destructive_hint=False, idempotent_hint=False, open_world_hint=True))
def create_event(
    confirmation_id: Annotated[str, Field(description="The id returned by preview_event.")],
) -> dict:
    """Step 2 of 2: create a previewed event. Only call this after the user has seen
    the preview_event summary and explicitly approved it."""
    args = pending.pop(confirmation_id, None)
    if args is None:
        return {
            "status": "error",
            "message": "Unknown, already-used, or replaced confirmation_id. Only the newest preview can be created: call preview_event again.",
        }
    try:
        result = create_calendar_event(**args)
    except Exception as e:  # e.g. Google Calendar rejecting the event
        return {"status": "error", "message": f"The calendar couldn't create the event: {e}"}
    record("mcp_event")  # learner progress; prints to stderr only
    return {"status": "created", "event": format_event_summary(args), **result}


if __name__ == "__main__":
    server.run()  # stdio transport: the client talks to us over stdin/stdout
