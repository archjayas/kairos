# Friction log: Claude API quickstart and Messages API guide (Python)

Notes from following Anthropic's documentation site while trying the Messages API, before
building Kairos. Rewritten from my own notes; the examples are from the docs as they were
on the date below.

**Date:** 2026-11-25
**Goal:** Make a first API call by following the docs, then try the examples in "Using the Messages API" (basic request, multi-turn, prefill, vision).
**Pages followed:**
- Claude docs home (starting point): https://platform.claude.com/docs/en/home
- Get started: https://platform.claude.com/docs/en/get-started
- Using the Messages API: https://platform.claude.com/docs/en/build-with-claude/working-with-messages

**Environment:**

| Component | Version |
|---|---|
| OS | macOS 26.6.2 (Darwin 25.6.0), Apple silicon |
| Python | 3.9.6 (macOS system `python3`) → 3.12.13 (Homebrew), after the fix in issue 1 |
| `anthropic` Python SDK | 0.125.0 → 2.14.0, after the fix in issue 1 |
| `httpx2` | not installed → 2.16.2 (installed with SDK 2.14.0) |
| `ant` CLI | 2.14.0 (Homebrew) |
| Editor | VS Code with Pylance |
| Virtual environment | Created with the command from Get started (`python3 -m venv .venv`) |

**Severity scale:** High = copied code fails or I could not continue without outside help. Medium = it worked, but I was confused or unsure what was happening. Low = minor annoyance.

## Top 3 takeaways

1. **Setup gives you an old SDK without warning.** On the default macOS Python (3.9), `pip install anthropic` falls back to SDK 0.125.0, which then breaks the vision example's `import httpx2`.
2. **Examples steer you toward high cost and old models.** Every example defaults to the most expensive model, with no cost guidance, and the prefill example runs on a deprecated one.
3. **Credential precedence and billing need plain language.** When both `ANTHROPIC_API_KEY` and `ant auth login` are set up, the docs don't say which credential is used or which organization is billed.

## Summary

| # | Page | Issue | Severity |
|---|---|---|---|
| 1 | Get started | `pip install anthropic` silently installs an old SDK on Python 3.9; no Python version requirement is given | High |
| 2 | Using the Messages API | Vision example's `import httpx2` fails with the SDK that step 1 installs | High |
| 3 | Get started | Using both an API key and `ant auth login` gives a warning the page doesn't explain; unclear which account is billed | Medium |
| 4 | Both | Every example uses Claude Opus 5.5 with no cost guidance or pointer to cheaper models | Medium |
| 5 | Using the Messages API | Prefill example runs on a deprecated model; no runnable version for current models | Medium |
| 6 | Using the Messages API | Code snippets leave out `import anthropic` | Low |
| 7 | Using the Messages API | Python output looks different from the JSON shown on the page | Low |
| 8 | Using the Messages API | Vision example gives no way to see the image Claude is describing | Low |
| 9 | Get started | Sample output says "Renewable energy news 2025" | Low |

## Details

### 1. `pip install anthropic` silently installs an old SDK (High)

**Page:** Get started, Python tab, step "Create a project and install the SDK"

**What I did:** Ran the commands as written:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install anthropic
```

**What happened:** On macOS, `python3` is 3.9.6. pip installed `anthropic` **0.125.0** without any warning. The latest release on PyPI is **2.14.0**, which requires Python 3.10 or later, so pip quietly fell back to the last version that supports 3.9. I only found this out later, while debugging issue 2.

**Expected:** A stated Python version requirement, or a check before the install step.

**How I fixed it:** Rebuilt the virtual environment with Homebrew's Python 3.12 (`python3.12 -m venv --clear .venv`) and ran `pip install anthropic` again. That installed 2.14.0, and the docs' `import httpx2` then worked unchanged.

**Suggestion:** Add a prerequisite such as "Python 3.10 or later. Check with `python3 --version`." Include a macOS note, because the system Python is 3.9. Consider showing how to confirm the installed SDK version (`pip show anthropic`).

### 2. Vision example: `import httpx2` cannot be resolved (High)

**Page:** Using the Messages API, Vision section, Python tab

**What I did:** Copied the Python vision example, which starts with:
```python
import base64
import httpx2
```

**What happened:** Pylance reported `Import "httpx2" could not be resolved` (reportMissingImports). The SDK that issue 1 installed (0.125.0) depends on `httpx`, not `httpx2`, so `httpx2` isn't installed. Running the script would fail with `ModuleNotFoundError`. At first this looked like a typo in the docs, and I changed it to `import httpx`. That works only because of the old SDK.

**Expected:** Code from the docs works with the SDK that the docs' own install step gives me.

**Suggestion:** Say that `httpx2` comes with newer versions of the `anthropic` SDK, and link to the Python version requirement. Alternatively, download the image with the standard library (`urllib.request`) so the example has no extra dependency.

### 3. API key and CLI login conflict; unclear which account is billed (Medium)

**Page:** Get started, "Choose how to authenticate"

**What I did:** At different times I set up both options on the page: I exported `ANTHROPIC_API_KEY` and also ran `ant auth login`.

**What happened:** I got this message:
> ANTHROPIC_API_KEY is set and takes precedence over the SDK's profile / federation auto-discovery; unset ANTHROPIC_API_KEY to use the auto-discovered credential.

I didn't know what "profile / federation auto-discovery" meant, which credential my scripts were using, or which account was paying. `ant auth status` showed that the API key was active and the login profile was being ignored. The key and the login belonged to **two different organizations**. To confirm which one was billed, I had to call the API and read the `anthropic-organization-id` response header.

**Expected:** The page says "Follow the steps for one of the following options" but doesn't say what happens if both are set up.

**Suggestion:** Add a note to this step: "If `ANTHROPIC_API_KEY` is set, it is used instead of your CLI login. Run `ant auth status` to see which credential is active. Usage is billed to the organization that owns the active credential." Reword the warning in plain language, or link from it to the Authentication page.

### 4. No cost guidance; every example uses the most expensive default (Medium)

**Pages:** Get started; Using the Messages API

**What happened:** Every example uses `claude-opus-5-5`. Neither page gives a price or a rough cost per run, and neither mentions that a cheaper model could run the same examples. I had to ask how much my test script cost. Switching all six requests to `claude-haiku-5-5` worked without other changes (apart from issue 5). Its listed price is about 40 times lower: $0.10 / $0.50 per million input / output tokens, compared with $4 / $20 for Opus 5.5.

**Expected:** A one-line note about cost when I make my first call.

**Suggestion:** In Get started, add something like: "This call costs a fraction of a cent. To keep experimenting cheaply, use `claude-haiku-5-5`." Link to pricing. The "Models overview" card under Next steps helps, but it appears only after the first call.

### 5. Prefill example uses a deprecated model (Medium)

**Page:** Using the Messages API, "Prefilling Claude's response"

**What happened:** The runnable example uses `claude-opus-4-5-20251101` with `max_tokens=1`. The page explains that Opus 4.5 is deprecated and that current models return a 400 error for prefill. It then lists four steps to adapt the example, but gives no code for them. When I moved my scripts to Haiku 5.5, I had to rewrite this example myself: I added a system prompt asking for only the letter, removed the assistant message and raised `max_tokens` to 1024 so there was room for thinking. That version worked and returned `C`.

**Suggestion:** Show the current-model version as code next to (or instead of) the Opus 4.5 example. Then the first code a reader copies from this section runs on a model that isn't deprecated.

### 6. Snippets leave out `import anthropic` (Low)

**Page:** Using the Messages API (basic request, multi-turn, prefill and vision examples)

**What happened:** The Python snippets start with `message = anthropic.Anthropic()...` and have no import. On its own, each snippet fails with `NameError`. It worked for me only because I pasted it into my Get started file, which already had the import. The vision snippet includes `import base64` and `import httpx2` but still not `import anthropic`.

**Suggestion:** Make each snippet runnable when copied on its own, or say once at the top of the page that the examples assume `import anthropic`.

### 7. Python output differs from the page's JSON (Low)

**Page:** Using the Messages API (basic request and others)

**What happened:** The page shows JSON under "Output". In Python, `print(message)` prints a Python object instead, such as `Message(id='msg_...', content=[TextBlock(...)], ...)`. It's the same data in a different format, which was briefly confusing.

**Suggestion:** In the Python tab, print `message.model_dump_json(indent=2)` to match the JSON, or add a note that Python prints the object form.

### 8. Vision: no way to see the image (Low)

**Page:** Using the Messages API, Vision section

**What happened:** The example downloads an image and Claude describes it, but I never saw the image, so I couldn't judge the description. I added code to save the image and open it in Preview.

**Suggestion:** Show the example image on the page next to the code, or link to it.

### 9. Outdated sample output (Low)

**Page:** Get started, sample output

**What happened:** The sample response suggests searching for "Renewable energy news 2025", which looks out of date in late 2026.

**Suggestion:** Regenerate the sample output, or use a prompt whose answer doesn't depend on the date.

## What worked well

- The first API call worked on the first try after setup.
- The multi-turn and URL-image examples worked unchanged.
- The prefill section clearly says which models accept prefill and lists the alternatives.
- `ant auth status` clearly showed which credential was active and why. I just didn't know to run it.
