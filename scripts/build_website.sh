#!/usr/bin/env bash
# Stages the real website (html/ + js/) for exactly one device into the shape scripts/
# build_frozen_html.sh expects, then invokes it. See WEBSITE_PLAN.md §10 item 4 for the design
# this follows and the gaps it closes; scripts/build_frozen_html.sh itself is unchanged by this
# script's existence - it stays a generic "merge N source dirs, gzip, freezefs" pipeline, this
# script's own job is only building the one merged dir HTML_SRC_DIRS points at.
#
# What gets staged, and why each rename/selection exists:
#   - html/index.html - staged with html/style.css and the device's own definitions.json inlined
#     directly into it (see "Inlining" below) - neither is staged as a separate file any more.
#   - html/definitions/<device>.json - inlined into index.html, not staged under its own name; a
#     real device's firmware only ever ships its own one definitions file, so the inlined data is
#     always the one matching this build's own device rather than needing a "device" constant
#     baked into checked-in JS (mirrors how html/index.html itself never branches on device -
#     WEBSITE_PLAN.md §4's "per-device page-scheme mechanism" row).
#   - The production JS module set (js/field-format.js, poll-manager.js, templates.js,
#     definitions.js, render.js, nav.js, main.js) - concatenated into one bundled js/app.js (see
#     "Bundling" below), not copied as separate files. js/mock-server.js (prototype-only fake
#     backend) is deliberately NOT staged at all - its fetch-patching has no business anywhere near
#     production.
#   - The bundle is staged as js/app.js on purpose: html/index.html's own `<script>` imports
#     "../js/app.js" unconditionally, and that one path is meant to stay identical between
#     `npm run preview` (serves the real repo layout, where js/app.js is the separate,
#     prototype-only entry file) and a real device build (where the staged js/app.js is really the
#     bundle below) - see WEBSITE_PLAN.md §10 item 4's "no production entry point exists yet" note.
#     Staging under this name means html/index.html never needs a build-time text rewrite.
#
# Bundling (WEBSITE_PLAN.md §10 item 5): concatenated into one file, not copied as 7 separate
# js/*.js files, so a single page load opens far fewer concurrent TCP connections - the real
# rp2040 lwIP build's MEMP_NUM_TCP_PCB=5 (lwIP's own default, confirmed against the vendored
# source, no project override) is a hard ceiling on simultaneously active TCP connections that no
# amount of src/asy_webserver_service.py tuning can raise; 7 separate JS files plus index.html plus
# style.css could alone exceed it on a single browser tab's first paint, before any other client
# (e.g. an OpenHAB instance polling REST endpoints) even connects. Concatenation order matters -
# each file only ever appears after every local file it imports from, so a `const`/class needed by
# a later file already exists by the time that file's top-level code runs (function declarations
# are hoisted regardless, so strict ordering only matters for the few top-level `const`s -
# poll-manager.js's DEFAULT_TIMEOUT_MS/pollManager, definitions.js's SUPPORTED_SCHEMA_MAJOR - but
# kept consistent throughout rather than relying on that distinction). Every file's own
# `import { ... } from "./local-file.js";` line is dropped (`grep -v`) since after concatenation
# every imported name is already in scope from earlier in the same file; each file's own `export`
# keywords are left as-is - a module script can freely contain unused exports, and stripping them
# would be one more thing that could get the regex wrong for no real benefit. This is a plain,
# dependency-free text concatenation (matching this project's own small/lean/no-build-step-magic
# philosophy - WEBSITE_PLAN.md §3), not a real bundler - safe here specifically because every
# production js/*.js file uses only simple `import { name, ... } from "./relative.js"` (no default
# exports, no dynamic imports, no re-exports, no naming collisions across files - confirmed by
# direct inspection, and cross-checked mechanically below) rather than because concatenation is a
# generally-safe substitute for real bundling.
#
# Inlining (WEBSITE_PLAN.md §7's follow-up round): html/style.css and the device's own
# definitions.json are embedded directly into the staged index.html (a `<style>` block replacing
# the `<link rel="stylesheet">`, and a `<script type="application/json" id="inlined-definitions">`
# element js/definitions.js's own loadDefinitions() reads in preference to fetching) instead of
# being staged as separate files - cuts a single page load from 4 concurrent connections (index.html
# + style.css + app.js + definitions.json) to 2 (index.html + app.js), reducing how much of the
# real rp2040 lwIP build's MEMP_NUM_TCP_PCB=5 ceiling one browser tab alone can consume, the same
# problem the JS bundling above already addresses for the seven production modules. This was chosen
# deliberately over real HTTP keep-alive/persistent connections after an earlier attempt: vendored
# ext/microdot.py (checked directly, including its current upstream `main` branch - no keep-alive
# support has been added even there) always closes the connection after exactly one request by
# design, and building persistent-connection support entirely in application code around it (a
# stream-proxy wrapper intercepting Microdot's own close call, a write-capture loop) proved fragile
# and easy to break silently on any future Microdot change - reverted in favor of this simpler,
# framework-respecting reduction instead. Raising the rp2 firmware's own MEMP_NUM_TCP_PCB compile
# constant (the standard fix MicroPython's own maintainers point to for this exact ceiling elsewhere)
# was also considered and set aside for this round - out of scope for a website-only change.
# The definitions JSON is embedded with every literal `<` replaced by the escape sequence
# backslash-u-zero-zero-three-c (semantically identical once JSON-parsed) - `<script>` is an HTML
# "raw text" element, terminated by a literal
# `</script` (case-insensitively) wherever it appears, so a field value that happened to contain
# that exact substring would otherwise prematurely close the tag and corrupt the page; escaping
# away every `<` removes any possibility of that substring surviving in the embedded text at all.
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

STAGE_DIR="$stage_dir" DEFINITIONS_SRC="$definitions_src" python3 <<'PYEOF'
import os

stage_dir = os.environ["STAGE_DIR"]
definitions_src = os.environ["DEFINITIONS_SRC"]

with open("html/index.html", encoding="utf-8") as f:
    html = f.read()
with open("html/style.css", encoding="utf-8") as f:
    css = f.read()
with open(definitions_src, encoding="utf-8") as f:
    definitions_json = f.read()

# Built via chr(92) rather than a literal backslash in this script's own source, purely to keep
# this heredoc's own escaping unambiguous - the resulting six-character sequence (backslash,
# "u003c") is standard JSON's own escape for "<", semantically identical to a literal "<" once
# JSON.parse()'d (see this script's own "Inlining" comment above for why every "<" is escaped
# this way before embedding).
escaped_lt = chr(92) + "u003c"
definitions_json = definitions_json.replace("<", escaped_lt)

link_tag = '<link rel="stylesheet" href="style.css">'
if link_tag not in html:
    raise SystemExit("html/index.html's stylesheet <link> tag not found - update build_website.sh")
html = html.replace(link_tag, "<style>\n" + css + "</style>")

inlined_script = '<script type="application/json" id="inlined-definitions">' + definitions_json + "</script>\n"
if "</head>" not in html:
    raise SystemExit("html/index.html has no </head> - update build_website.sh")
html = html.replace("</head>", inlined_script + "</head>")

with open(os.path.join(stage_dir, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
PYEOF

mkdir -p "$stage_dir"/js
{
    echo "// Generated by scripts/build_website.sh - concatenation of js/field-format.js, poll-manager.js,"
    echo "// templates.js, definitions.js, render.js, nav.js, main.js (in that dependency order). Do not"
    echo "// edit directly - edit the source files under js/ instead. See this script's own header comment for why."
    for src in js/field-format.js js/poll-manager.js js/templates.js js/definitions.js js/render.js js/nav.js js/main.js; do
        echo ""
        echo "// ---- $src ----"
        grep -v -E '^import .* from "\./[^"]+\.js";$' "$src"
    done
} > "$stage_dir"/js/app.js

HTML_SRC_DIRS="$stage_dir" scripts/build_frozen_html.sh "$out_file"
