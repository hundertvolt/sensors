#!/usr/bin/env bash
# Builds one device's website: generates its definitions (SPECIFICATION.md H.5), stages html/ and js/
# through scripts/_stage_website.py (H.2) and freezes the stage with build_frozen_html.sh.
#
# Usage: scripts/build_website.sh [--stage-only] <device> [output]
#   <device> names a devices/<device>.toml. output is the frozen module (default frozen_modules/frozen_html.py),
#   or with --stage-only the stage directory to fill, created if absent; nothing is frozen then.
set -euo pipefail
usage="Usage: scripts/build_website.sh [--stage-only] <device> [output]"
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
    cat <<'EOF'
Usage: scripts/build_website.sh [--stage-only] <device> [output]
Builds one device's website into a frozen module.
  <device>      names a devices/<device>.toml
  output        the frozen module written (default: frozen_modules/frozen_html.py)
  --stage-only  stage the page and bundle into the directory output names instead; nothing is frozen
EOF
    exit 0
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."

stage_only=false
if [ "${1:-}" = "--stage-only" ]; then
    stage_only=true
    shift
fi
if [ $# -lt 1 ] || { $stage_only && [ $# -lt 2 ]; } || [ $# -gt 2 ]; then
    echo "error: $usage (--stage-only needs the stage directory)" >&2
    exit 2
fi
device="$1"

scratch_dir="$(mktemp -d)"
trap 'rm -rf "$scratch_dir"' EXIT

# Every device's definitions are generated from its TOML and the src/ tags, never hand-kept.
device_toml="devices/${device}.toml"
if [[ ! -f "$device_toml" ]]; then
    echo "error: no $device_toml" >&2
    exit 1
fi
# A sibling of the stage, never inside it: the stage is the served /html root and gets frozen whole, so a
# definitions.json there would ship as /definitions.json.gz and defeat H.7's inlining.
definitions_src="$scratch_dir/definitions.json"
python3 -m buildgen.definitions "$device_toml" --src-dir src --out "$definitions_src"

if $stage_only; then
    python3 scripts/_stage_website.py "$definitions_src" "$2"
    exit 0
fi
out_file="${2:-frozen_modules/frozen_html.py}"
python3 scripts/_stage_website.py "$definitions_src" "$scratch_dir/stage"
HTML_SRC_DIRS="$scratch_dir/stage" scripts/build_frozen_html.sh "$out_file"
