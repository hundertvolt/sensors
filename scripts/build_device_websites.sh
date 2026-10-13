#!/usr/bin/env bash
# Builds every derived device's website (each devices/*.toml except the zz_test_ fixtures) through
# scripts/build_website.sh into <out_root>/<device>/frozen_html.py, or with --stage-only stages each into
# <out_root>/<device>/ and freezes nothing; stops at the first failure, naming that device.
set -euo pipefail

usage() {
    cat <<'EOF_USAGE'
Usage: scripts/build_device_websites.sh [--stage-only] [out_root]

  out_root      where each device's frozen_html.py lands (default: build/generated_html), or with
                --stage-only where each device's staged index.html and js/app.js land (default: build/staged_html)
  --stage-only  stage every device's page and bundle without freezing them (what html-validate lints)
  -h, --help    this text

Builds every devices/*.toml device except the zz_test_ fixtures through scripts/build_website.sh;
stops at the first failure, naming that device.
EOF_USAGE
}
stage_only=false
case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    --stage-only) stage_only=true; shift ;;
    -*) echo "error: unknown option $1" >&2; usage >&2; exit 2 ;;
esac
[ $# -le 1 ] || { echo "error: at most one out_root, got $#" >&2; usage >&2; exit 2; }
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if $stage_only; then
    out_root="${1:-build/staged_html}"
else
    out_root="${1:-build/generated_html}"
fi
device=""
trap 'status=$?; if (( status != 0 )) && [[ -n "$device" ]]; then echo "error: the website build for device $device failed" >&2; fi' EXIT

for toml in devices/*.toml; do
    device="$(basename "$toml" .toml)"
    if [[ "$device" == zz_test_* ]]; then
        continue
    fi
    if $stage_only; then
        scripts/build_website.sh --stage-only "$device" "$out_root/$device"
    else
        scripts/build_website.sh "$device" "$out_root/$device/frozen_html.py"
    fi
done
device=""
