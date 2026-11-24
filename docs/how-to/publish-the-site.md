# Publish the site

The Kairos website, with its home page of cards, search, and dark mode, is built from
the Markdown files in `docs/` with [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).
The result is a folder of plain HTML that you can host anywhere.

## 1. Install the site tools

These are separate from the agent's packages. With your virtual environment active:

```bash
pip install -r requirements-docs.txt
```

## 2. Set your repo URL

In `mkdocs.yml`, change `repo_url` to your repository:

```yaml
repo_url: https://github.com/your-username/kairos
```

Every link to a code file on the site is built from this one line.
(The docs link to code with relative paths like `../claude_agent.py`, which work on
GitHub. `mkdocs_hooks.py` turns them into GitHub links when the site is built.)

## 3. Preview it locally

```bash
mkdocs serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The page reloads as you edit any
file in `docs/`.

## 4. Publish

### GitHub Pages (one command)

```bash
mkdocs gh-deploy
```

This builds the site and pushes it to a `gh-pages` branch. In your repository on
GitHub, go to **Settings → Pages** and set the source to the `gh-pages` branch. The
site appears at `https://your-username.github.io/kairos/`.

### Any other host

```bash
mkdocs build --strict
```

This writes the whole site to a `site/` folder. Upload that folder to any static
host, such as Netlify, Vercel, Cloudflare Pages, or a plain web server. On hosts that
build for you, use:

| Setting | Value |
|---|---|
| Build command | `pip install -r requirements-docs.txt && mkdocs build --strict` |
| Output folder | `site` |

`--strict` stops the build on any broken link or missing page, so a broken site never
gets published. `site/` is git-ignored; it's rebuilt every time.

## How the site is organized

| Part | Where it comes from |
|---|---|
| **The menu across the top** | The top-level entries under `nav:` in `mkdocs.yml`. Each one is a tab. Keep the labels short so the row fits |
| **The sidebar** | The pages inside the current tab |
| **Breadcrumbs** above each title | Built automatically from `nav:` (for example *Home › Extend*) |
| **The quick-access bar** on every page | The links in `overrides/main.html`. Edit that list to change them |
| **The home page** | `docs/index.md`: the banner and the grouped cards |
| **Badges on the home page** | `mkdocs_hooks.py` fills in the `<!-- KAIROS_BADGES -->` marker. With `mkdocs serve`, it shows your own badges; with `mkdocs build` or `gh-deploy`, all five as a preview, so personal progress is never published |

## Add a page

1. Create the Markdown file in `docs/` (or `docs/how-to/`).
2. Add it under the right tab in `nav:` in `mkdocs.yml`, so it appears in the menu.
3. To show it on the home page, add a link to the right card in `docs/index.md`. The
   cards are grouped by audience: *Start here* (beginner), *Go further* (advanced),
   and *Help and updates*. Keep each card to a handful of links; if one grows past
   five or six, it's probably two cards.
4. Add a line to [Release notes](../release-notes.md).

Card icons come from the [Material Design icon set](https://pictogrammers.com/library/mdi/).
Use the icon's name as `:material-icon-name:`.

## A note on the site tool's future

Material for MkDocs reaches end of life on May 5, 2027, and prints a notice saying so
when you build. Its maintained successor, [Zensical](https://zensical.org), is from the
same team and reads the same `mkdocs.yml`, so the site can move over without
rewriting any pages. To hide the notice, set `NO_MKDOCS_2_WARNING=1`.

## Related

- [Release notes](../release-notes.md)
- [Overview](../overview.md)
