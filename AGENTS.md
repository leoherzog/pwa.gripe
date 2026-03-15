# AGENTS.md

This file provides guidance to Claude Code, Codex, Gemini, etc when working with code in this repository.

## What This Is

pwa.gripe is a static site that shows PWA feature support across browsers (Chrome Android, Safari iOS, and the visitor's own browser). The "Your Browser" column prefers runtime feature detection via JavaScript, falling back to caniuse data only when no detect expression exists.

## Build

The site is built with a Python script that fetches caniuse data and renders `index.html` from a Jinja2 template:

```bash
uv run build/build.py
```

This requires Python 3.12+ and uses inline script metadata (PEP 723) so `uv run` handles dependencies automatically (`requests`, `jinja2`).

There is no npm/node toolchain, no bundler, no test suite, and no linter.

## Architecture

- **`build/build.py`** — Build script. Downloads caniuse `data-2.0.json`, extracts support data for each feature (including `notes_by_num` footnotes for partial-support tooltips), and renders the template. The `FEATURES` list defines all tracked features as `(display_name, caniuse_id, detect_expression)` tuples. Features without a caniuse ID use the `HARDCODED` dict for Chrome/Safari support values.
- **`build/template.html.j2`** — Jinja2 template for `index.html`. Renders the feature table with static Chrome/Safari columns, embeds trimmed caniuse stats (with `_notes`) as a JSON blob (`<script type="application/json" id="caniuse-data">`), and uses Pico CSS `data-tooltip` for caniuse footnotes on partial-support entries.
- **`index.html`** — Generated output (do not edit directly; re-run `build/build.py`).
- **`app.js`** — Client-side JS (vanilla, no framework). Prefers runtime `detect` expressions for the "Your Browser" column, falling back to Bowser UA parsing + caniuse JSON lookup. Resolves caniuse footnotes as tooltips for partial-support results. Also handles the theme toggle (cycles auto/light/dark).

## Adding a New Feature

Add a tuple to the `FEATURES` list in `build/build.py`:
```python
("Display Name", "caniuse-id-or-None", "'SomeAPI' in window")
```
If no caniuse ID exists, add an entry to `HARDCODED` for Chrome/Safari values. Then re-run the build.

## Key Details

- CSS framework: Pico CSS v2 (CDN)
- Icons: Font Awesome 7 (CDN, SVG/JS) with Unicode fallback text — note FA replaces `<span>` with `<svg>`, so dynamic icon changes must create new spans (FA's MutationObserver auto-converts them)
- UA parsing: Bowser v2 (CDN)
- All iOS/iPadOS browsers map to `ios_saf` (WebKit requirement)
- Support values: `y` (supported), `a` (partial), `n` (no), `d` (behind flag), `u` (unknown)
