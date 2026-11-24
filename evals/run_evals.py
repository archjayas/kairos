"""Score what each model extracts from a scheduling request.

Sends every case in cases.jsonl to each extractor (a no-LLM regex baseline,
Claude, Gemini), captures the tool arguments from the FIRST turn only, and
scores them. It never runs the confirmation step and never calls the
calendar, so no event is ever created.

"Today" is pinned to 2026-12-01 09:00 America/Los_Angeles so results are
repeatable.

Usage (from the repo root):
    python evals/run_evals.py                          # all available extractors
    python evals/run_evals.py --models baseline,claude
    python evals/run_evals.py --repeat 3               # find flaky cases
    python evals/run_evals.py --no-boundary            # ablation: drop the source boundary
    python evals/run_evals.py --replay evals/recordings/sample_run.json   # no API keys

Needs ANTHROPIC_API_KEY + CLAUDE_MODEL for claude, and GEMINI_API_KEY for
gemini. Extractors without credentials are skipped. --replay needs neither.
"""

import argparse
import datetime
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from calendar_tools import DEFAULT_GEMINI_MODEL, build_system_prompt, normalize_datetime  # noqa: E402
from evals import baseline_extractor  # noqa: E402
from kairos_progress import record  # noqa: E402

TIMEZONE = "America/Los_Angeles"
FIXED_NOW = datetime.datetime(2026, 12, 1, 9, 0, tzinfo=ZoneInfo(TIMEZONE))
CHECKS = ["attendees", "start", "end", "zoom_link", "agenda", "no_call"]


# ---------------------------------------------------------------- extractors
# Each factory takes the system prompt and returns a function
# case -> {"called": bool, "args": dict | None, "text": str, "usage": tokens}.

def baseline_runner(system):
    def run(case):
        args, text = baseline_extractor.extract(case["request"], FIXED_NOW, TIMEZONE)
        return {"called": args is not None, "args": args, "text": text}
    return run


def claude_runner(system):
    import anthropic
    import claude_agent

    client = anthropic.Anthropic()
    model = os.environ["CLAUDE_MODEL"]

    def run(case):
        response, tool_use = claude_agent.first_turn(client, model, case["request"], system)
        usage = {"input": response.usage.input_tokens, "output": response.usage.output_tokens}
        if tool_use is None:
            return {"called": False, "args": None, "text": claude_agent.text_of(response), "usage": usage}
        return {"called": True, "args": dict(tool_use.input), "text": "", "usage": usage}
    return run


def gemini_runner(system):
    from google import genai
    import gemini_agent

    client = genai.Client()

    def run(case):
        interaction, call = gemini_agent.first_turn(client, case["request"], system)
        usage = gemini_usage(interaction)
        if call is None:
            return {"called": False, "args": None, "text": interaction.output_text or "", "usage": usage}
        return {"called": True, "args": dict(call.arguments), "text": "", "usage": usage}
    return run


def gemini_usage(interaction):
    """Token counts from a Gemini interaction, or None if the SDK doesn't report them."""
    usage = getattr(interaction, "usage", None)
    if usage is None:
        return None
    get = usage.get if isinstance(usage, dict) else (lambda k: getattr(usage, k, None))
    return {"input": get("total_input_tokens"), "output": get("total_output_tokens")}


EXTRACTORS = {
    "baseline": (baseline_runner, lambda: True),
    "claude": (claude_runner, lambda: bool(os.environ.get("CLAUDE_MODEL")) and bool(
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))),
    "gemini": (gemini_runner, lambda: bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))),
}


# ------------------------------------------------------------------- scoring

def to_instant(value):
    """Parse a model time into an aware datetime. Comparing aware datetimes
    compares moments, so 15:00-05:00 equals 12:00-08:00."""
    return datetime.datetime.fromisoformat(normalize_datetime(value, TIMEZONE))


def made_up_fields(case, args):
    """Fields the request doesn't support: an email or Zoom link that isn't
    in the request text, or an agenda when the request has no topic."""
    request = case["request"].lower()
    invented = []
    for email in args.get("attendees") or []:
        if email.lower() not in request:
            invented.append(f"attendee {email}")
    zoom = args.get("zoom_link")
    if zoom and zoom.lower() not in request:
        invented.append(f"zoom_link {zoom}")
    if case.get("expected", {}).get("agenda") is False and args.get("agenda"):
        invented.append(f"agenda {args['agenda']!r}")
    return invented


def score(case, outcome):
    """Score one outcome against one case. Pure function: no API calls."""
    if "error" in outcome:
        return {"passed": False, "checks": {}, "invented": [], "notes": [outcome["error"]]}

    checks, notes = {}, []
    called, args = outcome["called"], outcome["args"] or {}

    if not case["expect_call"]:
        checks["no_call"] = not called
        if called:
            notes.append("no_call: called the tool on an incomplete request")
    elif not called:
        if case.get("clarify_ok"):
            notes.append("asked to clarify (acceptable for this case)")
        else:
            for name in CHECKS[:5]:
                checks[name] = False
            notes.append(f"no tool call: {outcome['text'][:120]!r}")
    else:
        expected = case["expected"]
        got_attendees = {a.lower() for a in args.get("attendees") or []}
        checks["attendees"] = got_attendees == set(expected["attendees"])
        if not checks["attendees"]:
            notes.append(f"attendees: expected {sorted(expected['attendees'])}, got {sorted(got_attendees)}")

        try:
            got_start = to_instant(args["start_datetime"])
            got_end = to_instant(args["end_datetime"])
        except (KeyError, ValueError, TypeError) as e:
            got_start = got_end = None
            notes.append(f"unparseable time: {e}")
        options = [(to_instant(s), to_instant(e)) for s, e in expected["times"]]
        want_start, want_end = next((o for o in options if o[0] == got_start), options[0])
        checks["start"] = got_start == want_start
        checks["end"] = got_end == want_end
        if not checks["start"]:
            notes.append(f"start: expected {want_start.isoformat()}, got {args.get('start_datetime')}")
        if not checks["end"]:
            notes.append(f"end: expected {want_end.isoformat()}, got {args.get('end_datetime')}")

        got_zoom = (args.get("zoom_link") or "").strip() or None
        checks["zoom_link"] = got_zoom == expected["zoom_link"]
        if not checks["zoom_link"]:
            notes.append(f"zoom_link: expected {expected['zoom_link']}, got {got_zoom}")

        if expected["agenda"] is not None:
            has_agenda = bool((args.get("agenda") or "").strip())
            checks["agenda"] = has_agenda == expected["agenda"]
            if not checks["agenda"]:
                notes.append(f"agenda: expected {'present' if expected['agenda'] else 'absent'}, "
                             f"got {args.get('agenda')!r}")

    invented = made_up_fields(case, args) if called else []
    if invented:
        notes.append("made up: " + ", ".join(invented))
    return {"passed": all(checks.values()), "checks": checks, "invented": invented, "notes": notes}


# ------------------------------------------------------------------- running

def collect(name, cases, system, repeat):
    """Call one extractor on every case, `repeat` times.
    Returns a list of runs; each run is a list of outcomes in case order."""
    runner = EXTRACTORS[name][0](system)

    def one(case):
        try:
            return runner(case)
        except Exception as e:  # record and keep going; one bad call shouldn't sink the run
            return {"error": f"{type(e).__name__}: {e}"[:300]}

    with ThreadPoolExecutor(max_workers=6) as pool:
        return [list(pool.map(one, cases)) for _ in range(repeat)]


def load_recording(path, cases):
    """Load saved outcomes so they can be re-scored without calling any model.
    Outcomes are matched to cases by id; a case with no recording is an error."""
    saved = json.loads(Path(path).read_text(encoding="utf-8"))
    recorded = {}
    for name, runs in saved["results"].items():
        if runs and isinstance(runs[0], dict):  # older single-run format
            runs = [runs]
        by_id = [{r["id"]: r for r in run} for run in runs]
        recorded[name] = [
            [run.get(c["id"], {"error": f"no recording for case {c['id']}"}) for c in cases]
            for run in by_id
        ]
    return saved, recorded


# ------------------------------------------------------------------ reporting

def pct(hits, total):
    return f"{hits}/{total} ({100 * hits / total:.0f}%)" if total else "n/a"


def summarize(cases, names, outcomes, scored):
    """Per-extractor totals. Pools every (case, run) pair: with --repeat 3, 20 cases
    count as 60. Used by the terminal report and by evals/dashboard.py."""
    repeat = len(next(iter(scored.values())))
    summaries = {}
    for name in names:
        flat = [(r, o) for s_run, o_run in zip(scored[name], outcomes[name]) for r, o in zip(s_run, o_run)]
        s = {"case_runs": len(flat), "passed": sum(r["passed"] for r, _ in flat)}
        for check in CHECKS:
            values = [r["checks"][check] for r, _ in flat if check in r["checks"]]
            s[check] = [sum(values), len(values)]
        calls = [r for r, o in flat if o.get("called")]
        s["made_up"] = [sum(bool(r["invented"]) for r in calls), len(calls)]
        s["errors"] = sum("error" in o for _, o in flat)
        usages = [o["usage"] for _, o in flat if o.get("usage")]
        s["tokens"] = ({"input": sum(u["input"] or 0 for u in usages),
                        "output": sum(u["output"] or 0 for u in usages),
                        "calls": len(usages)} if usages else None)
        s["flaky_cases"] = sum(
            0 < sum(run[i]["passed"] for run in scored[name]) < repeat for i in range(len(cases))
        )
        summaries[name] = s
    return summaries


def print_report(cases, names, outcomes, scored):
    width = 22
    repeat = len(next(iter(scored.values())))

    print(f"\n{'case':<5} {'category':<19}" + "".join(f"{n:<{width}}" for n in names))
    for i, case in enumerate(cases):
        row = f"{case['id']:<5} {case['category']:<19}"
        for name in names:
            results = [run[i] for run in scored[name]]
            passes = sum(r["passed"] for r in results)
            failed = sorted({k for r in results for k, v in r["checks"].items() if not v})
            if any("error" in run[i] for run in outcomes[name]):
                cell = "ERROR"
            elif repeat == 1:
                asked = not outcomes[name][0][i].get("called") and case.get("clarify_ok")
                cell = ("PASS" + (" (asked)" if asked else "")) if passes else "FAIL: " + ",".join(failed)
            elif passes == repeat:
                cell = f"PASS {passes}/{repeat}"
            elif passes == 0:
                cell = f"FAIL 0/{repeat}: " + ",".join(failed)
            else:
                cell = f"FLAKY {passes}/{repeat}: " + ",".join(failed)
            row += f"{cell[:width - 1]:<{width}}"
        print(row)

    summaries = summarize(cases, names, outcomes, scored)

    label = "case pass rate" if repeat == 1 else f"pass rate ({repeat} runs)"
    print(f"\n{'metric':<24}" + "".join(f"{n:<{width}}" for n in names))
    rows = [(label, lambda s: pct(s["passed"], s["case_runs"]))]
    rows += [(check, lambda s, c=check: pct(*s[c])) for check in CHECKS]
    rows += [("made-up-field rate", lambda s: pct(*s["made_up"])),
             ("errors", lambda s: str(s["errors"]))]
    if any(summaries[n]["tokens"] for n in names):
        rows += [("input tokens", lambda s: f"{s['tokens']['input']:,}" if s["tokens"] else "-"),
                 ("output tokens", lambda s: f"{s['tokens']['output']:,}" if s["tokens"] else "-")]
    if repeat > 1:
        rows.append(("flaky cases", lambda s: str(s["flaky_cases"])))
    for row_label, fmt in rows:
        print(f"{row_label:<24}" + "".join(f"{fmt(summaries[n]):<{width}}" for n in names))
    print("(made-up-field rate = tool calls with an email/link not in the request, "
          "or an agenda the request didn't give; lower is better)")

    print("\nWhy each failure failed:")
    for name in names:
        for i, case in enumerate(cases):
            seen = set()
            for run_index, run in enumerate(scored[name]):
                r = run[i]
                if r["passed"] and not r["invented"]:
                    continue
                detail = "; ".join(r["notes"])
                if detail in seen:
                    continue
                seen.add(detail)
                tag = f" run {run_index + 1}" if repeat > 1 else ""
                print(f"  [{name}] {case['id']}{tag}: {detail}")
    return summaries


# ----------------------------------------------------------------------- main

def positive_int(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--models", default="baseline,claude,gemini")
    parser.add_argument("--cases", default=str(ROOT / "evals" / "cases.jsonl"))
    parser.add_argument("--out", default=str(ROOT / "evals" / "results" / "latest.json"))
    parser.add_argument("--repeat", type=positive_int, default=1, help="run each case N times")
    parser.add_argument("--no-boundary", action="store_true",
                        help="ablation: leave the source-boundary instruction out of the prompt")
    parser.add_argument("--replay", metavar="FILE",
                        help="re-score saved outcomes from FILE instead of calling models")
    args = parser.parse_args()

    cases = [json.loads(line) for line in Path(args.cases).read_text(encoding="utf-8").splitlines()
             if line.strip()]
    for case in cases:
        if case.get("expect_call") and "expected" not in case:
            sys.exit(f"Case {case.get('id', '?')} has expect_call true but no \"expected\" answers. "
                     "See docs/how-to/add-eval-cases.md.")
    requested = [n.strip().lower() for n in args.models.split(",") if n.strip()]
    unknown = [n for n in requested if n not in EXTRACTORS]
    if unknown:
        sys.exit(f"Unknown --models {', '.join(unknown)}. Choose from: {', '.join(EXTRACTORS)}.")

    if args.replay:
        saved, outcomes = load_recording(args.replay, cases)
        names = [n for n in requested if n in outcomes]
        outcomes = {n: outcomes[n] for n in names}
        meta = {k: saved.get(k) for k in ("models", "source_boundary")}
        print(f"Replaying {args.replay} (no model calls). Replays aren't saved, so --out is ignored.")
    else:
        system = build_system_prompt(now=FIXED_NOW, timezone_name=TIMEZONE,
                                     source_boundary=not args.no_boundary)
        names, outcomes = [], {}
        for name in requested:
            if not EXTRACTORS[name][1]():
                needs = {"claude": "CLAUDE_MODEL and ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}[name]
                print(f"Skipping {name}: set {needs} to run it.")
                continue
            print(f"Running {name} on {len(cases)} cases x{args.repeat}...")
            names.append(name)
            outcomes[name] = collect(name, cases, system, args.repeat)
        all_models = {"claude": os.environ.get("CLAUDE_MODEL"),
                      "gemini": os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)}
        meta = {"models": {n: m for n, m in all_models.items() if n in names},
                "source_boundary": not args.no_boundary}

    if not names:
        sys.exit("Nothing to run. Try --models baseline, which is free and needs no API key.")
    if meta.get("source_boundary") is False:
        print("Prompt: source boundary OFF (ablation)")
    scored = {n: [[score(c, o) for c, o in zip(cases, run)] for run in outcomes[n]] for n in names}
    summaries = print_report(cases, names, outcomes, scored)

    # A model whose every call failed (wrong key, bad model id) didn't really run.
    failed = [n for n in names if summaries[n]["errors"] == summaries[n]["case_runs"]]
    for n in failed:
        print(f"\nWarning: every {n} call failed (see the errors above). "
              "Check your API key and model id.")
    live_ok = [n for n in names if n != "baseline" and n not in failed]

    # Learner progress (see progress.py). Baseline and replay are the free path.
    if args.replay or "baseline" in names:
        record("free_eval")
    if not args.replay and live_ok:
        record("live_eval", ",".join(live_ok))
    if not args.replay and "gemini" in live_ok:
        record("other_llm", "eval")

    if args.replay:
        return  # replay never overwrites results
    if [n for n in names if n != "baseline"] and not live_ok:  # every model failed
        print("Results not saved, so your last good run is kept.")
        return
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "fixed_now": FIXED_NOW.isoformat(),
        **meta,
        "repeat": args.repeat,
        "summaries": summaries,
        "results": {n: [[{"id": c["id"], **o} for c, o in zip(cases, run)] for run in outcomes[n]]
                    for n in names},
    }, indent=2, default=str), encoding="utf-8")
    print(f"\nFull results written to {out}")

    # One line per run, so the dashboard can chart pass rate over time.
    history = ROOT / "evals" / "results" / "history.jsonl"
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "time": datetime.datetime.now().isoformat(timespec="seconds"),
            "cases": Path(args.cases).name, **meta, "repeat": args.repeat,
            "pass_rate": {n: summaries[n]["passed"] / summaries[n]["case_runs"]
                          for n in names if n not in failed},
            "tokens": {n: summaries[n]["tokens"] for n in names if n not in failed},
        }) + "\n")
    print("Dashboard: python evals/dashboard.py")


if __name__ == "__main__":
    main()
