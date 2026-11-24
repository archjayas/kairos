"""MkDocs hooks for the Kairos website.

1. Code links: doc pages link to code with relative paths like ../claude_agent.py,
   so the links work on GitHub. A docs site only contains docs/, so those links
   would break there. Any link that leads outside docs/ becomes a GitHub link,
   built from repo_url in mkdocs.yml.

2. Badges on the home page: the <!-- KAIROS_BADGES --> marker in docs/index.md
   becomes a row of badges.
   - `mkdocs serve` (local preview): shows YOUR badges, from .kairos/progress.json.
   - `mkdocs build` / `gh-deploy` (publishing): shows all five as a showcase. Your
     personal progress is never baked into a published site.
"""

import html
import posixpath
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kairos_progress import BADGES, PROGRESS_FILE, earned_badges, load  # noqa: E402
from progress import badge_svg  # noqa: E402

LINK = re.compile(r"\]\((?!https?://|mailto:|#)([^)\s#]+)(#[^)\s]*)?\)")
BADGE_MARKER = "<!-- KAIROS_BADGES -->"
esc = html.escape
command = "build"


def on_startup(command, dirty):  # noqa: F811 (MkDocs passes the command name)
    globals()["command"] = command


def on_serve(server, config, builder):
    """With `mkdocs serve`, also watch the progress folder, so earning a badge
    rebuilds the site and reloads the browser. No restart needed."""
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)  # .kairos/ is git-ignored
    server.watch(str(PROGRESS_FILE.parent))
    return server


def badges_html(on_progress_page=False):
    personal = command == "serve"
    progress = load() if personal else {"milestones": {}}
    done = progress.get("milestones", {})
    earned = {b["id"] for b in earned_badges(progress)}

    items = []
    for badge in BADGES:
        got = badge["id"] in earned
        if got:
            status = "Earned " + max(done[m].get("first", "") for m in badge["needs"])[:10]
        else:
            status = "Not earned yet" if personal else "Earn it as you go"
        locked = personal and not got
        how = "" if got else f'<span class="kairos-tip-how">How: {esc(badge["earn"])}</span>'
        items.append(
            f'<li class="kairos-badge{" locked" if locked else ""}" tabindex="0" '
            f'aria-label="{esc(badge["name"])}. {esc(status)}. {esc(badge["about"])}">'
            f'{badge_svg(badge, not locked)}'
            f'<span class="kairos-badge-name">{esc(badge["name"])}</span>'
            f'<span class="kairos-tip" role="tooltip"><strong>{esc(badge["name"])}</strong>'
            f'<span class="kairos-tip-status">{esc(status)}</span>'
            f'<span>{esc(badge["about"])}</span>{how}</span></li>'
        )

    if personal:
        intro = (f"You've earned <strong>{len(earned)} of {len(BADGES)}</strong> badges. "
                 "Hover a badge to see what it means. Run <code>python progress.py</code> for your full journey.")
    else:
        intro = ("Earn five badges as you learn. Kairos notices what you do and awards them "
                 "automatically. Hover a badge to see what it means. <em>This is a preview: "
                 "your own badges stay on your computer. To see them, run "
                 "<code>python progress.py</code>, or preview this site locally with "
                 "<code>mkdocs serve</code>.</em>")
    # Keep it one HTML block with no blank lines, so Markdown leaves it alone.
    return (f'<div class="kairos-badges"><p>{intro}</p>'
            f'<ul class="kairos-badge-row">{"".join(items)}</ul>'
            + ("" if on_progress_page else '<p class="kairos-badges-more"><a href="progress/">How badges work</a></p>')
            + "</div>")


def on_page_markdown(markdown, page, config, files):
    if BADGE_MARKER in markdown:
        markdown = markdown.replace(BADGE_MARKER, badges_html(page.file.src_uri == "progress.md"))

    repo_url = config["repo_url"].rstrip("/")
    page_dir = posixpath.dirname(page.file.src_uri)

    def rewrite(match):
        target, anchor = match.group(1), match.group(2) or ""
        # Where the link points, relative to the repo root (docs/ is one level down).
        from_root = posixpath.normpath(posixpath.join("docs", page_dir, target))
        if from_root == "docs" or from_root.startswith(("docs/", "..", "/")):
            return match.group(0)  # a docs page, or outside the repo: leave it alone
        kind = "tree" if target.endswith("/") else "blob"
        return f"]({repo_url}/{kind}/main/{from_root}{anchor})"

    return LINK.sub(rewrite, markdown)
