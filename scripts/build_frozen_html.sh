#!/usr/bin/env bash
# Builds the frozen static-content module the firmware serves (SPECIFICATION.md Part A.9, which
# owns the whole pipeline: the freezefs invocation, why never --compress, and why the output goes to
# frozen_modules/ rather than the .frozen/ import sentinel).
#
# Usage: HTML_SRC_DIRS="dir ..." scripts/build_frozen_html.sh [output_path]   # default frozen_modules/frozen_html.py
# HTML_SRC_DIRS is required (scripts/build_website.sh sets it): a space-separated list merged
# recursively into one build tree. Output is a gitignored build artifact, never committed.
#
# ext/freezefs is vendored and unmodified. Don't copy build-wozi.sh's literal invocation: that
# legacy pipeline predates freezefs 2.4's current CLI (its "-s" flag is gone).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

src_dirs="${HTML_SRC_DIRS:?HTML_SRC_DIRS must name the source dir(s) - scripts/build_website.sh sets it}"
out_file="${1:-frozen_modules/frozen_html.py}"
mount_target="/html"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

for src_dir in $src_dirs; do
    cp -r "$src_dir"/. "$tmp_dir"/
done
find "$tmp_dir" -type f -exec gzip -9 {} +

mkdir -p "$(dirname "$out_file")"
rm -f "$out_file"

# ext/freezefs has no __init__.py (freezefs 2.4 upstream ships it as an implicit namespace
# package) - PYTHONPATH=ext is what makes `python -m freezefs` resolve it, confirmed directly
# against the vendored copy (see ext/freezefs/__main__.py: `from freezefs.archive import main`).
PYTHONPATH="ext${PYTHONPATH:+:$PYTHONPATH}" python3 -m freezefs "$tmp_dir" "$out_file" \
    --on-import mount --target "$mount_target" --overwrite always --silent

echo "Wrote $out_file (mounts at $mount_target on import)"
