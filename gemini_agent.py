"""Gemini calendar agent: takes a meeting request as free-form natural
language typed at runtime, has Gemini extract the event fields via function
calling, and creates the event (Zoom link + agenda included).

Calendar code and the tool schema live in calendar_tools.py so the Claude
version can share them.

Prerequisites:
    export GEMINI_API_KEY="your-key-from-aistudio.google.com"
    export CALENDAR_BACKEND=mock                 # default; 'google' for real
    export TIMEZONE=America/Los_Angeles          # default
    pip install -r requirements.txt

For CALENDAR_BACKEND=google you also need credentials.json (see README).
"""

import os
import sys

from google import genai

from calendar_tools import DEFAULT_GEMINI_MODEL, GEMINI_TOOL, build_system_prompt, get_timezone_name, run_tool_call
from kairos_progress import record

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)


def first_turn(client, user_input, system_instruction=None):
    """Send the request; return (interaction, function_call step or None).

    Used by the CLI below and by evals/run_evals.py, which stops here so it
    never creates an event."""
    # system_instruction anchors relative dates ("tomorrow") to a real date
    # and the user's timezone — the model has no other source for either —
    # and nudges it to pull out the optional agenda/zoom_link fields when
    # the free-form input happens to mention them.
    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        system_instruction=system_instruction or build_system_prompt(),
        tools=[GEMINI_TOOL],
        input=user_input,
    )
    # The model's response is a list of steps; if it decided to call our
    # tool, one of them is a function_call step carrying the arguments.
    function_call = next(
        (step for step in interaction.steps if step.type == "function_call"), None
    )
    return interaction, function_call


def run():
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

    # Reads the actual meeting request from the terminal at runtime.
    user_input = input("Your request: ").strip()

    client = genai.Client()
    interaction, function_call = first_turn(client, user_input)

    if function_call is None:
        # Likely means the request didn't include enough info to satisfy the
        # tool's required fields (e.g. no attendee email) — the model falls
        # back to asking for what's missing instead of calling the function.
        print("\nModel responded without calling the function:")
        print(interaction.output_text)
        return

    # Shows the extracted fields and asks "Create this event? (y/n)".
    # Only "y" creates the event; otherwise result says the user declined.
    result = run_tool_call(function_call.arguments)

    # Reports the function's result (created or declined) back to the same
    # conversation (previous_interaction_id) so Gemini can turn it into a
    # natural-language confirmation instead of us just printing raw JSON.
    # result must be the raw dict, not a json.dumps() string, and name
    # should echo the function's name — see docs/FRICTION_LOG_GEMINI.md
    # #16 for why.
    interaction_2 = client.interactions.create(
        model=GEMINI_MODEL,
        previous_interaction_id=interaction.id,
        input=[
            {
                "type": "function_result",
                "call_id": function_call.id,
                "name": function_call.name,
                "result": result,
            }
        ],
    )

    print("\n" + interaction_2.output_text)
    record("other_llm", "gemini_agent")  # learner progress


def main():
    # Common failures become readable messages instead of stack traces.
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        sys.exit("Set GEMINI_API_KEY to your key from aistudio.google.com.")
    try:
        get_timezone_name()  # check TIMEZONE before you type a request
        run()
    except (KeyboardInterrupt, EOFError):
        sys.exit("\nCancelled. Nothing was created.")
    except ValueError as e:  # e.g. an invalid TIMEZONE setting
        sys.exit(str(e))
    except Exception as e:  # API errors: show the message, not a traceback
        sys.exit(f"Gemini API error: {e}")


if __name__ == "__main__":
    main()
