#!/usr/bin/env bash
# Builds one device's website: generates its definitions (SPECIFICATION.md H.5), stages html/ and js/ through
# scripts/_stage_website.py (H.2) and freezes the stage with build_frozen_html.sh. Intermediates stay in
# build/website/<device>/ (or $WEBSITE_WORK_DIR) until that device's next build.
set -euo pipefail
usage="Usage: scripts/build_website.sh [--stage-only] [--build-date STAMP] <device> [output]"
help() {
    cat <<'EOF'
Usage: scripts/build_website.sh [--stage-only] [--build-date STAMP] <device> [output]
Builds one device's website into a frozen module.
  <device>            names a devices/<device>.toml
  output              the frozen module written (default: frozen_modules/frozen_html.py)
  --stage-only        stage the page and bundle into the directory output names instead; nothing is frozen
  --build-date STAMP  stamp the firmware build's UTC date (YYYY-MM-DDTHH:MM:SSZ) into the page; none by default
Environment:
  WEBSITE_WORK_DIR    the intermediates, wiped at the start and kept (default: build/website/<device>)
EOF
}

stage_only=false
build_date=""
positional=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        -h | --help)
            help
            exit 0
            ;;
        --stage-only) stage_only=true ;;
        --build-date)
            if [ "$#" -lt 2 ]; then
                echo "error: --build-date needs a UTC stamp - $usage" >&2
                exit 2
            fi
            build_date="$2"
            shift
            ;;
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
mkdir -p "$work/scratch"
echo "== Website work dir: $work"

# Every device's definitions are generated from its TOML and the src/ tags, never hand-kept. A sibling of the stage,
# never inside it: the stage is the served /html root and gets frozen whole (H.7 inlines the definitions).
definitions="$work/scratch/definitions.json"
python3 -m buildgen.definitions "devices/$device.toml" --src-dir src --out "$definitions"
stamp=()
if [ -n "$build_date" ]; then
    stamp=(--build-date "$build_date")
fi

if $stage_only; then
    python3 scripts/_stage_website.py "${stamp[@]}" "$definitions" "${positional[1]}"
    exit 0
fi
out_file="${positional[1]:-frozen_modules/frozen_html.py}"
python3 scripts/_stage_website.py "${stamp[@]}" "$definitions" "$work/stage"
HTML_SRC_DIRS="$work/stage" FROZEN_HTML_WORK_DIR="$work/gzipped" scripts/build_frozen_html.sh "$out_file"
