#!/usr/bin/env bash
# Builds every derived device's website (each devices/*.toml except the zz_test_ fixtures) through
# scripts/build_website.sh into <out_root>/<device>/frozen_html.py, or with --stage-only stages each into
# <out_root>/<device>/ and freezes nothing; stops at the first failure, naming that device.
set -euo pipefail

usage() {
    cat <<'EOF_USAGE'
Usage: scripts/build_device_websites.sh [--stage-only] [out_root]

  out_root      where each device's frozen_html.py lands (default: build/generated_html), or with
                --stage-only where each device's staged index.html and js/app.js land (default: build/staged_html),
                every staged page under it removed first, so no removed device's page stays behind
  --stage-only  stage every device's page and bundle without freezing them (what html-validate lints)
  -h, --help    this text

Builds every devices/*.toml device except the zz_test_ fixtures through scripts/build_website.sh;
stops at the first failure, naming that device. Each device's intermediates go to
$WEBSITE_WORK_ROOT/<device> (default: build/website/<device>).
EOF_USAGE
}
stage_only=false
case "${1:-}" in
    -h | --help)
        usage
        exit 0
        ;;
    --stage-only)
        stage_only=true
        shift
        ;;
    -*)
        echo "error: unknown option $1" >&2
        usage >&2
        exit 2
        ;;
esac
if [ "$#" -gt 1 ]; then
    echo "error: at most one out_root, got $# arguments" >&2
    usage >&2
    exit 2
fi
cd "$(dirname "${BASH_SOURCE[0]}")/.."
# shellcheck source=/dev/null  # linted on its own, as one of scripts/*.sh
source scripts/_devices.sh
mapfile -t devices < <(derived_devices)
[ "${#devices[@]}" -gt 0 ] || exit 1

if $stage_only; then
    out_root="${1:-build/staged_html}"
    # Cleaned at the start, never at the end: every staged page under the root goes (html-validate globs each
    # <out_root>/*/index.html), and only those, since out_root may be any directory the caller names.
    for page in "$out_root"/*/index.html; do
        if [ -f "$page" ]; then
            rm -rf "$(dirname "$page")"
        fi
    done
else
    out_root="${1:-build/generated_html}"
fi
work_root="${WEBSITE_WORK_ROOT:-build/website}"
device=""
trap 'status=$?; if (( status != 0 )) && [[ -n "$device" ]]; then echo "error: the website build for device $device failed" >&2; fi' EXIT

# build_website.sh checks each name itself (require_device) before it builds anything.
for device in "${devices[@]}"; do
    if $stage_only; then
        WEBSITE_WORK_DIR="$work_root/$device" scripts/build_website.sh --stage-only "$device" "$out_root/$device"
    else
        WEBSITE_WORK_DIR="$work_root/$device" scripts/build_website.sh "$device" "$out_root/$device/frozen_html.py"
    fi
done
device=""
