#!/usr/bin/env bash
# Builds one device's website: stages the definitions the generator wrote (SPECIFICATION.md H.5, generating them first
# when its stamp no longer holds) with html/ and js/ through scripts/_stage_website.py (H.2) and freezes the stage
# with build_frozen_html.sh. Intermediates stay in build/website/<device>/ (or $WEBSITE_WORK_DIR) until its next build.
set -euo pipefail
usage="Usage: scripts/build_website.sh [--stage-only] <device> [output]"
help() {
    cat <<'EOF'
Usage: scripts/build_website.sh [--stage-only] <device> [output]
Builds one device's website into a frozen module.
  <device>            names a devices/<device>.toml
  output              the frozen module written (default: frozen_modules/frozen_html.py)
  --stage-only        stage the page and bundle into the directory output names instead; nothing is frozen
Environment:
  WEBSITE_WORK_DIR    the intermediates, wiped at the start and kept (default: build/website/<device>)
EOF
}

stage_only=false
positional=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        -h | --help)
            help
            exit 0
            ;;
        --stage-only) stage_only=true ;;
        -*)
            echo "error: unknown option $1 - $usage" >&2
            exit 2
            ;;
        *) positional+=("$1") ;;
    esac
    shift
done
if [ "${#positional[@]}" -lt 1 ] || { $stage_only && [ "${#positional[@]}" -lt 2 ]; } || [ "${#positional[@]}" -gt 2 ]; then
    echo "error: $usage (--stage-only needs the stage directory)" >&2
    exit 2
fi
device="${positional[0]}"
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_devices.sh
require_device "$device"
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_require_python.sh
require_python311

# One build of a device at a time: a second waits for the first, then wipes and rebuilds the same tree.
work="${WEBSITE_WORK_DIR:-build/website/$device}"
mkdir -p "$(dirname "$work")"
exec {work_lock}>"$work.lock"
flock "$work_lock"
rm -rf "$work"
mkdir -p "$work"
echo "== Website work dir: $work"

# Every device's definitions are generated from its TOML and the src/ tags, never hand-kept: the generator's own copy,
# outside the stage (the served /html root, frozen whole; H.7 inlines the definitions).
python3 scripts/_generate_sensortask_modules.py --if-stale
definitions="build/generated_src/definitions/$device.json"

if $stage_only; then
    python3 scripts/_stage_website.py "$definitions" "${positional[1]}"
    exit 0
fi
out_file="${positional[1]:-frozen_modules/frozen_html.py}"
python3 scripts/_stage_website.py "$definitions" "$work/stage"
HTML_SRC_DIRS="$work/stage" FROZEN_HTML_WORK_DIR="$work/gzipped" scripts/build_frozen_html.sh "$out_file"
