# Friction log: Gemini API

> *Notes from building Kairos; to be expanded.*

Things that slowed me down while getting started with the Gemini API and building
the first version of Kairos on it. SDK: `google-genai` 2.14.0 (Python), Interactions
API, model `gemini-3.6-flash`.

Format per entry: what I tried / what happened / what I expected / suggested fix.
Entry numbers match my original log, so references elsewhere (for example in
[`gemini_agent.py`](../gemini_agent.py)) stay valid. For how the API
compares with Claude's, see [PORTING.md](PORTING.md).

---

## Function calling (the Kairos loop)

### 16. Sending a function result back returns a 400 with no field-level detail

- **Tried:** After Gemini called `create_calendar_event`, sending the result on a
  follow-up `create()` call with
  `input=[{"type": "function_result", "call_id": ..., "result": json.dumps(result)}]`.
- **Happened:** `Error code: 400 - {'error': {'message': 'Invalid input received.',
  'code': 'invalid_request'}}`, with no hint of which field was wrong. There was no
  worked example of the function-calling round trip to check against: only the
  managed-agent and plain-text paths had samples.
- **Expected:** Either an error naming the bad field, or a documented example of a
  complete function-call round trip.
- **What fixed it:** Sending `result` as the raw dict instead of a `json.dumps()`
  string, and adding the optional `name` field with the function's name. The type stub
  accepts a `str`, but it's listed last in the union, and it isn't what the backend
  wants. Both changes were made together, so which one mattered (or both) isn't
  confirmed.
- **Suggested fix:** A function-calling round-trip sample in the Interactions docs,
  and field-level detail in `invalid_request` errors.

### 8. Different parameter names in the Models API and the Interactions API

- **Tried:** Moving code between `generate_content()` and `interactions.create()`.
- **Happened:** One takes `contents=`, the other takes `input=`. Nothing flags the
  difference, so it's an easy copy-paste mistake.
- **Expected:** Consistent naming, or a migration note.
- **Suggested fix:** A short "coming from `generate_content`" table on the Interactions
  page.

### 9. The response JSON in the docs doesn't connect to the sample code

- **Tried:** Matching the documented response to what the code prints.
- **Happened:** The docs show the full `interaction` object (`id`, `status`, `usage`,
  `steps`, ...), but the sample prints `interaction.output_text`, a derived field. When
  the wording of a reply changed, it looked like a bug rather than normal model
  variation read through a convenience property.
- **Expected:** The sample to say where `output_text` comes from.
- **Suggested fix:** One sentence linking `output_text` to the `steps` it summarizes.

### 5. Reasoning models return parts the sample code doesn't expect

- **Tried:** The quickstart sample with `gemini-3.6-flash`.
- **Happened:** The model returns a `thought_signature` part alongside the text, and
  the SDK warns when `.text` drops it. The sample predates this and doesn't explain it.
- **Expected:** Samples that match current models' output.
- **Suggested fix:** Update the sample, or explain the warning next to it.

### 15. A 429 can mean two different things

- **Tried:** Following the quickstart's "watch for a 429" guidance, which describes
  it as the free-tier rate limit.
- **Happened:** A run returned 429 with "Your prepayment credits are depleted": a
  billing problem that waiting won't fix. Same status code, different cause and fix.
  The runtime error message was more helpful than the docs: it named the cause and
  linked to where to fix it.
- **Expected:** The docs to cover both meanings.
- **Suggested fix:** List both 429 causes and how to tell them apart from the message.

## Setup

### 1. The API key export silently disappears

- **Tried:** `export GEMINI_API_KEY=...` as the docs say.
- **Happened:** It only lasts for the current terminal. A new window has no key, with
  no warning. (This came up again while building Kairos: an editor opened before the
  export can't see the key either.)
- **Expected:** The docs to say how long the export lasts, and how to make it stick.
- **Suggested fix:** One line on adding it to the shell profile (`~/.zshrc`).

### 2. No "did it work?" check for the key

- **Tried:** Confirming the key was set.
- **Happened:** Nothing suggests a check. Typing `echo GEMINI_API_KEY` without the `$`
  prints the variable's name, which looks exactly like "it's not set": a false
  negative for anyone new to the shell.
- **Expected:** A documented check.
- **Suggested fix:** Suggest a check that doesn't print the key, such as
  `[ -n "$GEMINI_API_KEY" ] && echo set`.

### 3. No minimum Python version stated

- **Tried:** `pip3 install -U google-genai` on Python 3.9.
- **Happened:** The install succeeded silently. The problem only appeared later as a
  runtime `FutureWarning` that Python 3.9 is past end of life.
- **Expected:** The minimum version stated before install.
- **Suggested fix:** Put the supported Python versions at the top of the quickstart.

### 7. Version checks can mislead from an old environment

- **Tried:** `pip index versions google-genai` to find the latest release.
- **Happened:** It reported `1.47.0` as latest: true only for the Python 3.9
  environment it ran in, because pip hides versions that need a newer Python. That
  caused an extended false alarm that the Interactions API didn't exist.
- **Expected:** A way to see the true latest version, or a note about this.
- **Suggested fix:** A troubleshooting entry: "Can't find the Interactions API? Check
  your Python version first."

### 4. Unexplained `NotOpenSSLWarning` on macOS

- **Tried:** Running the quickstart with the Python that ships with macOS.
- **Happened:** macOS's Python uses LibreSSL instead of OpenSSL, and `urllib3` v2
  warns about it.
- **Expected:** The quickstart to anticipate the most common Mac setup.
- **Suggested fix:** A note recommending a python.org or Homebrew Python on macOS.

### 6. Model names and APIs move faster than the docs

- **Tried:** Following a single snapshot of the docs.
- **Happened:** During this work, the quickstart model changed from `gemini-2.5-flash`
  to `gemini-3.6-flash`, and a new API (Interactions) appeared. Any doc snapshot, even
  one fetched live, needed checking against the installed package.
- **Expected:** Docs and the installed SDK to agree.
- **Suggested fix:** Show the SDK version each page was written for.

## Beyond Kairos: managed agents

These came from the managed-agents quickstart, which Kairos doesn't use.

- **10. No latency warning for remote sandboxes.** `environment="remote"` starts a
  fresh sandbox VM per call, which is much slower than a text completion. The docs
  don't say this call behaves differently in kind.
- **11. File retrieval is easy to miss.** The "Download files from the environment"
  section exists, further down the page ("no SDK method yet"), but working top to
  bottom you hit a dead end after creating a file. A forward reference where files are
  first created would save the detour.
- **12. "Download the file" downloads the whole sandbox.** The endpoint returns a tar
  archive of the entire environment, not one file.
- **13. The download endpoint isn't in the SDK.** You build the URL, the
  `x-goog-api-key` header, and the `alt=media` parameter by hand with `requests`. A
  real SDK coverage gap, not only a docs gap.
- **14. The docs' download sample fails on Python 3.12+.** Unfiltered
  `tarfile.extractall()` tries to recreate device nodes and fails with
  `PermissionError` on macOS. The obvious fix, `filter="data"`, is too strict for this
  archive (`SpecialFileError` on overlay artifacts). `filter="tar"` works. It took
  three tries, with no guidance in the docs.
