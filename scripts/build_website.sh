#!/usr/bin/env bash
# Stages the real website (html/ + js/) for exactly one device into the shape scripts/
# build_frozen_html.sh expects, then invokes it. See WEBSITE_PLAN.md §10 item 4 for the design
# this follows and the gaps it closes; scripts/build_frozen_html.sh itself is unchanged by this
# script's existence - it stays a generic "merge N source dirs, gzip, freezefs" pipeline, this
# script's own job is only building the one merged dir HTML_SRC_DIRS points at.
#
# What gets staged, and why each rename/selection exists:
#   - html/index.html, html/style.css - copied verbatim.
#   - html/definitions/<device>.json -> definitions.json (renamed, no "definitions/" nesting) -
#     a real device's firmware only ever ships its own one definitions file, so js/main.js fetches
#     a fixed "definitions.json" rather than needing a "device" constant baked into checked-in JS
#     (mirrors how html/index.html itself never branches on device - WEBSITE_PLAN.md §4's
#     "per-device page-scheme mechanism" row).
#   - The production JS module set (js/definitions.js, poll-manager.js, render.js, templates.js,
#     nav.js) - copied verbatim into js/. js/app.js (prototype: mock fetch, `?device=` switch,
#     dev-server-relative paths) and js/mock-server.js (prototype-only fake backend) are
#     deliberately NOT staged - shipping either would be dead weight against §3's "stays small,
#     lean" goal, and mock-server.js's fetch-patching has no business anywhere near production.
#   - js/main.js (the real entry point) -> js/app.js - renamed on purpose: html/index.html's own
#     `<script>` imports "../js/app.js" unconditionally, and that one file is meant to stay
#     identical between `npm run preview` (serves the real repo layout, where js/app.js is the
#     prototype entry) and a real device build (where the staged tree's js/app.js is really
#     main.js's content) - see WEBSITE_PLAN.md §10 item 4's "no production entry point exists yet"
#     note. Renaming at staging time means html/index.html never needs a build-time text rewrite.
#
# Usage: scripts/build_website.sh <device> [output_path]
#   <device>     matches an html/definitions/<device>.json file, e.g. "wozi".
#   output_path  forwarded to build_frozen_html.sh (default: frozen_modules/frozen_html.py).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

device="${1:?Usage: scripts/build_website.sh <device> [output_path]}"
out_file="${2:-frozen_modules/frozen_html.py}"

definitions_src="html/definitions/${device}.json"
if [[ ! -f "$definitions_src" ]]; then
    echo "error: no definitions file at $definitions_src" >&2
    exit 1
fi

stage_dir="$(mktemp -d)"
trap 'rm -rf "$stage_dir"' EXIT

cp html/index.html html/style.css "$stage_dir"/
cp "$definitions_src" "$stage_dir"/definitions.json

mkdir -p "$stage_dir"/js
cp js/definitions.js js/poll-manager.js js/render.js js/templates.js js/nav.js "$stage_dir"/js/
cp js/main.js "$stage_dir"/js/app.js

HTML_SRC_DIRS="$stage_dir" scripts/build_frozen_html.sh "$out_file"
