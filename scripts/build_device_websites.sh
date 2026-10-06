#!/usr/bin/env bash
# Builds every derived device's website (each devices/*.toml except the zz_test_ fixtures) through
# scripts/build_website.sh into <out_root>/<device>/frozen_html.py; stops at the first failure, naming that device.
#
set -euo pipefail

usage() {
    cat <<'EOF_USAGE'
Usage: scripts/build_device_websites.sh [out_root]

  out_root    where each device's frozen_html.py lands (default: build/generated_html)
  -h, --help  this text

Builds every devices/*.toml device except the zz_test_ fixtures through scripts/build_website.sh;
stops at the first failure, naming that device.
EOF_USAGE
}
case "${1:-}" in
    -h|--help) usage; exit 0 ;;
    -*) echo "error: unknown option $1" >&2; usage >&2; exit 2 ;;
esac
[ $# -le 1 ] || { echo "error: at most one out_root, got $#" >&2; usage >&2; exit 2; }
cd "$(dirname "${BASH_SOURCE[0]}")/.."

out_root="${1:-build/generated_html}"
device=""
trap 'status=$?; if (( status != 0 )) && [[ -n "$device" ]]; then echo "error: the website build for device $device failed" >&2; fi' EXIT

for toml in devices/*.toml; do
    device="$(basename "$toml" .toml)"
    if [[ "$device" == zz_test_* ]]; then
        continue
    fi
    scripts/build_website.sh "$device" "$out_root/$device/frozen_html.py"
done
device=""
