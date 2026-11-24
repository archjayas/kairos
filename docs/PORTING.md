# Porting a tool-calling agent from Gemini to Claude

Kairos was first built on Gemini's Interactions API and then ported to Claude's
Messages API. This page compares the two, step by step, using the real code in
[`gemini_agent.py`](../gemini_agent.py) and [`claude_agent.py`](../claude_agent.py).
Everything the agents share (the tool schema, the system prompt, date handling, and
the confirmation step) lives in [`calendar_tools.py`](../calendar_tools.py) and didn't
need porting.

Versions: `google-genai` 2.14.0 and `anthropic` 2.13.0 (Python).

This page is about [Path 1](quickstart.md#4-schedule-a-meeting-with-claude), where you write the agent loop yourself.
Path 2 needs no porting at all: [the MCP server](how-to/use-mcp.md) works with any MCP
client.

## At a glance

| Step | Gemini (Interactions API) | Claude (Messages API) |
|---|---|---|
| Client | `genai.Client()` reads `GEMINI_API_KEY` | `anthropic.Anthropic()` reads `ANTHROPIC_API_KEY` |
| Call | `client.interactions.create(...)` | `client.messages.create(...)` |
| User input | `input=` | `messages=[{"role": "user", ...}]` |
| System prompt | `system_instruction=` | `system=` |
| Tool schema key | `parameters` | `input_schema` |
| "The model wants a tool" | A step with `type == "function_call"` in `interaction.steps` | `stop_reason == "tool_use"` and a `tool_use` block in `content` |
| Tool arguments | `function_call.arguments` | `tool_use.input` |
| Sending the result | `function_result` with `call_id`, `name`, `result` | `tool_result` with `tool_use_id`, `content` |
| Result format | The raw dict | A string (Kairos sends JSON) or content blocks |
| Conversation state | Kept by the server: pass `previous_interaction_id` | Kept by you: resend the whole conversation |
| Required output limit | Not required | `max_tokens` |

## 1. Defining the tool

Both APIs describe tool arguments with JSON Schema, so Kairos defines the schema once
(`TOOL_PARAMETERS`) and wraps it for each API:

```python
GEMINI_TOOL = {
    "type": "function",
    "name": TOOL_NAME,
    "description": TOOL_DESCRIPTION,
    "parameters": TOOL_PARAMETERS,
}

CLAUDE_TOOL = {
    "name": TOOL_NAME,
    "description": TOOL_DESCRIPTION,
    "input_schema": {**TOOL_PARAMETERS, "additionalProperties": False},
    "strict": True,
}
```

Differences:

- **Key name:** `parameters` vs. `input_schema`.
- **Type field:** Gemini's tool needs `"type": "function"`. Claude's custom tools don't need a type.
- **Strict mode:** `strict: True` makes Claude's arguments always match the schema. It
  requires `additionalProperties: false`, which is why the Claude wrapper adds it.

## 2. The system prompt

Both agents send the same prompt from `build_system_prompt()`: today's date, your
timezone, and the source boundary. Only the parameter name changes:

```python
# Gemini
client.interactions.create(model=..., system_instruction=system, tools=[GEMINI_TOOL], input=user_input)

# Claude
client.messages.create(model=..., max_tokens=16000, system=system, tools=[CLAUDE_TOOL],
                       messages=[{"role": "user", "content": user_input}])
```

Claude requires `max_tokens`, a ceiling on the reply's length.

## 3. Detecting a tool call

**Gemini** returns a list of steps. A tool call is one of them:

```python
function_call = next(
    (step for step in interaction.steps if step.type == "function_call"), None
)
```

**Claude** says why it stopped in `stop_reason`, and the tool call is a block in
`content`:

```python
if response.stop_reason == "tool_use":
    tool_use = next(b for b in response.content if b.type == "tool_use")
```

On current Claude models, `content` can also include `thinking` blocks before the
`tool_use` block, so always select blocks by `type`, never by position.

## 4. Sending the result back

This is where the two APIs differ most.

**Gemini keeps the conversation on its servers.** You send only the new message and
point at the earlier interaction:

```python
client.interactions.create(
    model=GEMINI_MODEL,
    previous_interaction_id=interaction.id,
    input=[{
        "type": "function_result",
        "call_id": function_call.id,
        "name": function_call.name,
        "result": result,              # the raw dict
    }],
)
```

**Claude's Messages API is stateless.** You resend the whole conversation: the user's
request, Claude's full reply (thinking blocks included), and your result:

```python
messages = [
    {"role": "user", "content": user_input},
    {"role": "assistant", "content": response.content},
    {"role": "user", "content": [{
        "type": "tool_result",
        "tool_use_id": tool_use.id,
        "content": json.dumps(result),  # a string
    }]},
]
client.messages.create(model=model, max_tokens=16000, system=system,
                       tools=[CLAUDE_TOOL], messages=messages)
```

Watch the result format. Gemini wanted the **raw dict**: a JSON string caused a 400
([Gemini friction log #16](FRICTION_LOG_GEMINI.md)). Claude's `tool_result.content`
takes a **string** or content blocks, so the dict is JSON-encoded. Code copied across
from one agent to the other breaks in both directions.

## 5. When the model doesn't call the tool

If a required detail is missing, both models reply with text instead.

| | Gemini | Claude |
|---|---|---|
| How you know | No `function_call` step | `stop_reason == "end_turn"` |
| Reading the text | `interaction.output_text` | Join the `text` blocks in `content` |
| Safety refusal | (not handled in Kairos) | `stop_reason == "refusal"` |

## 6. Error handling

| | Gemini agent | Claude agent |
|---|---|---|
| What Kairos does | Checks for the key up front, then prints any API error's message instead of a traceback | Checks for the key up front, then catches the SDK's typed exceptions and prints a readable message |
| Exceptions used | | `AuthenticationError`, `NotFoundError` (bad model id), `BadRequestError`, `RateLimitError`, `APIStatusError`, `APIConnectionError` |
| Retries | | The SDK retries rate limits and server errors automatically (2 retries by default) |
| Observed gotchas | A bad request shape returned `Invalid input received.` with no field named (#16). A 429 can mean a rate limit or depleted credits (#15). | |

## 7. Behavior differences seen in testing

These come from the same requests sent to both agents. They're observations from a
small number of runs, not benchmarks.

- **Extraction quality was the same.** On the [20-case eval](how-to/run-the-eval.md), both scored 20/20
  ([recording](../evals/recordings/sample_run.json)).
- **Timezones: same moment, different form.** For "3pm Eastern", Gemini returned
  `15:00-05:00`, and Claude converted it to `12:00-08:00`. Both are correct, which is
  why the eval compares moments, not strings.
- **Titles vary.** For the same request, Gemini wrote "Q1 Roadmap Meeting" and Claude
  wrote "Q1 Roadmap Review". The eval doesn't score titles.
- **Reporting the result.** On the mock calendar (which returns no event link), Claude
  said the event came from a test system and might not be on the calendar. Gemini said
  "I have scheduled the meeting." Both got the same result object.
- **Ambiguous dates.** For "next Friday", both picked Dec 11 in the eval. In a separate
  live run, Claude asked which Friday was meant instead.

## Porting checklist

- [ ] Rename `system_instruction` to `system`, and add `max_tokens`.
- [ ] Wrap the schema in `input_schema`; add `additionalProperties: false` if using
      `strict: true`.
- [ ] Replace "find the `function_call` step" with "check `stop_reason`, find the
      `tool_use` block".
- [ ] Replace `previous_interaction_id` with a `messages` list you keep and resend.
- [ ] Send the **whole** assistant `content` back, not just the text.
- [ ] Change the result from a raw dict to a string (`json.dumps`).
- [ ] Match `tool_use_id`, not `call_id`.
- [ ] Read text by block type; don't assume `content[0]` is text.
- [ ] Handle `refusal` as well as `end_turn`.
- [ ] Re-run the eval on both and compare.

