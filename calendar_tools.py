"""Shared calendar code used by both gemini_agent.py and claude_agent.py.

Contains:
  - the tool's parameter schema (defined once, wrapped per-API below)
  - the system prompt that anchors today's date and the user's timezone
  - create_calendar_event(), which writes to either a mock backend
    (default) or the real Google Calendar

Backend is chosen by the CALENDAR_BACKEND env var:
    CALENDAR_BACKEND=mock    (default) print the event, return a fake id
    CALENDAR_BACKEND=google  call the real Google Calendar API

Google Calendar's API doesn't have native Zoom integration (conferenceData
is reserved for Google Meet), so the Zoom link is just folded into the
event's description/location fields — the same way you'd paste it in
manually.
"""

import contextlib
import datetime
import json
import os
import sys
import uuid
from zoneinfo import ZoneInfo

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
DEFAULT_TIMEZONE = "America/Los_Angeles"
DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

TOOL_NAME = "create_calendar_event"
TOOL_DESCRIPTION = "Creates an event on the user's Google Calendar."

# JSON Schema for the tool's arguments. This is the single source of truth;
# each agent wraps it in its own API's tool format.
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "The event title."},
        "start_datetime": {
            "type": "string",
            "description": "Start time in RFC3339 format, e.g. 2026-07-27T15:00:00-07:00.",
        },
        "end_datetime": {
            "type": "string",
            "description": "End time in RFC3339 format. Default to a 30-minute meeting if no duration is given.",
        },
        "attendees": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Attendee email addresses.",
        },
        "agenda": {
            "type": "string",
            "description": "A brief agenda or description of what the meeting is about.",
        },
        "zoom_link": {
            "type": "string",
            "description": "Zoom meeting URL, if one was provided.",
        },
    },
    "required": ["summary", "start_datetime", "end_datetime", "attendees"],
}

# Gemini Interactions API tool format.
GEMINI_TOOL = {
    "type": "function",
    "name": TOOL_NAME,
    "description": TOOL_DESCRIPTION,
    "parameters": TOOL_PARAMETERS,
}

# Claude Messages API tool format: same schema, but under input_schema.
# strict=True makes Claude's arguments always validate against the schema,
# which requires additionalProperties: false.
CLAUDE_TOOL = {
    "name": TOOL_NAME,
    "description": TOOL_DESCRIPTION,
    "input_schema": {**TOOL_PARAMETERS, "additionalProperties": False},
    "strict": True,
}


def get_timezone_name():
    name = os.environ.get("TIMEZONE", DEFAULT_TIMEZONE)
    try:
        ZoneInfo(name)
    except Exception:  # unknown names raise different errors on different systems
        raise ValueError(
            f"TIMEZONE={name!r} isn't a timezone Kairos recognizes. "
            "Use a Region/City name, such as America/New_York."
        ) from None
    return name


def get_backend_name():
    return os.environ.get("CALENDAR_BACKEND", "mock").strip().lower()


# The source boundary: what the model may use as facts. Kept separate so the
# eval can measure what it's worth (run_evals.py --no-boundary).
SOURCE_BOUNDARY = (
    "Use only details stated in the request. Never invent attendee email "
    "addresses, links, or an agenda. If a required detail is missing, ask for "
    "it instead of guessing."
)


def build_system_prompt(now=None, timezone_name=None, source_boundary=True):
    """System prompt shared by both agents.

    The model has no other source for the current date or the user's
    timezone, so we state both explicitly. `now` can be passed in (the eval
    pins it) so results are repeatable.
    """
    timezone_name = timezone_name or get_timezone_name()
    tz = ZoneInfo(timezone_name)
    now = now.astimezone(tz) if now else datetime.datetime.now(tz)
    prompt = (
        f"Today is {now:%A, %Y-%m-%d}. The user's timezone is {timezone_name} "
        f"(current UTC offset {now:%z}). Resolve relative dates/times against this, "
        "and write start/end in RFC3339 with the UTC offset that applies on the "
        "event's date in that timezone (watch for daylight saving changes). "
        "Extract an agenda and zoom_link from the request if present."
    )
    if source_boundary:
        prompt += " " + SOURCE_BOUNDARY
    return prompt


def normalize_datetime(value, timezone_name):
    """Parse an RFC3339/ISO string; if it has no offset, assume the user's
    timezone. Returns an ISO string with an explicit offset.

    This is a code-side safety net so a missing offset never silently
    becomes UTC (or the server's local time).
    """
    parsed = datetime.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return parsed.isoformat()


def build_event_body(
    summary, start_datetime, end_datetime, attendees=None, agenda=None,
    zoom_link=None, timezone_name=None,
):
    """Build the Google Calendar event dict. Pure function — no I/O."""
    timezone_name = timezone_name or get_timezone_name()
    event = {
        "summary": summary,
        "start": {
            "dateTime": normalize_datetime(start_datetime, timezone_name),
            "timeZone": timezone_name,
        },
        "end": {
            "dateTime": normalize_datetime(end_datetime, timezone_name),
            "timeZone": timezone_name,
        },
    }
    start = datetime.datetime.fromisoformat(event["start"]["dateTime"])
    end = datetime.datetime.fromisoformat(event["end"]["dateTime"])
    if end <= start:
        raise ValueError("the end time isn't after the start time")
    if attendees:
        event["attendees"] = [{"email": a} for a in attendees]

    # No native Zoom support in the Calendar API, so the link goes in
    # both location (shows prominently in the event header) and
    # description (alongside the agenda text).
    description_parts = []
    if agenda:
        description_parts.append(agenda)
    if zoom_link:
        description_parts.append(f"Zoom link: {zoom_link}")
        event["location"] = zoom_link
    if description_parts:
        event["description"] = "\n\n".join(description_parts)
    return event


def get_calendar_service():
    # Imported here so the mock backend and tests don't need the Google
    # client libraries installed or any credentials on disk.
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    credentials_file = os.environ.get("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    token_file = os.environ.get("GOOGLE_TOKEN_FILE", "token.json")

    # Reuse a cached OAuth token if we have one; only prompt for consent
    # (via a browser) the first time or after the token expires without a
    # refresh token available.
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            # Sign-in prints a URL. Send it to stderr, so it can't corrupt the MCP
            # server's stdout if sign-in ever happens there.
            with contextlib.redirect_stdout(sys.stderr):
                creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())
        try:
            os.chmod(token_file, 0o600)  # the token grants calendar access: keep it private
        except OSError:
            pass
    return build("calendar", "v3", credentials=creds)


def create_calendar_event(
    summary, start_datetime, end_datetime, attendees=None, agenda=None, zoom_link=None
):
    event = build_event_body(
        summary, start_datetime, end_datetime, attendees, agenda, zoom_link
    )
    backend = get_backend_name()

    if backend == "mock":
        event_id = f"mock-{uuid.uuid4().hex[:12]}"
        # stderr, not stdout: the MCP server (mcp_server.py) uses stdout for
        # protocol messages, so any stray print there would break it. In a
        # terminal, stderr looks the same.
        print("\n[mock calendar] Would create this event (nothing sent to Google):", file=sys.stderr)
        print(json.dumps(event, indent=2), file=sys.stderr)
        return {"event_id": event_id, "htmlLink": None, "backend": "mock"}

    if backend == "google":
        service = get_calendar_service()
        created = service.events().insert(calendarId="primary", body=event).execute()
        return {"event_id": created["id"], "htmlLink": created["htmlLink"], "backend": "google"}

    raise ValueError(f"Unknown CALENDAR_BACKEND {backend!r}; use 'mock' or 'google'.")


def format_local_time(value, timezone_name):
    """Show a model-supplied time in the user's own timezone, e.g.
    'Tue Nov 24, 2026 2:00 PM PST'. Converting (rather than echoing the
    raw string) means a wrong offset from the model is visible to the user
    as a wrong local time before anything is created."""
    local = datetime.datetime.fromisoformat(
        normalize_datetime(value, timezone_name)
    ).astimezone(ZoneInfo(timezone_name))
    return local.strftime("%a %b %d, %Y %I:%M %p %Z").replace(" 0", " ")


def format_event_summary(args, timezone_name=None):
    """Plain-text summary of the event the model wants to create."""
    timezone_name = timezone_name or get_timezone_name()
    attendees = args.get("attendees") or []
    lines = [
        f"  Title:     {args.get('summary', '(none)')}",
        f"  Start:     {format_local_time(args['start_datetime'], timezone_name)}",
        f"  End:       {format_local_time(args['end_datetime'], timezone_name)}",
        f"  Attendees: {', '.join(attendees) if attendees else '(none)'}",
        f"  Agenda:    {args.get('agenda') or '(none)'}",
        f"  Zoom link: {args.get('zoom_link') or '(none)'}",
    ]
    return "\n".join(lines)


def confirm_event(args, ask=input):
    """Show the summary and ask for confirmation. Only 'y' proceeds.

    `ask` defaults to input(); tests pass a fake to simulate the user."""
    print("\nAbout to create this event:")
    print(format_event_summary(args))
    answer = ask("Create this event? (y/n) ")
    return answer.strip().lower() == "y"


def run_tool_call(args, ask=input):
    """Confirmation step + event creation, shared by both agents.

    Returns the dict to send back to the model as the tool result — either
    the created event, or a 'declined' status so the model can respond
    naturally instead of claiming the event was made."""
    fields = {
        "summary": args.get("summary"),
        "start_datetime": args.get("start_datetime"),
        "end_datetime": args.get("end_datetime"),
        "attendees": args.get("attendees"),
        "agenda": args.get("agenda"),
        "zoom_link": args.get("zoom_link"),
    }
    # Check the model's details before asking you, so a bad time or a missing
    # field becomes a clear message (sent back to the model) instead of a crash.
    try:
        if not (fields["summary"] and fields["start_datetime"] and fields["end_datetime"]):
            raise ValueError("the title, start, or end time is missing")
        build_event_body(**fields)
    except (ValueError, TypeError) as e:
        print(f"\nCan't use these event details: {e}. Nothing was created.")
        return {"status": "error",
                "message": f"The event details couldn't be used: {e}. No event was created."}

    if not confirm_event(args, ask=ask):
        return {
            "status": "declined",
            "message": "The user declined. No event was created.",
        }
    try:
        result = create_calendar_event(**fields)
    except Exception as e:  # e.g. Google Calendar rejecting the event
        print(f"\nThe calendar couldn't create the event: {e}")
        return {"status": "error", "message": f"The calendar rejected the event: {e}"}
    return {"status": "created", **result}
