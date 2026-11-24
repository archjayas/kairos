"""Claude calendar agent: same behavior as gemini_agent.py, built on the
Anthropic Messages API with tool use.

Flow:
  1. Send the request + tool definition + a system prompt anchoring today's
     date and timezone.
  2. If Claude replies with stop_reason "tool_use", take the tool_use block,
     run the confirmation step, and create the event (or not).
  3. Send a tool_result with the matching tool_use_id; print Claude's reply.
  If Claude asks for missing details instead (stop_reason "end_turn"), print
  its question.

Prerequisites:
    export ANTHROPIC_API_KEY="your-key-from-console.anthropic.com"
    export CLAUDE_MODEL="claude-opus-5-5"        # any current Claude model id
    export CALENDAR_BACKEND=mock                 # default; 'google' for real
    export TIMEZONE=America/Los_Angeles          # default
    pip install -r requirements.txt
"""

import json
import os
import sys

import anthropic

from calendar_tools import CLAUDE_TOOL, build_system_prompt, get_timezone_name, run_tool_call
from kairos_progress import record

MAX_TOKENS = 16000


def text_of(response):
    """Join the text blocks of a response (skipping thinking/tool_use blocks)."""
    return "\n".join(b.text for b in response.content if b.type == "text").strip()


def create_message(client, model, system, messages):
    return client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        system=system,
        tools=[CLAUDE_TOOL],
        # One tool call per reply. This agent confirms and answers a single call,
        # and the API rejects a follow-up that leaves a second call unanswered.
        tool_choice={"type": "auto", "disable_parallel_tool_use": True},
        messages=messages,
    )


def first_turn(client, model, user_input, system=None):
    """Send the request; return (response, tool_use block or None).

    Used by the CLI below and by evals/run_evals.py, which stops here so it
    never creates an event."""
    messages = [{"role": "user", "content": user_input}]
    response = create_message(client, model, system or build_system_prompt(), messages)
    tool_use = None
    if response.stop_reason == "tool_use":
        tool_use = next(b for b in response.content if b.type == "tool_use")
    return response, tool_use


def run(model):
    print("Describe the meeting you'd like to schedule. Include:")
    print("  - Who:     attendee email address(es)")
    print("  - When:    a date and time (e.g. 'tomorrow at 3pm' or 'Aug 5 at 10am for 1 hour')")
    print("  - Agenda:  a brief description of what the meeting is about")
    print("  - Zoom:    a meeting link, if you have one (optional)")
    print()
    print("Example:")
    print("  Schedule a meeting with alice@example.com and bob@example.com")
    print("  tomorrow at 2pm for 45 minutes to discuss Q3 planning.")
    print("  Zoom link: https://zoom.us/j/123456789")
    print()
    user_input = input("Your request: ").strip()

    # Anthropic() reads ANTHROPIC_API_KEY from the environment.
    client = anthropic.Anthropic()
    system = build_system_prompt()
    response, tool_use = first_turn(client, model, user_input, system)

    if response.stop_reason == "refusal":
        print("\nClaude declined this request.")
        return
    if tool_use is None:
        # Usually Claude asking for something missing (e.g. an email
        # address) instead of guessing.
        print("\nClaude responded without calling the tool:")
        print(text_of(response))
        return

    result = run_tool_call(tool_use.input)

    # Unlike Gemini's server-side previous_interaction_id, the Messages API
    # is stateless: we resend the conversation ourselves. Send back the
    # whole assistant turn (it may include thinking blocks alongside
    # tool_use), then our tool_result. tool_use_id must match; content must
    # be a string or content blocks, so the dict is JSON-encoded.
    messages = [
        {"role": "user", "content": user_input},
        {"role": "assistant", "content": response.content},
        {
            "role": "user",
            "content": [{
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": json.dumps(result),
            }],
        },
    ]
    final = create_message(client, model, system, messages)
    print("\n" + text_of(final))
    record("claude_agent")  # learner progress: a full tool call, start to finish


def main():
    model = os.environ.get("CLAUDE_MODEL")
    if not model:
        sys.exit("Set CLAUDE_MODEL to a Claude model id, e.g. claude-opus-5-5.")
    # Checked up front, so you don't type a request only to hit a missing key.
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        sys.exit("Set ANTHROPIC_API_KEY to your key from console.anthropic.com.")
    # Common failures become readable messages instead of stack traces.
    try:
        get_timezone_name()  # check TIMEZONE before you type a request
        run(model)
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nCancelled. Nothing was created.")
    except ValueError as e:  # e.g. an invalid TIMEZONE setting
        sys.exit(str(e))
    except anthropic.AuthenticationError:
        sys.exit("Authentication failed: check ANTHROPIC_API_KEY.")
    except anthropic.NotFoundError:
        sys.exit(f"Model {model!r} not found: check CLAUDE_MODEL.")
    except anthropic.BadRequestError as e:
        sys.exit(f"Bad request: {e.message}")
    except anthropic.RateLimitError:
        sys.exit("Rate limited (the SDK already retried). Try again shortly.")
    except anthropic.APIStatusError as e:
        sys.exit(f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        sys.exit("Could not reach the Anthropic API. Check your network.")


if __name__ == "__main__":
    main()
