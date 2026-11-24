"""See your Kairos progress and badges.

Kairos records milestones as you go (running the eval, the agents, the MCP
server). This shows what you've done, the badges you've earned, and what's next.

Usage:
    python progress.py            # summary here, plus a progress page in your browser
    python progress.py --no-open  # summary only
    python progress.py --reset    # start over
"""

import argparse
import datetime
import html
import webbrowser
from pathlib import Path

from kairos_progress import BADGES, MILESTONES, PROGRESS_FILE, earned_badges, load

SYMBOLS = {"rocket": "🚀", "chart": "📊", "plug": "🔌", "globe": "🌐", "trophy": "🏆"}
esc = html.escape


LOCKED_COLOR = "#e34948"  # red: "not yet", without looking disabled

# A white padlock drawn in SVG (crisper than an emoji at small sizes).
LOCK = f"""<path d="M47 57 v-9 a13 13 0 0 1 26 0 v9" fill="none" stroke="#ffffff"
    stroke-width="6" stroke-linecap="round"/>
  <rect x="39" y="55" width="42" height="31" rx="6" fill="#ffffff"/>
  <circle cx="60" cy="67.5" r="4.2" fill="{LOCKED_COLOR}"/>
  <rect x="58.2" y="69" width="3.6" height="8" rx="1.5" fill="{LOCKED_COLOR}"/>"""


def badge_svg(badge, earned):
    """A round medallion: the badge's color and symbol when earned, red with a
    white padlock when not."""
    color = badge["color"] if earned else LOCKED_COLOR
    icon = (f'<text x="60" y="74" font-size="40" text-anchor="middle">{SYMBOLS[badge["symbol"]]}</text>'
            if earned else LOCK)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img"
  aria-label="{esc(badge['name'])} badge, {'earned' if earned else 'not yet earned'}">
  <defs><radialGradient id="g-{badge['id']}-{int(earned)}" cx="38%" cy="30%" r="75%">
    <stop offset="0" stop-color="#ffffff" stop-opacity="0.4"/>
    <stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>
  <circle cx="60" cy="60" r="54" fill="{color}"/>
  <circle cx="60" cy="60" r="54" fill="url(#g-{badge['id']}-{int(earned)})"/>
  <circle cx="60" cy="60" r="45" fill="none" stroke="#ffffff" stroke-opacity="0.6" stroke-width="2.5"
    stroke-dasharray="{'none' if earned else '5 5'}"/>
  {icon}
</svg>"""


def terminal_summary(progress):
    done = progress.get("milestones", {})
    earned = {b["id"] for b in earned_badges(progress)}
    filled = round(20 * len(earned) / len(BADGES))
    print(f"\nKairos progress  [{'#' * filled}{'.' * (20 - filled)}]  "
          f"{len(earned)} of {len(BADGES)} badges\n")
    for key, label in MILESTONES.items():
        mark = "x" if key in done else " "
        when = f"  ({done[key].get('first', '')[:10]})" if key in done else ""
        print(f"  [{mark}] {label}{when}")
    print()
    for badge in BADGES:
        if badge["id"] in earned:
            print(f"  {SYMBOLS[badge['symbol']]}  {badge['name']}: earned")
        else:
            print(f"  🔒  {badge['name']}: {badge['earn']}" + (f"  ->  {badge['cmd']}" if badge["cmd"] else ""))
    next_badge = next((b for b in BADGES if b["id"] not in earned), None)
    print("\n" + (f"Next up: {next_badge['name']}. {next_badge['earn']}"
                  + (f" Try: {next_badge['cmd']}" if next_badge["cmd"] else "") if next_badge
                  else "You've finished Kairos. Congratulations! 🎉") + "\n")


def journey_svg(progress):
    """The learner's path: one stop per milestone, filled when reached."""
    done = progress.get("milestones", {})
    keys = list(MILESTONES)
    w, left, right, y = 760, 60, 60, 46
    step = (w - left - right) / (len(keys) - 1)
    reached = [k in done for k in keys]
    parts = [f'<svg class="journey" viewBox="0 0 {w} 130" role="img" aria-label="Your milestones">',
             f'<line x1="{left}" y1="{y}" x2="{w - right}" y2="{y}" class="track"/>']
    for i in range(len(keys) - 1):  # color a segment only when both of its stops are done
        if reached[i] and reached[i + 1]:
            parts.append(f'<line x1="{left + step * i}" y1="{y}" x2="{left + step * (i + 1)}" '
                         f'y2="{y}" class="track-done"/>')
    short = ["Free eval", "Claude agent", "Live eval", "MCP", "Gemini"]
    for i, k in enumerate(keys):
        x = left + step * i
        state = "done" if reached[i] else "todo"
        date = done[k].get("first", "")[5:10] if reached[i] else ""
        parts.append(f'<g class="stop {state}"><title>{esc(MILESTONES[k])}</title>'
                     f'<circle cx="{x}" cy="{y}" r="13"/>'
                     f'<text x="{x}" y="{y + 5}" text-anchor="middle" class="tick">{"✓" if reached[i] else i + 1}</text>'
                     f'<text x="{x}" y="{y + 38}" text-anchor="middle" class="stop-label">{short[i]}</text>'
                     f'<text x="{x}" y="{y + 56}" text-anchor="middle" class="stop-date">{date}</text></g>')
    parts.append("</svg>")
    return "".join(parts)


def progress_page(progress):
    earned = {b["id"] for b in earned_badges(progress)}
    cards = []
    for badge in BADGES:
        got = badge["id"] in earned
        cards.append(f'<div class="badge {"earned" if got else "locked"}">{badge_svg(badge, got)}'
                     f'<h3>{esc(badge["name"])}</h3>'
                     f'<p>{"Earned!" if got else esc(badge["earn"])}</p>'
                     f'{"" if got or not badge["cmd"] else "<code>" + esc(badge["cmd"]) + "</code>"}</div>')
    next_badge = next((b for b in BADGES if b["id"] not in earned), None)
    cheer = ("You've finished Kairos. Congratulations! 🎉" if not next_badge else
             "Great start! " if earned else "Welcome! ") + (
             f"Next up: <strong>{esc(next_badge['name'])}</strong>. {esc(next_badge['earn'])}"
             + (f" Try <code>{esc(next_badge['cmd'])}</code>" if next_badge["cmd"] else "") if next_badge else "")
    percent = round(100 * len(earned) / len(BADGES))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>My Kairos progress</title>
<style>
:root {{ color-scheme: light; --bg: #fcfcfb; --card: #f3f2ef; --text: #0b0b0b; --text-2: #52514e;
  --track: #dcdbd6; --done: #6250d6; }}
@media (prefers-color-scheme: dark) {{ :root {{ color-scheme: dark; --bg: #1a1a19; --card: #252524;
  --text: #f0efec; --text-2: #c3c2b7; --track: #3a3a38; --done: #9085e9; }} }}
body {{ margin: 0; background: var(--bg); color: var(--text); font: 16px/1.5 system-ui, sans-serif; }}
main {{ max-width: 900px; margin: 0 auto; padding: 28px 16px 48px; }}
h1 {{ margin: 0 0 4px; }} .sub {{ color: var(--text-2); margin: 0 0 20px; }}
.meter {{ height: 14px; background: var(--track); border-radius: 7px; overflow: hidden; }}
.meter > div {{ height: 100%; width: {percent}%; background: linear-gradient(90deg, #4f46e5, #a855f7, #f59e0b); }}
.meter-label {{ font-weight: 700; margin: 8px 0 24px; }}
.journey {{ width: 100%; height: auto; }} .track {{ stroke: var(--track); stroke-width: 4; }}
.track-done {{ stroke: var(--done); stroke-width: 4; }}
.stop circle {{ fill: var(--bg); stroke: var(--track); stroke-width: 3; }}
.stop.done circle {{ fill: var(--done); stroke: var(--done); }}
.tick {{ font: 700 13px system-ui; fill: var(--text-2); }} .stop.done .tick {{ fill: #fff; }}
.stop-label {{ font: 600 13px system-ui; fill: var(--text); }} .stop-date {{ font: 12px system-ui; fill: var(--text-2); }}
.badges {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; margin-top: 8px; }}
.badge {{ background: var(--card); border-radius: 12px; padding: 16px; text-align: center; }}
.badge svg {{ width: 96px; height: 96px; }} .badge h3 {{ margin: 8px 0 4px; font-size: 1rem; }}
.badge p {{ margin: 0; font-size: 0.85rem; color: var(--text-2); }}
.badge.earned p {{ color: var(--done); font-weight: 700; }}
.badge code, .cheer code {{ display: inline-block; margin-top: 6px; font-size: 0.78rem; padding: 2px 6px;
  border-radius: 5px; background: var(--bg); word-break: break-word; }}
.cheer {{ background: var(--card); border-radius: 12px; padding: 14px 16px; margin: 24px 0; }}
</style></head><body><main>
<h1>My Kairos progress</h1>
<p class="sub">Updated {datetime.datetime.now():%b %d, %Y at %H:%M}. Kairos records this on your computer only.</p>
<div class="meter" role="progressbar" aria-valuenow="{percent}" aria-valuemin="0" aria-valuemax="100"><div></div></div>
<p class="meter-label">{len(earned)} of {len(BADGES)} badges ({percent}%)</p>
<h2>Your journey</h2>
{journey_svg(progress)}
<p class="cheer">{cheer}</p>
<h2>Badges</h2>
<div class="badges">{"".join(cards)}</div>
</main></body></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-open", action="store_true", help="don't open the progress page")
    parser.add_argument("--reset", action="store_true", help="forget all progress")
    parser.add_argument("--export-badges", metavar="DIR", help=argparse.SUPPRESS)  # for the docs site
    args = parser.parse_args()

    if args.export_badges:
        out = Path(args.export_badges); out.mkdir(parents=True, exist_ok=True)
        for badge in BADGES:
            (out / f"{badge['id']}.svg").write_text(badge_svg(badge, True), encoding="utf-8")
        print(f"Badges written to {out}")
        return
    if args.reset:
        PROGRESS_FILE.unlink(missing_ok=True)
        print("Progress reset.")
        return

    progress = load()
    terminal_summary(progress)
    if not args.no_open:
        page = PROGRESS_FILE.parent / "progress.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(progress_page(progress), encoding="utf-8")
        print(f"Progress page: {page}")
        webbrowser.open(page.resolve().as_uri())


if __name__ == "__main__":
    main()
