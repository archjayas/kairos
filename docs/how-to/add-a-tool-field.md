# Add a field to the tool

This guide adds an optional `room` field (a meeting room name) as an example. The same
steps work for any field. Because both agents share one schema, you change
[`calendar_tools.py`](../../calendar_tools.py) and both agents pick it up.

## 1. Add it to the schema

In `calendar_tools.py`, add a property to `TOOL_PARAMETERS["properties"]`:

```python
"room": {
    "type": "string",
    "description": "Meeting room name, only if the request names one.",
},
```

Leave it out of `required`. If you make a field required, the model has to supply it,
so it either asks every time or invents a value.

Write the description for the model, not for people. It's the only guidance the model
gets about when to fill the field. "Only if the request names one" discourages
made-up values.

## 2. Put it on the event

In `build_event_body()`, add a `room=None` parameter and decide where it goes. Google
Calendar has no room field for personal calendars, so add it to the description:

```python
if room:
    description_parts.append(f"Room: {room}")
```

Note that `location` already holds the Zoom link when there is one.

## 3. Pass it through

- Add `room=None` to `create_calendar_event()` and pass it to `build_event_body()`.
- In `run_tool_call()`, pass `room=args.get("room")`.
- For [Path 2](use-mcp.md), add a `room` parameter to `preview_event()` in
  [`mcp_server.py`](../../mcp_server.py), annotated with
  `Field(description=FIELD["room"])`, and include it in `args`. The description comes
  from the schema you edited in step 1, so you don't write it twice.

## 4. Show it at confirmation

In `format_event_summary()`, add a line so you can check the value before saying `y`:

```python
f"  Room:      {args.get('room') or '(none)'}",
```

## 5. Test it

- **By hand:** run either agent with *"... in the Redwood room"*, and once without a
  room, to check the model leaves it out.
- **In the [eval](run-the-eval.md):** add `"room"` to the expected fields of a few cases and a check in
  `score()` in `evals/run_evals.py`. To count invented rooms in the made-up-field rate,
  extend `made_up_fields()` as well.

Claude's tool uses `strict: true`, which requires `additionalProperties: false`.
`CLAUDE_TOOL` adds that for you, so you don't need to change it.

## Related

- [Run the eval](run-the-eval.md)
- [Add eval cases](add-eval-cases.md)
- [Use Kairos over MCP](use-mcp.md)
- [Overview: key ideas](../overview.md#key-ideas)
