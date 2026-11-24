"""Track a learner's progress through Kairos and award badges.

The scripts call record() when you reach a milestone, for example when the
Claude agent finishes a full tool call. Progress is saved locally in
.kairos/progress.json (git-ignored). Nothing is sent anywhere.

See your progress:  python progress.py
"""

import datetime
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROGRESS_FILE = Path(os.environ.get("KAIROS_PROGRESS_FILE", ROOT / ".kairos" / "progress.json"))

# What you do, in the order a learner usually does it.
MILESTONES = {
    "free_eval":    "Ran the eval for free (baseline or replay)",
    "claude_agent": "Completed a full tool call with the Claude agent",
    "live_eval":    "Ran the eval on a live model",
    "mcp_event":    "Scheduled a meeting through the MCP server",
    "other_llm":    "Ran Kairos on another LLM (Gemini)",
}

# What you earn. Each badge needs every milestone in "needs".
BADGES = [
    {"id": "first_agent", "name": "First Agent", "needs": ["free_eval", "claude_agent"],
     "about": "For building your first tool-calling agent, seeing the approval gate work, and running your first eval.",
     "earn": "Run the free eval, then schedule a meeting with the Claude agent (Quickstart steps 2-4).",
     "cmd": "python claude_agent.py",
     "color": "#2a78d6", "symbol": "rocket"},
    {"id": "evaluator", "name": "Evaluator", "needs": ["live_eval"],
     "about": "For measuring a real model against the golden set, not just the free baseline.",
     "earn": "Run the eval on a live model.",
     "cmd": "python evals/run_evals.py --models baseline,claude",
     "color": "#1baf7a", "symbol": "chart"},
    {"id": "connector", "name": "Connector", "needs": ["mcp_event"],
     "about": "For making your tool reusable by any MCP client, with the approval gate inside the server.",
     "earn": "Schedule a meeting through the MCP server in Claude Code (Path 2).",
     "cmd": "claude",
     "color": "#6250d6", "symbol": "plug"},
    {"id": "polyglot", "name": "Polyglot", "needs": ["other_llm"],
     "about": "For running the same agent on a second LLM API, and seeing how little has to change.",
     "earn": "Run the agent or the eval on Gemini.",
     "cmd": "python gemini_agent.py",
     "color": "#eb6834", "symbol": "globe"},
    {"id": "complete", "name": "Kairos Complete", "needs": list(MILESTONES),
     "about": "For the whole journey: building an agent, measuring it, connecting it over MCP, and porting it.",
     "earn": "Earn the other four badges.",
     "cmd": "",
     "color": "#eda100", "symbol": "trophy"},
]


def load():
    try:
        progress = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        return progress if isinstance(progress.get("milestones"), dict) else {"milestones": {}}
    except (OSError, ValueError, AttributeError):
        return {"milestones": {}}


def earned_badges(progress):
    done = progress.get("milestones", {})
    return [b for b in BADGES if all(m in done for m in b["needs"])]


def record(milestone, detail=""):
    """Mark a milestone as reached. Never raises: progress tracking must never
    break an agent or eval run. Messages go to stderr, which keeps the MCP
    server's stdout clean."""
    try:
        progress = load()
        before = {b["id"] for b in earned_badges(progress)}
        now = datetime.datetime.now().isoformat(timespec="seconds")
        entry = progress["milestones"].setdefault(milestone, {"first": now, "count": 0})
        entry["count"] += 1
        entry["last"] = now
        if detail:
            entry["detail"] = detail
        PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Write to a temporary file, then swap it in, so an interrupted save
        # can never leave a half-written (and so unreadable) progress file.
        tmp = PROGRESS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(progress, indent=2), encoding="utf-8")
        tmp.replace(PROGRESS_FILE)

        for badge in earned_badges(progress):
            if badge["id"] not in before:
                print(f"\n🏅 Badge earned: {badge['name']}! "
                      "See your progress: python progress.py", file=sys.stderr)
    except Exception:
        pass
