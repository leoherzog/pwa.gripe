# AGENTS.md

This file provides guidance to Claude Code, Codex, Gemini, etc when working with code in this repository.

## What This Is

pwa.gripe is a static site that shows PWA feature support across Chrome Android, Safari iOS, and the visitor's own browser. The fixed columns come from caniuse data at build time. The "Your Browser" column comes from runtime feature detection in JavaScript.

## Build

```bash
uv run build/build.py
```

This downloads caniuse `data-2.0.json` and renders `index.html`. It needs Python 3.12+; inline script metadata (PEP 723) lets `uv run` install Jinja2. There is no npm/node toolchain, bundler, test suite, or linter.

## Architecture

- **`build/build.py`**: the `FEATURES` list of `Feature` records and the build. Fixed columns read each browser's `current_version` in caniuse, not the newest listed version, which may be unreleased. Partial support carries the caniuse footnotes as a tooltip. The build fails on an unknown caniuse id.
- **`build/template.html.j2`**: renders the table with Pico CSS. Feature names are row headers with their description as visible text. A small inline head script applies the saved theme before first paint.
- **`index.html`**: generated and untracked. Never edit it; re-run the build.
- **`app.js`**: ES module. Evaluates each `data-detect` expression to fill the "Your Browser" column, runs the auto/light/dark theme toggle, and registers the service worker.
- **`sw.js`**: network-first for same-origin requests, cache-first for the pinned Pico stylesheet. Bump `CACHE_NAME` when `PRECACHE` changes.
- **`manifest.json`**, **`icons/`**, **`screenshots/`**: install metadata. Regenerate the screenshots when the layout changes noticeably.
- **`.github/workflows/update-data.yml`**: rebuilds and deploys to GitHub Pages on push and weekly. A keepalive job re-enables the workflow so GitHub does not disable the schedule. Only the files copied into `_site/` are published.

## Adding a New Feature

Add a `Feature` to `FEATURES` in `build/build.py`:

```python
Feature("Display Name", "One-sentence description.", f"{MDN}/Web/API/Some_API",
        caniuse="caniuse-id", detect="'SomeAPI' in window"),
```

Without a caniuse id, set both `android` and `ios`. Setting either on a caniuse feature overrides caniuse for that column, for when its data is stale. Leave `detect` out only when no JavaScript check exists; the cell then shows unknown. Re-run the build.

## Key Details

- CSS: Pico CSS 2.1.1 from jsDelivr, pinned with SRI. Prefer Pico classes, elements and variables over custom CSS.
- Icons: Unicode ✔ ✘ ⚠ ?, with U+FE0E after ✔, ⚠ and ☀ so they render as recolorable text, not emoji.
- Support values: `y` (supported), `a` (partial), `n` (no). Flagged, polyfill-only and unknown caniuse values count as `n`.
- Detect expressions run in the page and return true or false. One that fails to compile shows unknown and logs an error.
