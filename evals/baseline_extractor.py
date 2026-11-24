"""Non-LLM baseline: regex + standard library only.

The point is to measure where the LLM actually earns its cost. If a field
is extracted just as well by a few regular expressions, code should own it.

Written for common phrasings, not tuned to individual eval cases. It
deliberately has no knowledge of other timezones or vague dates.
"""

import datetime
import re
from zoneinfo import ZoneInfo

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ZOOM = re.compile(r"https?://[\w.-]*zoom\.us/[^\s,;)]+")
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4}
TIME_12H = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.I)
TIME_24H = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
AGENDA = re.compile(
    r"\b(?:agenda:|to discuss|discuss|about|regarding|to go over|to review|to plan)\s+(.+?)(?:\.|$|\bzoom\b)",
    re.I,
)


def find_date(text, today):
    lower = text.lower()
    if "tomorrow" in lower:
        return today + datetime.timedelta(days=1)
    match = re.search(r"\bin (\d+|two|three|four) days\b", lower)
    if match:
        n = match.group(1)
        return today + datetime.timedelta(days=int(n) if n.isdigit() else NUMBER_WORDS[n])
    match = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.? (\d{1,2})(?:,? (\d{4}))?", lower)
    if match:
        year = int(match.group(3)) if match.group(3) else today.year
        date = datetime.date(year, MONTHS[match.group(1)], int(match.group(2)))
        if date < today and not match.group(3):
            date = date.replace(year=year + 1)
        return date
    for i, name in enumerate(WEEKDAYS):
        if name in lower:  # next occurrence strictly after today
            days_ahead = (i - today.weekday() - 1) % 7 + 1
            return today + datetime.timedelta(days=days_ahead)
    return None


def find_times(text):
    """Return a list of (hour, minute) in order of appearance."""
    found = []
    for m in TIME_12H.finditer(text):
        hour = int(m.group(1)) % 12 + (12 if m.group(3).lower() == "pm" else 0)
        found.append((m.start(), hour, int(m.group(2) or 0)))
    for m in TIME_24H.finditer(text):
        if not any(abs(m.start() - pos) < 3 for pos, _, _ in found):
            found.append((m.start(), int(m.group(1)), int(m.group(2))))
    if re.search(r"\bnoon\b", text, re.I):
        found.append((text.lower().index("noon"), 12, 0))
    return [(h, mi) for _, h, mi in sorted(found)]


def find_duration_minutes(text):
    lower = text.lower()
    match = re.search(r"\b(\d+|an?|one|two|three|four)[ -](hours?|hrs?|minutes?|mins?|min)\b", lower)
    if not match:
        return None
    n = match.group(1)
    amount = int(n) if n.isdigit() else NUMBER_WORDS[n]
    return amount * 60 if match.group(2).startswith("h") else amount


def extract(request, now, timezone_name):
    """Return (args dict or None, explanation). Same arg shape as the tool."""
    tz = ZoneInfo(timezone_name)
    attendees = EMAIL.findall(request)
    date = find_date(request, now.date())
    times = find_times(request)
    if not (attendees and date and times):
        return None, "baseline: missing email, date, or time"

    start = datetime.datetime.combine(date, datetime.time(*times[0]), tz)
    if len(times) >= 2 and re.search(r"\b(to|until|-)\b", request):
        end = datetime.datetime.combine(date, datetime.time(*times[1]), tz)
    else:
        end = start + datetime.timedelta(minutes=find_duration_minutes(request) or 30)

    args = {
        "summary": "Meeting",
        "start_datetime": start.isoformat(),
        "end_datetime": end.isoformat(),
        "attendees": attendees,
    }
    zoom = ZOOM.search(request)
    if zoom:
        args["zoom_link"] = zoom.group(0)
    agenda = AGENDA.search(request)
    if agenda:
        args["agenda"] = agenda.group(1).strip()
    return args, "baseline: extracted"
