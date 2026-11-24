# Friction log: Claude API (Messages API + tool use)

> *Notes from building Kairos; to be expanded.*

Things that slowed me down while porting the Gemini calendar agent to Claude.
SDK: `anthropic` 2.13.0 (Python). Model used for testing: set via `CLAUDE_MODEL` ([Switch models](how-to/switch-models.md)).
The code is [`claude_agent.py`](../claude_agent.py); the API comparison is in
[PORTING.md](PORTING.md).

Format per entry: what I tried / what happened / what I expected / suggested fix.

---

## 1. Choosing between the Tool Runner and a manual loop

- **Tried:** Looked up the "tool use loop" for Python to mirror the Gemini flow.
- **Happened:** The docs lead with the Tool Runner (`client.beta.messages.tool_runner`,
  `@beta_tool`) as the recommended path; the manual loop is presented as the fallback.
  The runner is a beta API, and it hides the request/response round-trip I wanted to
  show side by side with Gemini.
- **Expected:** A short "which one should I use?" table up front: runner for most apps,
  manual loop when you need a custom confirmation step, want no beta dependency, or are
  teaching the loop.
- **Suggested fix:** Add that decision table at the top of the tool-use page, and show
  that a human-approval step works in both (the runner's docs mention it in one line).

## 2. `strict: true` means the schema can't be shared verbatim

- **Tried:** Reusing the exact JSON Schema object from the Gemini tool, and turning on
  `strict: true` so Claude's arguments are guaranteed to validate.
- **Happened:** Strict mode requires `additionalProperties: false` on the schema, so
  the shared schema needs a Claude-specific tweak (`{**TOOL_PARAMETERS,
  "additionalProperties": False}`).
- **Expected:** Either the API to assume `additionalProperties: false` under strict mode,
  or a clear error message saying exactly what to add.
- **Suggested fix:** Put the `additionalProperties: false` requirement in the first
  strict-mode example, not just the reference text.

## 3. The response isn't just `[tool_use]`: thinking blocks come first

- **Tried:** Pulling Claude's text with `response.content[0].text`, the way many quick
  examples do.
- **Happened:** On current models thinking is on by default, so `content` can start
  with a `thinking` block (with empty text unless you opt into summaries). Indexing
  `[0]` gives the wrong block type.
- **Expected:** Examples that never rely on block position.
- **Suggested fix:** Have every quickstart filter by `block.type == "text"` / `"tool_use"`,
  and note that the whole `response.content` (thinking included) must be sent back as
  the assistant turn.

## 4. `tool_result` content is the opposite of Gemini's rule

- **Tried:** Sending the event result dict back as the tool result, as the Gemini agent
  does.
- **Happened:** Claude's `tool_result.content` takes a string or a list of content
  blocks, so the dict has to be `json.dumps()`-ed. Gemini's Interactions API is the
  reverse: it wants the raw dict, and a JSON string caused problems (see the Gemini log).
- **Expected:** Not friction in Claude's API on its own, but a sharp edge when porting.
- **Suggested fix:** A "coming from other providers" note on the tool-use page listing
  the result format difference.

## 5. No default model, so you need to know a current id

- **Tried:** Following the plan's rule of no hard-coded model (`CLAUDE_MODEL` from env).
- **Happened:** Fine once set, but a newcomer has to find a current model id first, and
  ids from older tutorials may be retired.
- **Expected:** An easy way to discover a valid id.
- **Suggested fix:** Point newcomers at `client.models.list()` in the quickstart so they
  can print the available ids.

---
