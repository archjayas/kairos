"""Turn eval results into a dashboard: one self-contained HTML page.

Shows pass rate, accuracy per check, the made-up-field rate, token usage, every
case's result, and pass rate over time. No API calls and no extra packages: it
re-scores the saved results with the same code as run_evals.py.

Usage (from the repo root):
    python evals/dashboard.py                    # latest run, opens in your browser
    python evals/dashboard.py --results evals/recordings/sample_run.json
    python evals/dashboard.py --no-open --out my_dashboard.html
"""

import argparse
import html
import json
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.run_evals import CHECKS, load_recording, score, summarize  # noqa: E402

RESULTS_DIR = ROOT / "evals" / "results"
SAMPLE = ROOT / "evals" / "recordings" / "sample_run.json"

# Identity colors, fixed per extractor (never by rank). Validated with the
# dataviz palette checker: CVD-safe for all three pairs, light and dark.
# Light aqua is below 3:1 contrast, so every bar also carries a text label.
COLORS = {
    "claude":   ("#2a78d6", "#3987e5"),
    "gemini":   ("#eb6834", "#d95926"),
    "baseline": ("#1baf7a", "#199e70"),
}
LABELS = {"claude": "Claude", "gemini": "Gemini", "baseline": "Baseline (no AI)"}
CHECK_LABELS = {"attendees": "Attendees", "start": "Start time", "end": "End time",
                "zoom_link": "Zoom link", "agenda": "Agenda", "no_call": "Asks when info is missing"}

esc = html.escape


def pct(hits, total):
    return 100 * hits / total if total else None


def bar_path(x, y, width, height, radius=4):
    """A bar anchored at the left, with a rounded data end on the right."""
    if width <= radius:
        return f'<rect x="{x}" y="{y}" width="{max(width, 1):.1f}" height="{height}"/>'
    w = width - radius
    return (f'<path d="M{x},{y} h{w:.1f} a{radius},{radius} 0 0 1 {radius},{radius} '
            f'v{height - 2 * radius} a{radius},{radius} 0 0 1 -{radius},{radius} h-{w:.1f} z"/>')


# ------------------------------------------------------------------ sections

def stat_tiles(names, summaries):
    tiles = []
    for n in names:
        s = summaries[n]
        rate = pct(s["passed"], s["case_runs"]) or 0
        made_up = pct(*s["made_up"])
        tokens = s.get("tokens")
        token_line = (f'{tokens["input"]:,} in &middot; {tokens["output"]:,} out'
                      if tokens else "not recorded")
        tiles.append(f"""
      <div class="tile">
        <div class="tile-name"><span class="chip" style="background:var(--{n})"></span>{esc(LABELS.get(n, n))}</div>
        <div class="tile-value">{rate:.0f}%</div>
        <div class="tile-sub">of cases passed ({s["passed"]}/{s["case_runs"]})</div>
        <dl>
          <dt>Made-up fields</dt><dd>{"n/a" if made_up is None else f"{made_up:.0f}%"}</dd>
          <dt>Tokens</dt><dd>{token_line}</dd>
          <dt>Errors</dt><dd>{s["errors"]}</dd>
        </dl>
      </div>""")
    return '<div class="tiles">' + "".join(tiles) + "</div>"


def check_bars(names, summaries):
    label_w, bar_area, bar_h, gap, group_gap = 190, 380, 12, 2, 14
    groups = [c for c in CHECKS if any(summaries[n][c][1] for n in names)]
    height = len(groups) * (len(names) * (bar_h + gap) + group_gap) + 20
    out = [f'<svg class="chart" viewBox="0 0 {label_w + bar_area + 60} {height}" role="img" '
           f'aria-label="Accuracy by check for each extractor">']
    for pct_mark in (0, 50, 100):  # recessive grid
        x = label_w + bar_area * pct_mark / 100
        out.append(f'<line class="grid" x1="{x}" y1="0" x2="{x}" y2="{height - 16}"/>'
                   f'<text class="axis" x="{x}" y="{height - 2}" text-anchor="middle">{pct_mark}%</text>')
    y = 4
    for check in groups:
        group_h = len(names) * (bar_h + gap)
        out.append(f'<text class="row-label" x="{label_w - 10}" y="{y + group_h / 2 + 4}" '
                   f'text-anchor="end">{esc(CHECK_LABELS[check])}</text>')
        for n in names:
            hits, total = summaries[n][check]
            value = pct(hits, total)
            if value is None:
                y += bar_h + gap
                continue
            width = bar_area * value / 100
            out.append(f'<g class="bar" style="fill:var(--{n})"><title>{esc(LABELS.get(n, n))}, '
                       f'{esc(CHECK_LABELS[check])}: {hits}/{total} ({value:.0f}%)</title>'
                       f'{bar_path(label_w, y, width, bar_h)}</g>'
                       f'<text class="value" x="{label_w + width + 6}" y="{y + bar_h - 2}">{value:.0f}%</text>')
            y += bar_h + gap
        y += group_gap
    out.append("</svg>")
    return "".join(out)


def legend(names):
    return '<div class="legend">' + "".join(
        f'<span><span class="chip" style="background:var(--{n})"></span>{esc(LABELS.get(n, n))}</span>'
        for n in names) + "</div>"


def trend_chart(history, names):
    runs = [h for h in history if any(n in h.get("pass_rate", {}) for n in names)]
    if len(runs) < 2:
        return (f'<p class="note">Run the eval again to see a trend: '
                f'{len(runs)} run recorded so far. Each run of <code>run_evals.py</code> adds a point.</p>')
    w, h, left, right, top, bottom = 640, 240, 44, 110, 12, 30
    plot_w, plot_h = w - left - right, h - top - bottom
    xs = [left + plot_w * i / (len(runs) - 1) for i in range(len(runs))]
    out = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Pass rate over time">']
    for v in (0, 50, 100):
        y = top + plot_h * (1 - v / 100)
        out.append(f'<line class="grid" x1="{left}" y1="{y}" x2="{left + plot_w}" y2="{y}"/>'
                   f'<text class="axis" x="{left - 8}" y="{y + 4}" text-anchor="end">{v}%</text>')
    for i, run in enumerate(runs):
        out.append(f'<text class="axis" x="{xs[i]}" y="{h - 8}" text-anchor="middle">'
                   f'{esc(run["time"][5:16].replace("T", " "))}</text>')
    end_labels = []
    for n in names:
        points = [(xs[i], top + plot_h * (1 - run["pass_rate"][n]), run)
                  for i, run in enumerate(runs) if n in run.get("pass_rate", {})]
        if not points:
            continue
        line = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in points)
        out.append(f'<polyline class="line" style="stroke:var(--{n})" points="{line}"/>')
        for x, y, run in points:
            out.append(f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="4" style="fill:var(--{n})">'
                       f'<title>{esc(LABELS.get(n, n))}, {esc(run["time"])}: '
                       f'{100 * run["pass_rate"][n]:.0f}%</title></circle>')
        end_labels.append([points[-1][1], points[-1][0], n])
    # Direct labels at each line's end, nudged apart so equal values don't overlap.
    end_labels.sort()
    for i in range(1, len(end_labels)):
        end_labels[i][0] = max(end_labels[i][0], end_labels[i - 1][0] + 14)
    for y, x, n in end_labels:
        out.append(f'<text class="value" x="{x + 10}" y="{y + 4}">{esc(LABELS.get(n, n))}</text>')
    out.append("</svg>")
    return "".join(out)


def case_grid(cases, names, outcomes, scored):
    head = "".join(f"<th>{esc(LABELS.get(n, n))}</th>" for n in names)
    rows = []
    for i, case in enumerate(cases):
        cells = []
        for n in names:
            results = [run[i] for run in scored[n]]
            outs = [run[i] for run in outcomes[n]]
            passes = sum(r["passed"] for r in results)
            failed = sorted({k for r in results for k, v in r["checks"].items() if not v})
            notes = "; ".join(dict.fromkeys(note for r in results for note in r["notes"]))
            if any("error" in o for o in outs):
                cell = '<td class="bad" title="{}">&#9888; Error</td>'.format(esc(notes))
            elif passes == len(results):
                asked = not outs[0].get("called") and case.get("clarify_ok")
                cell = f'<td class="good" title="{esc(notes)}">&#10003; Pass{" (asked)" if asked else ""}</td>'
            else:
                count = f" {passes}/{len(results)}" if len(results) > 1 else ""
                cell = (f'<td class="bad" title="{esc(notes)}">&#10007; Fail{count}: '
                        f'{esc(", ".join(CHECK_LABELS.get(c, c) for c in failed))}</td>')
            cells.append(cell)
        rows.append(f'<tr><th scope="row">{esc(case["id"])}</th><td class="muted">{esc(case["category"])}</td>'
                    f'<td class="request">{esc(case["request"])}</td>{"".join(cells)}</tr>')
    return (f'<div class="table-wrap"><table><thead><tr><th>Case</th><th>Category</th><th>Request</th>'
            f'{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def failures(cases, names, scored):
    items = []
    for n in names:
        for i, case in enumerate(cases):
            for note in dict.fromkeys(note for run in scored[n] for note in run[i]["notes"]
                                      if not run[i]["passed"] or run[i]["invented"]):
                items.append(f"<li><strong>{esc(LABELS.get(n, n))}</strong>, {esc(case['id'])}: {esc(note)}</li>")
    return "<ul>" + "".join(items) + "</ul>" if items else "<p>No failures. Time for harder cases!</p>"


def summary_table(names, summaries):
    rows = []
    for c in CHECKS:
        cells = "".join(f"<td>{summaries[n][c][0]}/{summaries[n][c][1]}</td>" for n in names)
        rows.append(f"<tr><th scope='row'>{esc(CHECK_LABELS[c])}</th>{cells}</tr>")
    head = "".join(f"<th>{esc(LABELS.get(n, n))}</th>" for n in names)
    return f'<div class="table-wrap"><table><thead><tr><th>Check</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


# ---------------------------------------------------------------------- page

CSS = """
.viz-root { color-scheme: light; --surface: #fcfcfb; --surface-2: #f3f2ef; --text: #0b0b0b;
  --text-2: #52514e; --grid: #e4e3df; --good: #0b7a0b; --bad: #c03030; %LIGHT% }
@media (prefers-color-scheme: dark) { .viz-root { color-scheme: dark; --surface: #1a1a19;
  --surface-2: #252524; --text: #f0efec; --text-2: #c3c2b7; --grid: #3a3a38; --good: #3fbf3f;
  --bad: #e66767; %DARK% } }
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface); }
.viz-root { font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; color: var(--text);
  background: var(--surface); max-width: 1000px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 1.6rem; margin: 0 0 4px; } h2 { font-size: 1.15rem; margin: 36px 0 8px; }
.meta, .note, .muted { color: var(--text-2); } .meta { margin: 0 0 20px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.tile { background: var(--surface-2); border-radius: 10px; padding: 14px 16px; }
.tile-name { font-weight: 600; display: flex; align-items: center; gap: 8px; }
.tile-value { font-size: 2.2rem; font-weight: 700; line-height: 1.1; margin-top: 6px; }
.tile-sub { color: var(--text-2); font-size: 0.85rem; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 2px 12px; margin: 10px 0 0; font-size: 0.85rem; }
dt { color: var(--text-2); } dd { margin: 0; }
.chip { display: inline-block; width: 12px; height: 12px; border-radius: 3px; }
.legend { display: flex; gap: 18px; flex-wrap: wrap; margin: 4px 0 8px; font-size: 0.9rem; }
.legend > span { display: inline-flex; align-items: center; gap: 6px; }
.chart { width: 100%; height: auto; max-width: 760px; }
.chart text { font: 12px system-ui, sans-serif; fill: var(--text-2); }
.chart .row-label { fill: var(--text); font-size: 13px; } .chart .value { fill: var(--text); }
.chart .grid { stroke: var(--grid); stroke-width: 1; }
.chart .bar:hover { opacity: 0.8; }
.chart .line { fill: none; stroke-width: 2; }
.chart .dot { stroke: var(--surface); stroke-width: 2; }
.table-wrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--grid); vertical-align: top; }
thead th { color: var(--text-2); font-weight: 600; }
td.request { min-width: 260px; } td.good { color: var(--good); font-weight: 600; white-space: nowrap; }
td.bad { color: var(--bad); font-weight: 600; }
code { background: var(--surface-2); padding: 1px 5px; border-radius: 4px; }
"""


def build(results_path, history_path, cases_path):
    cases = [json.loads(l) for l in Path(cases_path).read_text(encoding="utf-8").splitlines() if l.strip()]
    saved, outcomes = load_recording(results_path, cases)
    if not outcomes:
        sys.exit(f"No results to show in {results_path}. Run the eval first.")
    names = [n for n in ("claude", "gemini", "baseline") if n in outcomes] + \
            [n for n in outcomes if n not in COLORS]
    scored = {n: [[score(c, o) for c, o in zip(cases, run)] for run in outcomes[n]] for n in names}
    summaries = summarize(cases, names, outcomes, scored)
    history = []
    if history_path and Path(history_path).exists():
        history = [json.loads(l) for l in Path(history_path).read_text(encoding="utf-8").splitlines()
                   if l.strip()]
        # Only compare like with like: same case file and same prompt setting.
        history = [h for h in history if h.get("cases", Path(cases_path).name) == Path(cases_path).name
                   and h.get("source_boundary", True) == (saved.get("source_boundary") is not False)]

    models = saved.get("models") or {}
    model_text = ", ".join(f"{LABELS.get(k, k)}: {v}" for k, v in models.items() if v and k in names)
    boundary = saved.get("source_boundary")
    repeat = saved.get("repeat") or max((len(runs) for runs in scored.values()), default=1)
    light = " ".join(f"--{n}: {COLORS.get(n, ('#6250d6',))[0]};" for n in names)
    dark = " ".join(f"--{n}: {COLORS.get(n, ('#6250d6', '#9085e9'))[-1]};" for n in names)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kairos eval dashboard</title>
<style>{CSS.replace("%LIGHT%", light).replace("%DARK%", dark)}</style></head>
<body><main class="viz-root">
<h1>Kairos eval dashboard</h1>
<p class="meta">{esc(Path(results_path).name)} &middot; {len(cases)} cases &middot;
"today" pinned to {esc(str(saved.get("fixed_now", ""))[:10])}
{f"&middot; {esc(model_text)}" if model_text else ""}
&middot; source boundary {"off (ablation)" if boundary is False else "on"}
{f"&middot; {repeat} runs per case" if repeat > 1 else ""}</p>

<h2>At a glance</h2>
{stat_tiles(names, summaries)}

<h2>Accuracy by check</h2>
<p class="note">How often each extractor got each field right. Hover a bar for the counts.</p>
{legend(names)}
{check_bars(names, summaries)}

<h2>Pass rate over time</h2>
{legend(names) if len(history) > 1 else ""}
{trend_chart(history, names)}

<h2>Every case</h2>
<p class="note">Hover a result to see why it passed or failed.</p>
{case_grid(cases, names, outcomes, scored)}

<h2>Why each failure failed</h2>
{failures(cases, names, scored)}

<h2>Table view</h2>
{summary_table(names, summaries)}
</main></body></html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    latest = RESULTS_DIR / "latest.json"
    parser.add_argument("--results", default=str(latest if latest.exists() else SAMPLE))
    parser.add_argument("--history", default=str(RESULTS_DIR / "history.jsonl"))
    parser.add_argument("--cases", default=str(ROOT / "evals" / "cases.jsonl"))
    parser.add_argument("--out", default=str(RESULTS_DIR / "dashboard.html"))
    parser.add_argument("--no-open", action="store_true", help="don't open it in a browser")
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(args.results, args.history, args.cases), encoding="utf-8")
    print(f"Dashboard for {Path(args.results).name} written to {out}")
    if not args.no_open:
        webbrowser.open(out.resolve().as_uri())


if __name__ == "__main__":
    main()
