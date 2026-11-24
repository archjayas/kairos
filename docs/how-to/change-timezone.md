# Change your timezone

Relative times like "tomorrow at 3pm" are resolved in the timezone set by `TIMEZONE`.
The default is `America/Los_Angeles`.

## Set it

Use an IANA timezone name: `Region/City`, not an abbreviation.

```bash
export TIMEZONE=Europe/London
python claude_agent.py
```

| Use | Not |
|---|---|
| `America/New_York` | `EST`, `Eastern` |
| `Europe/Berlin` | `CET` |
| `Asia/Kolkata` | `IST` |
| `UTC` | `GMT+0` |

Abbreviations are a trap: some, like `PST`, are rejected, but others, like `EST`, load
and then ignore daylight saving, so your times are an hour off for half the year.
Always use `Region/City`. To find yours, run `python -c "import zoneinfo; print(sorted(zoneinfo.available_timezones()))"`.

## What the setting changes

- **The system prompt** tells the model today's date in that timezone and its current
  UTC offset.
- **Times without an offset** that the model returns are interpreted in that timezone.
- **The confirmation summary** shows times converted to that timezone, so you can check
  them before saying `y`.
- **[Google Calendar](use-google-calendar.md) events** are created with that `timeZone`.

## Meetings in another timezone

You don't need to change `TIMEZONE` for a one-off. Say it in the request: *"3pm Eastern
with sam@example.com."* The model returns a time with the Eastern offset, and the
summary shows it in your own timezone (12:00 PM if you're on Pacific time).

## Daylight saving

Offsets are calculated for the event's date, not today's. In `America/Los_Angeles`, a
meeting on March 15, 2027 gets `-07:00` even if you schedule it in December, when the
offset is `-08:00`. The eval includes a case that checks this.

## Related

- [Troubleshooting: dates and times](../troubleshooting.md#dates-and-times)
- [Use Kairos over MCP](use-mcp.md) (set `TIMEZONE` in the server's `env`)
- [Use your real Google Calendar](use-google-calendar.md)
